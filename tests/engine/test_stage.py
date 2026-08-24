"""
Tests for independent stage execution.
"""
# File: tests/engine/test_stage.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import (
    StageContext,
    StageExecutionError,
    execute_stage,
)
from lowkey_artifact_builder.engine.registry import (
    StageRegistry,
)

# =========================================================
# Helpers
# =========================================================


def _context(
    tmp_path: Path,
    resolver: Resolver,
    *,
    model_name: str = "artwork",
    stage_name: str = "vector",
    outputs: dict[str, Path] | None = None,
) -> StageContext:
    """
    Construct a minimal context for independent stage execution.
    """

    working_dir = tmp_path / "artifacts" / "example" / model_name / "default" / "30-vector"

    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return StageContext(
        artifact_id="example",
        model_name=model_name,
        stage_name=stage_name,
        project_root=tmp_path,
        artifact_dir=tmp_path / "artifacts" / "example",
        working_dir=working_dir,
        resolver=resolver,
        inputs={},
        outputs=outputs or {},
    )


def _install_registry(
    monkeypatch: pytest.MonkeyPatch,
    registry: StageRegistry,
) -> None:
    """
    Install a stage registry for independent execution tests.
    """

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.stage.build_stage_registry",
        lambda: registry,
    )


# =========================================================
# Stage dispatch
# =========================================================


def test_execute_stage_dispatches_registered_implementation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution dispatches by model and stage identity.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    received: list[StageContext] = []

    def implementation(
        stage_context: StageContext,
    ) -> None:
        received.append(
            stage_context,
        )

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        implementation,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    execute_stage(
        context,
    )

    assert received == [
        context,
    ]


def test_execute_stage_passes_exact_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution does not reconstruct or replace StageContext.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    received: StageContext | None = None

    def implementation(
        stage_context: StageContext,
    ) -> None:
        nonlocal received

        received = stage_context

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        implementation,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    execute_stage(
        context,
    )

    assert received is context


# =========================================================
# Working directory
# =========================================================


def test_execute_stage_uses_stage_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    A stage executes from the working directory in its StageContext.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    observed: Path | None = None

    def implementation(
        stage_context: StageContext,
    ) -> None:
        nonlocal observed

        observed = Path.cwd()

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        implementation,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    execute_stage(
        context,
    )

    assert observed == context.working_dir


def test_execute_stage_restores_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution restores the caller's working directory.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    original = Path.cwd()

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        lambda context: None,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    execute_stage(
        context,
    )

    assert Path.cwd() == original


def test_execute_stage_restores_working_directory_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    The caller's working directory is restored when a stage fails.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    original = Path.cwd()

    def implementation(
        stage_context: StageContext,
    ) -> None:
        raise RuntimeError("boom")

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        implementation,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    with pytest.raises(
        StageExecutionError,
        match="Stage 'vector' failed",
    ):
        execute_stage(
            context,
        )

    assert Path.cwd() == original


# =========================================================
# Execution failures
# =========================================================


def test_execute_stage_rejects_missing_implementation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution requires a registered stage implementation.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    registry = StageRegistry()

    _install_registry(
        monkeypatch,
        registry,
    )

    with pytest.raises(
        StageExecutionError,
        match=("No implementation is registered for model 'artwork', stage 'vector'"),
    ):
        execute_stage(
            context,
        )


def test_execute_stage_wraps_implementation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Implementation failures cross the engine boundary as StageExecutionError.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    def implementation(
        stage_context: StageContext,
    ) -> None:
        raise ValueError("bad stage")

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        implementation,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    with pytest.raises(
        StageExecutionError,
        match="Stage 'vector' failed",
    ) as exc_info:
        execute_stage(
            context,
        )

    assert isinstance(
        exc_info.value.__cause__,
        ValueError,
    )


# =========================================================
# Product verification
# =========================================================


def test_execute_stage_accepts_declared_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution succeeds when every declared output exists.
    """

    output = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "30-vector" / "products.json"
    )

    context = _context(
        tmp_path,
        test_resolver,
        outputs={
            "manifest": output,
        },
    )

    def implementation(
        stage_context: StageContext,
    ) -> None:
        stage_context.output(
            "manifest",
        ).write_text(
            "{}",
            encoding="utf-8",
        )

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        implementation,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    execute_stage(
        context,
    )

    assert output.is_file()


def test_execute_stage_rejects_missing_declared_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution requires every declared output to exist.
    """

    output = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "30-vector" / "products.json"
    )

    context = _context(
        tmp_path,
        test_resolver,
        outputs={
            "manifest": output,
        },
    )

    registry = StageRegistry()

    registry.register(
        "artwork",
        "vector",
        lambda context: None,
    )

    _install_registry(
        monkeypatch,
        registry,
    )

    with pytest.raises(
        StageExecutionError,
        match="did not produce declared product",
    ):
        execute_stage(
            context,
        )
