"""
Tests for the artifact build engine.

These tests exercise the public engine interface and verify build
planning, external input materialization, stage execution contexts,
workspace management, stage dispatch, stage execution, and product
verification.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildError,
    BuildPlan,
    BuildPlanError,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
    ResolvedParameter,
    StageContext,
    StageContextError,
    create_build_plan,
    execute_build,
)
from lowkey_artifact_builder.engine.registry import StageRegistry

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
    assert ResolvedParameter is not None
    assert StageContext is not None
    assert StageContextError is not None
    assert BuildError is not None

    assert callable(create_build_plan)
    assert callable(execute_build)


# =========================================================
# Build planning
# =========================================================


def test_create_build_plan_for_artwork(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A configured artwork artifact produces the complete artwork build
    workflow in declared stage order.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert isinstance(
        plan,
        BuildPlan,
    )

    assert plan.artifact_id == "example"
    assert plan.model_name == "artwork"
    assert plan.project_root == tmp_path
    assert plan.artifact_dir == (tmp_path / "artifacts" / "example")

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_create_build_plan_resolves_stage_parameters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned stages contain the non-filesystem configuration values they
    consume together with configuration provenance.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    prepare = plan.stages[0]

    assert prepare.name == "prepare"

    assert tuple(parameter.name for parameter in prepare.parameters) == ("artwork_colors",)

    assert tuple(parameter.value for parameter in prepare.parameters) == (
        [
            "white",
            "black",
        ],
    )

    assert all(parameter.source == "test" for parameter in prepare.parameters)


def test_create_build_plan_resolves_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning resolves external filesystem inputs to both their original
    source and artifact-owned materialization paths.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    prepare = plan.stages[0]

    assert len(prepare.inputs) == 1

    source = prepare.inputs[0]

    assert source.name == "source"

    assert source.source_path == (tmp_path / "source.png")

    assert source.path == (plan.artifact_dir / "artifact.png")


def test_create_build_plan_materializes_product_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Declarative product paths are materialized relative to the
    artifact working directory.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    products = {
        stage.name: tuple(product.path for product in stage.products) for stage in plan.stages
    }

    artifact_dir = tmp_path / "artifacts" / "example"

    assert products == {
        "prepare": (artifact_dir / "prepare" / "trace.svg",),
        "raster": (artifact_dir / "raster" / "products.json",),
        "vector": (artifact_dir / "vector" / "products.json",),
        "extrude": (artifact_dir / "extrude" / "products.json",),
        "package": (artifact_dir / "artifact.3mf",),
    }


def test_create_build_plan_preserves_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned stages preserve their declared workflow dependencies.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    dependencies = {stage.name: stage.dependencies for stage in plan.stages}

    assert dependencies == {
        "prepare": (),
        "raster": ("prepare",),
        "vector": ("raster",),
        "extrude": ("vector",),
        "package": ("extrude",),
    }


# =========================================================
# Planning side effects
# =========================================================


def test_create_build_plan_does_not_create_artifact_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning is read-only and does not create the artifact working
    directory or materialize external inputs.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert not plan.artifact_dir.exists()

    assert not (plan.artifact_dir / "artifact.png").exists()


# =========================================================
# Invalid models
# =========================================================


def test_create_build_plan_rejects_unknown_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning fails when an artifact references a model that is not
    registered.
    """

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            assert name == "model"

            return "does-not-exist"

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, project_root: Resolver(),
    )

    with pytest.raises(
        BuildPlanError,
        match="unknown model",
    ):
        create_build_plan(
            "example",
            project_root=tmp_path,
        )


# =========================================================
# Stage context
# =========================================================


def test_stage_context_accessors(
    tmp_path: Path,
) -> None:
    """
    Stage contexts expose parameters, inputs, and outputs through their
    execution-oriented accessors.
    """

    artifact_dir = tmp_path / "artifacts" / "example"

    context = StageContext(
        artifact_id="example",
        model_name="artwork",
        stage_name="raster",
        project_root=tmp_path,
        artifact_dir=artifact_dir,
        working_dir=(artifact_dir / "raster"),
        parameters={
            "artwork_pixels": 1024,
        },
        inputs={
            "prepare.trace": (artifact_dir / "prepare" / "trace.svg"),
        },
        outputs={
            "manifest": (artifact_dir / "raster" / "products.json"),
        },
    )

    assert context.parameter("artwork_pixels") == 1024

    assert context.input("prepare.trace") == (artifact_dir / "prepare" / "trace.svg")

    assert context.output("manifest") == (artifact_dir / "raster" / "products.json")


def test_stage_context_rejects_unknown_parameter(
    tmp_path: Path,
) -> None:
    """
    Missing stage parameters produce a StageContextError rather than a
    raw mapping KeyError.
    """

    context = _empty_stage_context(
        tmp_path,
    )

    with pytest.raises(
        StageContextError,
        match="has no parameter",
    ):
        context.parameter("missing")


def test_stage_context_rejects_unknown_input(
    tmp_path: Path,
) -> None:
    """
    Missing filesystem inputs produce a StageContextError rather than a
    raw mapping KeyError.
    """

    context = _empty_stage_context(
        tmp_path,
    )

    with pytest.raises(
        StageContextError,
        match="has no input",
    ):
        context.input("prepare.trace")


def test_stage_context_rejects_unknown_output(
    tmp_path: Path,
) -> None:
    """
    Missing declared outputs produce a StageContextError rather than a
    raw mapping KeyError.
    """

    context = _empty_stage_context(
        tmp_path,
    )

    with pytest.raises(
        StageContextError,
        match="has no output",
    ):
        context.output("trace")


# =========================================================
# Build workspace
# =========================================================


def test_execute_build_creates_declared_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution creates the complete declared workspace before the first
    stage implementation runs.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    expected = {
        plan.artifact_dir,
        plan.artifact_dir / "prepare",
        plan.artifact_dir / "raster",
        plan.artifact_dir / "vector",
        plan.artifact_dir / "extrude",
    }

    observed: set[Path] = set()

    def implementation(
        context: StageContext,
    ) -> None:
        if context.stage_name == "prepare":
            observed.update(path for path in expected if path.is_dir())

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == expected


# =========================================================
# External input materialization
# =========================================================


def test_execute_build_materializes_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution copies the configured external source into the
    artifact-owned materialization path before stage execution.
    """

    source = tmp_path / "source.png"
    source.write_bytes(b"source artwork")

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    materialized = plan.artifact_dir / "artifact.png"

    def implementation(
        context: StageContext,
    ) -> None:
        if context.stage_name == "prepare":
            assert materialized.is_file()

            assert materialized.read_bytes() == (b"source artwork")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert materialized.is_file()
    assert materialized.read_bytes() == (b"source artwork")


def test_execute_build_prepare_receives_materialized_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The prepare implementation receives the artifact-owned source path
    rather than the original project source path.
    """

    source = tmp_path / "source.png"
    source.touch()

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: Path | None = None

    def implementation(
        context: StageContext,
    ) -> None:
        nonlocal observed

        if context.stage_name == "prepare":
            observed = context.input("source")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == (plan.artifact_dir / "artifact.png")

    assert observed != source


def test_execute_build_rejects_missing_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution fails before any stage runs when a required external
    filesystem input does not exist.
    """

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="does not exist",
    ):
        execute_build(plan)

    assert executed == []


# =========================================================
# Build execution order
# =========================================================


def test_execute_build_runs_stages_in_plan_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution invokes model stages in the order established by the
    build plan.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    ]


# =========================================================
# Stage working directories
# =========================================================


def test_execute_build_sets_stage_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Each implementation executes from the directory containing its
    declared products.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        Path,
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = Path.cwd()

        assert Path.cwd() == (context.working_dir)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == {
        "prepare": (plan.artifact_dir / "prepare"),
        "raster": (plan.artifact_dir / "raster"),
        "vector": (plan.artifact_dir / "vector"),
        "extrude": (plan.artifact_dir / "extrude"),
        "package": plan.artifact_dir,
    }


def test_execute_build_restores_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution restores the caller's working directory after a
    successful build.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    original = Path.cwd()

    def implementation(
        context: StageContext,
    ) -> None:
        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert Path.cwd() == original


def test_execute_build_restores_working_directory_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A failing implementation does not leave the process inside the
    artifact workspace.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    original = Path.cwd()

    def implementation(
        context: StageContext,
    ) -> None:
        raise ValueError("boom")

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
    ):
        execute_build(plan)

    assert Path.cwd() == original


# =========================================================
# Stage parameters
# =========================================================


def test_execute_build_context_contains_stage_parameters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage implementations receive resolved non-filesystem parameters
    through the execution context.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        set[str],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = set(context.parameters)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == {
        "prepare": {
            "artwork_colors",
        },
        "raster": {
            "artwork_colors",
            "artwork_pixels",
            "artwork_min_island_area",
            "artwork_island_connectivity",
        },
        "vector": {
            "artwork_size",
        },
        "extrude": {
            "artwork_colors",
            "artwork_raise",
        },
        "package": set(),
    }


# =========================================================
# Stage inputs
# =========================================================


def test_execute_build_context_contains_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit external inputs are exposed using their declarative names
    and artifact-owned paths.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        dict[str, Path],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = dict(context.inputs)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed["prepare"] == {
        "source": (plan.artifact_dir / "artifact.png"),
    }


def test_execute_build_context_contains_dependency_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage contexts expose products from direct dependencies using
    qualified input names.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        dict[str, Path],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = dict(context.inputs)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed["prepare"] == {
        "source": (plan.artifact_dir / "artifact.png"),
    }

    assert observed["raster"] == {
        "prepare.trace": (plan.artifact_dir / "prepare" / "trace.svg"),
    }

    assert observed["vector"] == {
        "raster.manifest": (plan.artifact_dir / "raster" / "products.json"),
    }

    assert observed["extrude"] == {
        "vector.manifest": (plan.artifact_dir / "vector" / "products.json"),
    }

    assert observed["package"] == {
        "extrude.manifest": (plan.artifact_dir / "extrude" / "products.json"),
    }


# =========================================================
# Stage outputs
# =========================================================


def test_execute_build_context_contains_declared_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage contexts expose current-stage products by declarative product
    name.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        dict[str, Path],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = dict(context.outputs)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed["prepare"] == {
        "trace": (plan.artifact_dir / "prepare" / "trace.svg"),
    }

    assert observed["raster"] == {
        "manifest": (plan.artifact_dir / "raster" / "products.json"),
    }

    assert observed["vector"] == {
        "manifest": (plan.artifact_dir / "vector" / "products.json"),
    }

    assert observed["extrude"] == {
        "manifest": (plan.artifact_dir / "extrude" / "products.json"),
    }

    assert observed["package"] == {
        "artifact": (plan.artifact_dir / "artifact.3mf"),
    }


# =========================================================
# Product verification
# =========================================================


def test_execute_build_rejects_missing_declared_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A stage that returns without creating its declared product causes
    the build to fail immediately.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        if context.stage_name != "raster":
            _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="did not produce declared product",
    ):
        execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
    ]


# =========================================================
# Stage failures
# =========================================================


def test_execute_build_stops_after_stage_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An exception from a stage implementation stops the build and
    prevents later stages from executing.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        if context.stage_name == "vector":
            raise ValueError("vector failed")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="vector failed",
    ):
        execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
        "vector",
    ]


def test_execute_build_wraps_stage_failure_with_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Exceptions from model-specific implementations are exposed as
    BuildError with artifact, model, and stage context.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    def implementation(
        context: StageContext,
    ) -> None:
        raise ValueError("boom")

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
    ) as exc_info:
        execute_build(plan)

    message = str(exc_info.value)

    assert "example" in message
    assert "artwork" in message
    assert "prepare" in message
    assert "boom" in message


# =========================================================
# Stage dispatch
# =========================================================


def test_execute_build_rejects_unregistered_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution fails cleanly when no model-specific implementation is
    registered for a planned stage.
    """

    _create_source(tmp_path)

    plan = _create_artwork_plan(
        tmp_path,
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build.build_stage_registry",
        lambda: StageRegistry(),
    )

    with pytest.raises(
        BuildError,
        match="No implementation is registered",
    ):
        execute_build(plan)


# =========================================================
# Test helpers
# =========================================================


def _create_artwork_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> BuildPlan:
    """
    Construct a standard artwork build plan for engine tests.
    """

    class Resolver:
        values = {
            "model": "artwork",
            "source": "source.png",
            "artwork_colors": [
                "white",
                "black",
            ],
            "artwork_pixels": 1024,
            "artwork_min_island_area": 0.5,
            "artwork_island_connectivity": 8,
            "artwork_size": 150.0,
            "artwork_raise": 1.0,
        }

        def __call__(
            self,
            name: str,
        ):
            return self.values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    resolver = Resolver()

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, project_root: resolver,
    )

    return create_build_plan(
        "example",
        project_root=tmp_path,
    )


def _create_source(
    tmp_path: Path,
) -> Path:
    """
    Create the standard external source image used by execution tests.
    """

    source = tmp_path / "source.png"

    source.write_bytes(b"source artwork")

    return source


def _empty_stage_context(
    tmp_path: Path,
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
        parameters={},
        inputs={},
        outputs={},
    )


def _install_stage_implementation(
    monkeypatch: pytest.MonkeyPatch,
    implementation: Callable[
        [StageContext],
        None,
    ],
) -> None:
    """
    Install one test implementation for every artwork model stage.

    Tests replace engine bootstrap with an isolated registry rather
    than patching private stage-dispatch behavior.
    """

    registry = StageRegistry()

    for stage_name in (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    ):
        registry.register(
            "artwork",
            stage_name,
            implementation,
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build.build_stage_registry",
        lambda: registry,
    )


def _create_declared_outputs(
    context: StageContext,
) -> None:
    """
    Create placeholder files for every declared output of a test stage.

    Workspace directories are expected to have already been created by
    the engine.
    """

    for path in context.outputs.values():
        assert path.parent.is_dir()

        path.touch()
