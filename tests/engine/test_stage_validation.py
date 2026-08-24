"""
Tests for independent stage input validation.
"""
# File: tests/engine/test_stage_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    StageContext,
    StageInputError,
    validate_stage_inputs,
)

# =========================================================
# Helpers
# =========================================================


def _context(
    tmp_path: Path,
    test_resolver,
    *,
    stage_name: str = "vector",
    inputs: dict[str, Path] | None = None,
) -> StageContext:
    """
    Construct a minimal context for stage input validation.
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
        resolver=test_resolver,
        inputs=inputs or {},
        outputs={},
    )


# =========================================================
# Successful validation
# =========================================================


def test_validate_stage_inputs_accepts_no_inputs(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A stage with no resolved inputs is ready for execution.
    """

    context = _context(
        tmp_path,
        test_resolver,
        inputs={},
    )

    validate_stage_inputs(
        context,
    )


def test_validate_stage_inputs_accepts_existing_file(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A resolved filesystem input is valid when the file exists.
    """

    input_path = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "20-raster" / "products.json"
    )

    input_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_path.write_text(
        "{}",
        encoding="utf-8",
    )

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "raster.manifest": input_path,
        },
    )

    validate_stage_inputs(
        context,
    )


def test_validate_stage_inputs_accepts_all_existing_inputs(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Every resolved input is checked independently.
    """

    first = tmp_path / "first.dat"
    second = tmp_path / "second.dat"

    first.write_bytes(
        b"first",
    )

    second.write_bytes(
        b"second",
    )

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "first": first,
            "second": second,
        },
    )

    validate_stage_inputs(
        context,
    )


# =========================================================
# Missing inputs
# =========================================================


def test_validate_stage_inputs_rejects_missing_input(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Independent execution requires every resolved input to exist.
    """

    input_path = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "20-raster" / "products.json"
    )

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "raster.manifest": input_path,
        },
    )

    with pytest.raises(
        StageInputError,
        match="raster.manifest",
    ):
        validate_stage_inputs(
            context,
        )


def test_validate_stage_inputs_identifies_missing_path(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Missing-input errors identify the expected filesystem location.
    """

    input_path = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "20-raster" / "products.json"
    )

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "raster.manifest": input_path,
        },
    )

    with pytest.raises(
        StageInputError,
    ) as exc_info:
        validate_stage_inputs(
            context,
        )

    assert str(input_path) in str(exc_info.value)


def test_validate_stage_inputs_reports_all_missing_inputs(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Validation reports every missing input in one failure.
    """

    first = tmp_path / "first.dat"
    second = tmp_path / "second.dat"

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "first": first,
            "second": second,
        },
    )

    with pytest.raises(
        StageInputError,
    ) as exc_info:
        validate_stage_inputs(
            context,
        )

    message = str(exc_info.value)

    assert "first" in message
    assert str(first) in message

    assert "second" in message
    assert str(second) in message


def test_validate_stage_inputs_reports_only_missing_inputs(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Existing inputs are not reported as missing.
    """

    existing = tmp_path / "existing.dat"
    missing = tmp_path / "missing.dat"

    existing.write_bytes(
        b"existing",
    )

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "existing": existing,
            "missing": missing,
        },
    )

    with pytest.raises(
        StageInputError,
    ) as exc_info:
        validate_stage_inputs(
            context,
        )

    message = str(exc_info.value)

    assert "missing" in message
    assert str(missing) in message

    assert str(existing) not in message


# =========================================================
# External artifact inputs
# =========================================================


def test_validate_stage_inputs_rejects_missing_materialized_external_input(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Independent prepare execution requires its artifact-owned input.

    Validation does not fall back to the original external source.
    """

    artifact_input = tmp_path / "artifacts" / "example" / "artifact.png"

    source = tmp_path / "source.png"

    source.write_bytes(
        b"source",
    )

    context = _context(
        tmp_path,
        test_resolver,
        stage_name="prepare",
        inputs={
            "source": artifact_input,
        },
    )

    with pytest.raises(
        StageInputError,
        match="source",
    ):
        validate_stage_inputs(
            context,
        )

    assert not artifact_input.exists()


# =========================================================
# Dependency products
# =========================================================


def test_validate_stage_inputs_requires_dependency_product(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Independent execution requires direct dependency products to exist.
    """

    manifest = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "20-raster" / "products.json"
    )

    context = _context(
        tmp_path,
        test_resolver,
        stage_name="vector",
        inputs={
            "raster.manifest": manifest,
        },
    )

    with pytest.raises(
        StageInputError,
        match="raster.manifest",
    ):
        validate_stage_inputs(
            context,
        )


def test_validate_stage_inputs_does_not_create_dependency_product(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Validation never attempts to realize a missing dependency product.
    """

    manifest = (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "20-raster" / "products.json"
    )

    context = _context(
        tmp_path,
        test_resolver,
        stage_name="vector",
        inputs={
            "raster.manifest": manifest,
        },
    )

    with pytest.raises(
        StageInputError,
    ):
        validate_stage_inputs(
            context,
        )

    assert not manifest.exists()


# =========================================================
# Validation side effects
# =========================================================


def test_validate_stage_inputs_does_not_modify_filesystem(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Input validation is read-only.
    """

    artifact_dir = tmp_path / "artifacts" / "example"

    missing = artifact_dir / "artwork" / "default" / "20-raster" / "products.json"

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "raster.manifest": missing,
        },
    )

    assert not artifact_dir.exists()

    with pytest.raises(
        StageInputError,
    ):
        validate_stage_inputs(
            context,
        )

    assert not artifact_dir.exists()


def test_validate_stage_inputs_rejects_directory(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A resolved stage input must identify a regular file.
    """

    input_path = tmp_path / "input"

    input_path.mkdir()

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "input": input_path,
        },
    )

    with pytest.raises(
        StageInputError,
        match="is not a regular file",
    ):
        validate_stage_inputs(
            context,
        )


def test_validate_stage_inputs_does_not_execute_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver,
) -> None:
    """
    Input validation never dispatches a stage implementation.
    """

    input_path = tmp_path / "input.dat"

    input_path.write_bytes(
        b"input",
    )

    context = _context(
        tmp_path,
        test_resolver,
        inputs={
            "input": input_path,
        },
    )

    def unexpected_registry():
        pytest.fail("stage implementation registry was constructed")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.stage.build_stage_registry",
        unexpected_registry,
    )

    validate_stage_inputs(
        context,
    )
