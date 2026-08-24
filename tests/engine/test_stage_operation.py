"""
Tests for independent artifact stage execution.
"""
# File: tests/engine/test_stage_operation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import (
    StageContext,
    StageInputError,
    create_stage_context,
    execute_artifact_stage,
)

# =========================================================
# Helpers
# =========================================================


def _context(
    tmp_path: Path,
    resolver: Resolver,
    *,
    stage_name: str = "vector",
) -> StageContext:
    """
    Construct a resolved context for operation tests.
    """

    artifact_dir = tmp_path / "artifacts" / "example"

    working_dir = artifact_dir / "artwork" / "default" / "30-vector"

    return StageContext(
        artifact_id="example",
        model_name="artwork",
        stage_name=stage_name,
        project_root=tmp_path,
        artifact_dir=artifact_dir,
        working_dir=working_dir,
        resolver=resolver,
        inputs={},
        outputs={},
    )


# =========================================================
# Context resolution
# =========================================================


def test_execute_artifact_stage_resolves_requested_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution resolves exactly the requested artifact stage.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    received: list[
        tuple[
            str,
            str,
            str | None,
            Path | None,
        ]
    ] = []

    def fake_create_stage_context(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
    ) -> StageContext:
        received.append(
            (
                artifact_id,
                stage_name,
                realization,
                project_root,
            )
        )

        return context

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.create_stage_context",
        fake_create_stage_context,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.validate_stage_inputs",
        lambda context: None,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        lambda context: None,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        realization="default",
        project_root=tmp_path,
    )

    assert received == [
        (
            "example",
            "vector",
            "default",
            tmp_path,
        ),
    ]


# =========================================================
# Operation ordering
# =========================================================


def test_execute_artifact_stage_validates_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution validates the resolved context before dispatch.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    events: list[str] = []

    def create_context(
        *args,
        **kwargs,
    ) -> StageContext:
        events.append(
            "resolve",
        )

        return context

    def validate(
        received: StageContext,
    ) -> None:
        assert received is context

        events.append(
            "validate",
        )

    def execute(
        received: StageContext,
    ) -> None:
        assert received is context

        events.append(
            "execute",
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.create_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.validate_stage_inputs",
        validate,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        execute,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert events == [
        "resolve",
        "validate",
        "execute",
    ]


def test_execute_artifact_stage_passes_same_context_through_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Resolution, validation, and execution share one StageContext instance.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    validated: StageContext | None = None
    executed: StageContext | None = None

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.create_stage_context",
        lambda *args, **kwargs: context,
    )

    def validate(
        received: StageContext,
    ) -> None:
        nonlocal validated

        validated = received

    def execute(
        received: StageContext,
    ) -> None:
        nonlocal executed

        executed = received

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.validate_stage_inputs",
        validate,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        execute,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert validated is context
    assert executed is context


# =========================================================
# Validation failure
# =========================================================


def test_execute_artifact_stage_does_not_execute_invalid_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Input validation failure prevents stage implementation execution.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    executed = False

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.create_stage_context",
        lambda *args, **kwargs: context,
    )

    def reject(
        received: StageContext,
    ) -> None:
        assert received is context

        raise StageInputError("missing prerequisite")

    def execute(
        received: StageContext,
    ) -> None:
        nonlocal executed

        executed = True

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.validate_stage_inputs",
        reject,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        execute,
    )

    with pytest.raises(
        StageInputError,
        match="missing prerequisite",
    ):
        execute_artifact_stage(
            "example",
            stage_name="vector",
            project_root=tmp_path,
        )

    assert not executed


# =========================================================
# Exactly-one-stage semantics
# =========================================================


def test_execute_artifact_stage_executes_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution dispatches exactly one stage implementation.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    executions: list[StageContext] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.create_stage_context",
        lambda *args, **kwargs: context,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.validate_stage_inputs",
        lambda context: None,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        executions.append,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert executions == [
        context,
    ]


# =========================================================
# Planning independence
# =========================================================


def test_execute_artifact_stage_does_not_create_build_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent stage execution does not enter graph build planning.
    """

    context = _context(
        tmp_path,
        test_resolver,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.create_stage_context",
        lambda *args, **kwargs: context,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.validate_stage_inputs",
        lambda context: None,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        lambda context: None,
    )

    def unexpected_plan(
        *args,
        **kwargs,
    ):
        pytest.fail("independent stage execution entered build planning")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.create_build_plan",
        unexpected_plan,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )


# =========================================================
# Integrated independent execution
# =========================================================


def test_execute_artifact_stage_executes_only_requested_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Real independent resolution and validation execute only the target.

    Direct dependency products must already exist. Their presence allows
    the requested stage to reach the execution boundary without build
    planning or execution of prerequisite stages.
    """

    def fake_get_resolver(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> Resolver:
        assert artifact_id == "example"
        assert realization is None
        assert project_root == tmp_path

        return test_resolver

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.context.get_resolver",
        fake_get_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert context.stage_name == "vector"
    assert context.inputs

    for path in context.inputs.values():
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            "{}",
            encoding="utf-8",
        )

    executed: list[StageContext] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.operation.execute_stage",
        executed.append,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert len(executed) == 1

    executed_context = executed[0]

    assert executed_context.stage_name == "vector"
    assert executed_context.model_name == "artwork"
    assert executed_context.artifact_id == "example"

    assert executed_context.inputs == context.inputs
    assert executed_context.outputs == context.outputs

    assert all(path.is_file() for path in executed_context.inputs.values())
