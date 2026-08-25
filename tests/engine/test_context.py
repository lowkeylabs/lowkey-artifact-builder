"""
Tests for independent stage context construction.
"""
# File: tests/engine/test_context.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    ConfigError,
    Resolver,
)
from lowkey_artifact_builder.engine import (
    StageContext,
    StageContextError,
    create_stage_context,
)

# =========================================================
# Helpers
# =========================================================


def _install_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resolver: Resolver,
) -> None:
    """
    Install the standard resolver for independent context construction.
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

        return resolver

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.context.get_resolver",
        fake_get_resolver,
    )


# =========================================================
# Context identity
# =========================================================


def test_create_stage_context_resolves_stage_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent context construction preserves artifact and stage identity.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert isinstance(
        context,
        StageContext,
    )

    assert context.artifact_id == "example"
    assert context.model_name == "artwork"
    assert context.stage_name == "vector"


def test_create_stage_context_retains_artifact_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent execution receives the artifact's resolved configuration.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert context.resolver is test_resolver


# =========================================================
# Filesystem identity
# =========================================================


def test_create_stage_context_resolves_artifact_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent context construction uses the canonical artifact directory.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert context.project_root == tmp_path

    assert context.artifact_dir == (tmp_path / "artifacts" / "example")


def test_create_stage_context_resolves_stage_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    A stage uses the same canonical working directory as graph execution.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert context.working_dir == (
        tmp_path / "artifacts" / "example" / "artwork" / "default" / "30-vector"
    )


# =========================================================
# Explicit inputs
# =========================================================


def test_create_stage_context_resolves_declared_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Declared external inputs resolve to their artifact-owned locations.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="prepare",
        project_root=tmp_path,
    )

    assert context.inputs["source"] == (tmp_path / "artifacts" / "example" / "artifact.png")


# =========================================================
# Dependency products
# =========================================================


def test_create_stage_context_resolves_direct_dependency_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Direct dependency products use qualified semantic input names.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert context.inputs == {
        "raster.manifest": (
            tmp_path
            / "artifacts"
            / "example"
            / "artwork"
            / "default"
            / "20-raster"
            / "products.json"
        ),
    }


def test_create_stage_context_includes_only_direct_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    StageContext contains direct dependency products, not transitive ones.

    Dependency traversal remains a planning concern rather than a
    StageContext construction concern.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert "raster.manifest" in context.inputs

    assert all(not name.startswith("prepare.") for name in context.inputs)


# =========================================================
# Outputs
# =========================================================


def test_create_stage_context_resolves_declared_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Declared outputs use the same canonical paths as graph execution.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert context.outputs == {
        "manifest": (
            tmp_path
            / "artifacts"
            / "example"
            / "artwork"
            / "default"
            / "30-vector"
            / "products.json"
        ),
    }


def test_create_stage_context_resolves_final_artifact_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent package execution preserves final-product path semantics.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    context = create_stage_context(
        "example",
        stage_name="package",
        project_root=tmp_path,
    )

    assert context.outputs == {
        "artifact": (
            tmp_path
            / "artifacts"
            / "example"
            / "artwork"
            / "default"
            / "50-package"
            / "artifact.3mf"
        ),
    }


# =========================================================
# Construction side effects
# =========================================================


def test_create_stage_context_does_not_create_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Constructing an independent context does not modify the filesystem.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    artifact_dir = tmp_path / "artifacts" / "example"

    assert not artifact_dir.exists()

    create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert not artifact_dir.exists()


# =========================================================
# Validation
# =========================================================


def test_create_stage_context_rejects_unknown_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Independent context construction requires a declared model stage.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    with pytest.raises(
        StageContextError,
        match="Unknown stage 'missing'",
    ):
        create_stage_context(
            "example",
            stage_name="missing",
            project_root=tmp_path,
        )


# =========================================================
# Graph and independent context equivalence
# =========================================================


@pytest.mark.parametrize(
    "stage_name",
    [
        "prepare",
        "vector",
        "package",
    ],
)
def test_independent_context_matches_planned_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
    artwork_plan,
    stage_name: str,
) -> None:
    """
    Independent and graph-driven execution resolve equivalent contexts.

    Representative stages cover explicit external inputs, dependency
    products, and final artifact products.

    Graph-driven contexts are observed at the common stage execution
    boundary rather than through build implementation details.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    captured: list[StageContext] = []

    def capture_stage(
        context: StageContext,
    ) -> None:
        captured.append(
            context,
        )

        for output in context.outputs.values():
            output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output.touch()

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build.execute_stage",
        capture_stage,
    )

    source = tmp_path / "source.png"

    source.write_bytes(
        b"test",
    )

    from lowkey_artifact_builder.engine import (
        execute_build,
    )

    execute_build(
        plan,
    )

    planned_context = next(context for context in captured if context.stage_name == stage_name)

    independent_context = create_stage_context(
        "example",
        stage_name=stage_name,
        project_root=tmp_path,
    )

    assert independent_context.artifact_id == planned_context.artifact_id
    assert independent_context.model_name == planned_context.model_name
    assert independent_context.stage_name == planned_context.stage_name
    assert independent_context.project_root == planned_context.project_root
    assert independent_context.artifact_dir == planned_context.artifact_dir
    assert independent_context.working_dir == planned_context.working_dir
    assert independent_context.resolver is planned_context.resolver
    assert independent_context.inputs == planned_context.inputs
    assert independent_context.outputs == planned_context.outputs


def test_independent_context_matches_planned_context_for_every_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
    artwork_plan,
) -> None:
    """
    Every graph-driven artwork stage has an equivalent independent context.

    Contexts are observed at the common stage execution boundary,
    ensuring normal builds and independent execution share the same
    execution-facing contract.
    """

    _install_resolver(
        tmp_path,
        monkeypatch,
        test_resolver,
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    captured: list[StageContext] = []

    def capture_stage(
        context: StageContext,
    ) -> None:
        captured.append(
            context,
        )

        for output in context.outputs.values():
            output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output.touch()

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build.execute_stage",
        capture_stage,
    )

    source = tmp_path / "source.png"

    source.write_bytes(
        b"test",
    )

    from lowkey_artifact_builder.engine import (
        execute_build,
    )

    execute_build(
        plan,
    )

    assert tuple(context.stage_name for context in captured) == tuple(
        stage.name for stage in plan.stages
    )

    for planned_context in captured:
        independent_context = create_stage_context(
            "example",
            stage_name=planned_context.stage_name,
            project_root=tmp_path,
        )

        assert independent_context.artifact_id == planned_context.artifact_id
        assert independent_context.model_name == planned_context.model_name
        assert independent_context.stage_name == planned_context.stage_name
        assert independent_context.project_root == planned_context.project_root
        assert independent_context.artifact_dir == planned_context.artifact_dir
        assert independent_context.working_dir == planned_context.working_dir
        assert independent_context.resolver is planned_context.resolver
        assert independent_context.inputs == planned_context.inputs
        assert independent_context.outputs == planned_context.outputs


def test_create_stage_context_translates_configuration_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Configuration failures are reported as stage context failures.
    """

    def fail(
        *args,
        **kwargs,
    ):
        raise ConfigError("artifact configuration is invalid")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.context.get_resolver",
        fail,
    )

    with pytest.raises(
        StageContextError,
        match="artifact configuration is invalid",
    ):
        create_stage_context(
            "example",
            stage_name="vector",
            project_root=tmp_path,
        )
