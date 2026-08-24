"""
Tests for the public artifact build engine interface.

These tests verify the public engine package surface and StageContext
behavior shared by model stage implementations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import (
    BuildError,
    BuildPlan,
    BuildPlanError,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
    StageContext,
    StageContextError,
    create_build_plan,
    create_build_plans,
    execute_build,
)

# =========================================================
# Public interface
# =========================================================


def test_engine_public_interface() -> None:
    """
    The engine package exposes its planning and execution interface.
    """

    assert BuildPlan is not None
    assert BuildPlanError is not None
    assert PlannedInput is not None
    assert PlannedProduct is not None
    assert PlannedStage is not None
    assert StageContext is not None
    assert StageContextError is not None
    assert BuildError is not None

    assert callable(create_build_plan)
    assert callable(create_build_plans)
    assert callable(execute_build)


# =========================================================
# Stage context
# =========================================================


def test_stage_context_accessors(
    tmp_path: Path,
    test_resolver: Resolver,
) -> None:
    """
    Stage contexts expose the artifact resolver together with
    filesystem input and output accessors.
    """

    artifact_dir = tmp_path / "artifacts" / "example"

    context = StageContext(
        artifact_id="example",
        model_name="artwork",
        stage_name="raster",
        project_root=tmp_path,
        artifact_dir=artifact_dir,
        working_dir=(artifact_dir / "raster"),
        resolver=test_resolver,
        inputs={
            "prepare.trace": (artifact_dir / "prepare" / "trace.svg"),
        },
        outputs={
            "manifest": (artifact_dir / "raster" / "products.json"),
        },
    )

    assert context.resolver is test_resolver

    assert context.resolver("artwork_pixels") == 1024

    assert context.input("prepare.trace") == (artifact_dir / "prepare" / "trace.svg")

    assert context.output("manifest") == (artifact_dir / "raster" / "products.json")


def test_stage_context_exposes_resolver(
    tmp_path: Path,
    test_resolver: Resolver,
) -> None:
    """
    Stage contexts expose the artifact configuration resolver directly.
    """

    context = _empty_stage_context(
        tmp_path,
        test_resolver,
    )

    assert context.resolver("artwork_pixels") == 1024

    assert context.resolver.source("artwork_pixels") == "test"


def test_stage_context_rejects_unknown_input(
    tmp_path: Path,
    test_resolver: Resolver,
) -> None:
    """
    Missing filesystem inputs produce a StageContextError rather than a
    raw mapping KeyError.
    """

    context = _empty_stage_context(
        tmp_path,
        test_resolver,
    )

    with pytest.raises(
        StageContextError,
        match="has no input",
    ):
        context.input("prepare.trace")


def test_stage_context_rejects_unknown_output(
    tmp_path: Path,
    test_resolver: Resolver,
) -> None:
    """
    Missing declared outputs produce a StageContextError rather than a
    raw mapping KeyError.
    """

    context = _empty_stage_context(
        tmp_path,
        test_resolver,
    )

    with pytest.raises(
        StageContextError,
        match="has no output",
    ):
        context.output("trace")


# =========================================================
# Test helpers
# =========================================================


def _empty_stage_context(
    tmp_path: Path,
    resolver: Resolver,
) -> StageContext:
    """
    Construct an empty stage context for accessor error tests.
    """

    artifact_dir = tmp_path / "artifacts" / "example"

    return StageContext(
        artifact_id="example",
        model_name="artwork",
        stage_name="prepare",
        project_root=tmp_path,
        artifact_dir=artifact_dir,
        working_dir=(artifact_dir / "prepare"),
        resolver=resolver,
        inputs={},
        outputs={},
    )
