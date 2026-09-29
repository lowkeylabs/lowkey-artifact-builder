"""Tests for the color-analysis CLI command."""

# File: tests/cli/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_color as cmd_color
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config.artifact import ArtifactState
from lowkey_artifact_builder.engine import BuildPlan
from lowkey_artifact_builder.model import ProductRef


# =========================================================
# CLI
# =========================================================
def test_colors_is_a_top_level_command() -> None:
    """
    Color analysis is exposed through the standard artifact CLI.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--help"],
    )
    assert result.exit_code == 0
    assert "colors" in result.output


def test_colors_does_not_require_an_artifact_id() -> None:
    """
    Color analysis without an Artifact ID selects the bulk Artifact scope.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "--help",
        ],
    )
    assert result.exit_code == 0
    assert "[ARTIFACT_ID]" in result.output


def test_colors_command_analyzes_and_displays_artifact(
    monkeypatch,
) -> None:
    """
    The colors command obtains and displays structured color analysis.
    """
    analyzed: list[str] = []
    displayed: list[object] = []
    expected_analysis = object()

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        assert realization is None
        analyzed.append(
            artifact_id,
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "discover_artifacts",
        lambda *, project_root: (
            ArtifactState(
                artifact_id="nydeli",
                original_path=project_root / "originals" / "nydeli.png",
                materialized=True,
            ),
        ),
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.display_color_analysis",
        displayed.append,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["colors", "nydeli"],
    )
    assert result.exit_code == 0
    assert analyzed == ["nydeli"]
    assert displayed == [expected_analysis]


# =========================================================
# Analysis
# =========================================================
def test_analyze_artifact_colors_targets_registered_artwork_manifest(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis plans only the canonical default Artwork manifest it requires.
    """
    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    manifest.write_text("{}", encoding="utf-8")
    resolver = object()
    plan = SimpleNamespace(
        resolver=resolver,
        stages=(
            SimpleNamespace(name="prepare", products=()),
            SimpleNamespace(name="raster", products=()),
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )
    planned: list[tuple[str, str, tuple[ProductRef, ...], Path]] = []

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str,
        targets: tuple[ProductRef, ...],
        project_root: Path,
    ) -> object:
        planned.append((artifact_id, realization, targets, project_root))
        return plan

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fail_execute,
        raising=False,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: object(),
    )
    monkeypatch.chdir(tmp_path)
    analyze_artifact_colors("nydeli")
    assert len(planned) == 1
    artifact_id, realization, targets, project_root = planned[0]
    assert artifact_id == "nydeli"
    assert realization == "artwork_default"
    assert project_root == tmp_path
    assert len(targets) == 1
    target = targets[0]
    assert target.artifact == "nydeli"
    assert target.model == "artwork"
    assert target.realization == "artwork_default"
    assert target.stage == "vector"
    assert target.product == "manifest"


def test_analyze_artifact_colors_reads_existing_target_without_execution(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis reads an existing targeted Artwork manifest without executing
    manufacturing.
    """
    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    manifest.write_text("{}", encoding="utf-8")
    resolver = object()
    expected_analysis = object()
    plan = SimpleNamespace(
        resolver=resolver,
        stages=(
            SimpleNamespace(name="prepare", products=()),
            SimpleNamespace(name="raster", products=()),
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fail_execute,
        raising=False,
    )
    analyzed: list[tuple[Path, object]] = []

    def fake_analyze_registered_artwork_colors(
        *,
        manifest: Path,
        resolver,
    ) -> object:
        analyzed.append((manifest, resolver))
        return expected_analysis

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )
    monkeypatch.chdir(tmp_path)
    result = analyze_artifact_colors("nydeli")
    assert result is expected_analysis
    assert analyzed == [(manifest, resolver)]


def test_analyze_artifact_colors_reuses_current_registered_artwork(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Existing registered Artwork is consumed directly without manufacturing.
    """
    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    manifest.write_text("{}", encoding="utf-8")
    resolver = object()
    expected_analysis = object()
    plan = SimpleNamespace(
        resolver=resolver,
        stages=(
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )
    analyzed: list[tuple[Path, object]] = []
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fail_execute,
        raising=False,
    )

    def fake_analyze_registered_artwork_colors(
        *,
        manifest,
        resolver,
    ) -> object:
        analyzed.append((manifest, resolver))
        return expected_analysis

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )
    monkeypatch.chdir(tmp_path)
    result = analyze_artifact_colors("nydeli")
    assert result is expected_analysis
    assert analyzed == [(manifest, resolver)]


def test_analyze_artifact_colors_does_not_modify_configuration(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis remains a read-only configuration diagnostic.
    """
    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    manifest.write_text("{}", encoding="utf-8")
    resolver = SimpleNamespace(
        colors={
            "white": {
                "rgb": [255, 255, 255],
                "manufacturer": "test",
            },
        },
    )
    plan = SimpleNamespace(
        resolver=resolver,
        stages=(
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fail_execute,
        raising=False,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: object(),
    )

    def fail_write(*args, **kwargs) -> None:
        raise AssertionError("color analysis must not modify configuration")

    monkeypatch.setattr(
        "lowkey_artifact_builder.config.write_artifact_config",
        fail_write,
    )
    monkeypatch.chdir(tmp_path)
    analyze_artifact_colors("nydeli")


def test_analyze_artifact_colors_does_not_require_standalone_artwork_stages(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis targets registered Artwork without requesting standalone
    extrusion or packaging and without executing manufacturing.
    """
    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    manifest.write_text("{}", encoding="utf-8")
    plan = SimpleNamespace(
        resolver=object(),
        stages=(
            SimpleNamespace(name="prepare", products=()),
            SimpleNamespace(name="raster", products=()),
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str | None = None,
        targets: tuple[ProductRef, ...] | None = None,
        project_root: Path,
    ) -> object:
        assert artifact_id == "nydeli"
        assert realization == "artwork_default"
        assert project_root == tmp_path
        if targets is None:
            raise AssertionError("color analysis must not request a complete Artwork plan")
        return plan

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fail_execute,
        raising=False,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: object(),
    )
    monkeypatch.chdir(tmp_path)
    analyze_artifact_colors("nydeli")
    stage_names = tuple(stage.name for stage in plan.stages)
    assert stage_names == ("prepare", "raster", "vector")
    assert "extrude" not in stage_names
    assert "package" not in stage_names


def test_analyze_artifact_colors_requires_existing_registered_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Missing registered Artwork is reported as BUILD-required without
    attempting analysis.
    """

    monkeypatch.chdir(tmp_path)

    resolver = Mock()
    manifest = tmp_path / "registered" / "products.json"

    plan = SimpleNamespace(
        resolver=resolver,
        stages=(
            SimpleNamespace(
                name="vector",
                products=(
                    SimpleNamespace(
                        name="manifest",
                        path=manifest,
                    ),
                ),
            ),
        ),
    )

    create_plan = Mock(
        return_value=plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "create_build_plan",
        create_plan,
    )

    analyze = Mock()

    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        analyze,
    )

    with pytest.raises(
        cmd_color.ColorBuildRequired,
    ):
        cmd_color.analyze_artifact_colors(
            "nydeli",
        )

    create_plan.assert_called_once()

    call = create_plan.call_args

    assert call.args == ("nydeli",)
    assert call.kwargs["realization"] == "artwork_default"
    assert call.kwargs["project_root"] == tmp_path
    assert call.kwargs["targets"] == (
        ProductRef(
            artifact="nydeli",
            model="artwork",
            realization="artwork_default",
            stage="vector",
            product="manifest",
        ),
    )

    analyze.assert_not_called()


def test_colors_accepts_realization_option(
    monkeypatch,
) -> None:
    """
    Color analysis may be scoped to a named Realization.
    """
    analyzed: list[tuple[str, str | None]] = []
    expected_analysis = object()

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        analyzed.append(
            (
                artifact_id,
                realization,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "discover_artifacts",
        lambda *, project_root: (
            ArtifactState(
                artifact_id="nydeli",
                original_path=project_root / "originals" / "nydeli.png",
                materialized=True,
            ),
        ),
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.display_color_analysis",
        lambda analysis: None,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
            "--realization",
            "shape_ornament",
        ],
    )
    assert result.exit_code == 0
    assert analyzed == [
        (
            "nydeli",
            "shape_ornament",
        )
    ]


def test_color_analysis_resolves_selected_realization(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped color analysis resolves the selected execution
    coordinate without assuming an Artwork Model.
    """
    selected_plan = SimpleNamespace(
        model_name="shape",
        realization_name="shape_ornament",
        resolver=object(),
        stages=(),
    )
    planned: list[
        tuple[
            str,
            str,
            tuple[ProductRef, ...] | None,
            Path,
        ]
    ] = []

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str,
        targets: tuple[ProductRef, ...] | None = None,
        project_root: Path,
    ) -> object:
        planned.append(
            (
                artifact_id,
                realization,
                targets,
                project_root,
            )
        )
        return selected_plan

    monkeypatch.setattr(
        cmd_color,
        "create_build_plan",
        fake_create_build_plan,
    )
    plan = cmd_color._resolve_color_realization(
        "nydeli",
        realization="shape_ornament",
        project_root=tmp_path,
    )
    assert plan is selected_plan
    assert planned == [
        (
            "nydeli",
            "shape_ornament",
            None,
            tmp_path,
        )
    ]


def test_requested_artwork_realization_dispatches_to_artwork_analysis(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A requested Artwork Realization is dispatched according to its actual
    Model identity through the Artwork-analysis boundary.
    """
    plan = SimpleNamespace(
        model_name="artwork",
        realization_name="artwork_default",
        resolver=object(),
        stages=(),
    )
    expected_analysis = object()
    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_realization",
        lambda artifact_id, *, realization, project_root: plan,
    )
    analyzed: list[
        tuple[
            str,
            str,
            Path,
        ]
    ] = []

    def fake_analyze_artwork_colors(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> object:
        analyzed.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "_analyze_artwork_colors",
        fake_analyze_artwork_colors,
    )
    monkeypatch.chdir(
        tmp_path,
    )
    analysis = cmd_color.analyze_artifact_colors(
        "nydeli",
        realization="artwork_default",
    )
    assert analysis is expected_analysis
    assert analyzed == [
        (
            "nydeli",
            "artwork_default",
            tmp_path,
        )
    ]


def test_requested_shape_realization_dispatches_to_shape_analysis(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A requested Shape Realization is dispatched according to its actual
    Model identity rather than through Artwork analysis.
    """
    plan = SimpleNamespace(
        model_name="shape",
        realization_name="shape_ornament",
        resolver=object(),
        stages=(),
    )
    expected_analysis = object()
    monkeypatch.setattr(
        cmd_color,
        "_resolve_color_realization",
        lambda artifact_id, *, realization, project_root: plan,
    )
    monkeypatch.setattr(
        cmd_color,
        "_analyze_shape_colors",
        lambda selected_plan: expected_analysis,
        raising=False,
    )
    monkeypatch.chdir(
        tmp_path,
    )
    analysis = cmd_color.analyze_artifact_colors(
        "nydeli",
        realization="shape_ornament",
    )
    assert analysis is expected_analysis


def test_requested_artwork_realization_targets_registered_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit Artwork color analysis targets only the existing registered Artwork
    manifest required for analysis and does not execute manufacturing.
    """
    discovery_plan = SimpleNamespace(
        artifact_id="nydeli",
        model_name="artwork",
        realization_name="artwork_default",
        resolver=object(),
        stages=(),
    )
    manifest = tmp_path / "products.json"
    manifest.write_text("{}", encoding="utf-8")
    targeted_plan = SimpleNamespace(
        resolver=object(),
        stages=(
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )
    planned: list[tuple[str, str, tuple[ProductRef, ...] | None, Path]] = []

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str,
        targets: tuple[ProductRef, ...] | None = None,
        project_root: Path,
    ) -> object:
        planned.append((artifact_id, realization, targets, project_root))
        if targets is None:
            return discovery_plan
        return targeted_plan

    expected_analysis = object()
    monkeypatch.setattr(cmd_color, "create_build_plan", fake_create_build_plan)

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        fail_execute,
        raising=False,
    )
    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        lambda *, manifest, resolver: expected_analysis,
    )
    monkeypatch.chdir(tmp_path)
    analysis = cmd_color.analyze_artifact_colors(
        "nydeli",
        realization="artwork_default",
    )
    assert analysis is expected_analysis
    assert planned == [
        ("nydeli", "artwork_default", None, tmp_path),
        (
            "nydeli",
            "artwork_default",
            (
                ProductRef(
                    artifact="nydeli",
                    model="artwork",
                    realization="artwork_default",
                    stage="vector",
                    product="manifest",
                ),
            ),
            tmp_path,
        ),
    ]


def test_shape_color_analysis_uses_resolved_configuration_without_execution(
    monkeypatch,
) -> None:
    """
    Shape color analysis consumes the selected Realization's resolved
    configuration directly.

    Structural semantic-color inspection does not require Shape manufacturing
    merely to obtain color information already available through the resolver.
    """

    resolver = object()

    plan = Mock(
        spec=BuildPlan,
    )

    plan.resolver = resolver
    plan.planned_product_dependencies = ()

    expected_analysis = object()

    def fake_analyze_shape_colors(
        *,
        resolver,
        artwork,
    ) -> object:
        assert resolver is plan.resolver
        assert artwork is None

        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_shape_colors",
        fake_analyze_shape_colors,
        raising=False,
    )

    analysis = cmd_color._analyze_shape_colors(
        plan,
    )

    assert analysis is expected_analysis


def test_shape_color_analysis_preserves_participating_artwork_analysis(
    monkeypatch,
) -> None:
    """
    Shape color analysis supplies participating Artwork analysis separately
    from Shape-owned structural semantic-color analysis.
    """
    resolver = object()
    plan = Mock(
        spec=BuildPlan,
    )
    plan.resolver = resolver
    artwork_analysis = object()
    expected_analysis = object()
    monkeypatch.setattr(
        cmd_color,
        "_analyze_shape_artwork_colors",
        lambda selected_plan: artwork_analysis,
        raising=False,
    )

    def fake_analyze_shape_colors(
        *,
        resolver,
        artwork,
    ) -> object:
        assert resolver is plan.resolver
        assert artwork is artwork_analysis
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_shape_colors",
        fake_analyze_shape_colors,
    )
    analysis = cmd_color._analyze_shape_colors(
        plan,
    )
    assert analysis is expected_analysis


def test_shape_artwork_analysis_uses_bound_artwork_dependency(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Shape color analysis obtains participating Artwork from the Shape
    Realization's bound registered-Artwork product dependency without executing
    manufacturing.
    """
    dependency = SimpleNamespace(
        binding=SimpleNamespace(
            artifact="source-artwork",
            realization="custom-artwork",
        ),
        product_ref=ProductRef(
            artifact="source-artwork",
            model="artwork",
            realization="custom-artwork",
            stage="vector",
            product="manifest",
        ),
    )
    shape_plan = Mock(spec=BuildPlan)
    shape_plan.artifact_id = "nydeli"
    shape_plan.project_root = tmp_path
    shape_plan.planned_product_dependencies = (dependency,)
    manifest = tmp_path / "registered" / "products.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")
    artwork_resolver = object()
    artwork_plan = SimpleNamespace(
        resolver=artwork_resolver,
        stages=(
            SimpleNamespace(
                name="vector",
                products=(SimpleNamespace(name="manifest", path=manifest),),
            ),
        ),
    )
    planned: list[tuple[object, Path]] = []
    expected_analysis = object()

    def fake_create_product_dependency_build_plan(
        selected_dependency,
        *,
        project_root: Path,
    ) -> object:
        planned.append((selected_dependency, project_root))
        return artwork_plan

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("COLORS must not execute manufacturing.")

    def fake_analyze_registered_artwork_colors(
        *,
        manifest: Path,
        resolver,
    ) -> object:
        assert manifest.is_file()
        assert resolver is artwork_resolver
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "create_product_dependency_build_plan",
        fake_create_product_dependency_build_plan,
        raising=False,
    )
    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        fail_execute,
        raising=False,
    )
    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )
    analysis = cmd_color._analyze_shape_artwork_colors(shape_plan)
    assert analysis is expected_analysis
    assert planned == [(dependency, tmp_path)]


@pytest.mark.parametrize(
    "recolor",
    (
        "printer",
        "library",
        "reset",
        "reset-all-realizations",
    ),
)
def test_colors_accepts_supported_recolor_selections(
    monkeypatch,
    recolor: str,
) -> None:
    """
    The colors command accepts every supported operator recolor selection.
    """
    requested: list[
        tuple[
            str,
            str | None,
            str | None,
        ]
    ] = []
    expected_analysis = object()

    def fake_run_colors(
        artifact_id: str,
        *,
        realization: str | None,
        recolor: str | None,
    ) -> object:
        requested.append(
            (
                artifact_id,
                realization,
                recolor,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "discover_artifacts",
        lambda *, project_root: (
            ArtifactState(
                artifact_id="nydeli",
                original_path=project_root / "originals" / "nydeli.png",
                materialized=True,
            ),
        ),
    )
    monkeypatch.setattr(
        cmd_color,
        "run_colors",
        fake_run_colors,
        raising=False,
    )
    monkeypatch.setattr(
        cmd_color,
        "display_color_analysis",
        lambda analysis: None,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
            f"--recolor={recolor}",
        ],
    )
    assert result.exit_code == 0
    assert requested == [
        (
            "nydeli",
            None,
            recolor,
        )
    ]


def test_colors_rejects_catalog_as_recolor_selection() -> None:
    """
    Catalog color analysis is advisory and cannot be selected for recoloring.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
            "--recolor=catalog",
        ],
    )
    assert result.exit_code != 0
    assert "catalog" in result.output


def test_colors_rejects_unknown_recolor_selection() -> None:
    """
    Recolor accepts only the explicitly supported operator selections.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
            "--recolor=unknown",
        ],
    )
    assert result.exit_code != 0
    assert "unknown" in result.output


def test_colors_rejects_reset_all_realizations_with_realization() -> None:
    """
    reset-all-realizations cannot be combined with one selected Realization.
    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
            "--realization",
            "shape_ornament",
            "--recolor=reset-all-realizations",
        ],
    )
    assert result.exit_code != 0
    assert "reset-all-realizations" in result.output
    assert "--realization" in result.output


def test_colors_rejects_registered_unmaterialized_artifact_without_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    COLORS does not perform expensive manufacturing work merely to inspect
    an ingested Artifact.
    A registered but unmaterialized Artifact is reported as requiring a
    BUILD. The command must not materialize the Artifact or realize any
    Products as a side effect.
    """
    from PIL import Image

    monkeypatch.chdir(
        tmp_path,
    )
    originals = tmp_path / "originals"
    originals.mkdir()
    original = originals / "nydeli.png"
    Image.new(
        "RGB",
        (16, 16),
        (255, 255, 255),
    ).save(
        original,
    )
    artifact_dir = tmp_path / "artifacts" / "nydeli"
    assert original.is_file()
    assert not artifact_dir.exists()
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
        ],
    )
    assert result.exit_code != 0
    assert "Artifact 'nydeli' is not materialized." in result.output
    assert "Try: artifact build nydeli" in result.output
    assert original.is_file()
    assert not artifact_dir.exists()


def test_colors_does_not_build_missing_vector_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    COLORS consumes existing color-analysis products; it does not manufacture
    missing products.

    A materialized Artifact whose registered Artwork manifest does not yet
    exist requires BUILD rather than causing COLORS to execute the expensive
    Prepare/Raster/Vector dependency chain.
    """

    from PIL import Image

    from lowkey_artifact_builder.config.artifact import materialize_artifact

    monkeypatch.chdir(tmp_path)

    originals = tmp_path / "originals"
    originals.mkdir()

    original = originals / "nydeli.png"

    Image.new(
        "RGB",
        (16, 16),
        (255, 255, 255),
    ).save(original)

    materialize_artifact(
        "nydeli",
        project_root=tmp_path,
    )

    artifact_dir = tmp_path / "artifacts" / "nydeli"

    assert artifact_dir.is_dir()

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
        ],
    )

    assert result.exit_code != 0
    assert "Try: artifact build nydeli" in result.output

    generated_dir = artifact_dir / "generated"

    assert not generated_dir.exists()


def test_colors_rejects_undefined_artifact_as_undefined(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An explicitly selected Artifact that is not registered remains an
    undefined-Artifact error rather than being reported as unmaterialized.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "missing",
        ],
    )
    assert result.exit_code != 0
    assert "Artifact 'missing' is not defined." in result.output
    assert "not materialized" not in result.output
    assert "Try: artifact build missing" not in result.output


def test_colors_allows_materialized_artifact_past_lifecycle_preflight(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    COLORS lifecycle preflight permits a registered, materialized Artifact to
    proceed to the color operation.
    """
    from PIL import Image

    from lowkey_artifact_builder.config.artifact import materialize_artifact

    monkeypatch.chdir(tmp_path)
    originals = tmp_path / "originals"
    originals.mkdir()
    original = originals / "nydeli.png"
    Image.new(
        "RGB",
        (16, 16),
        (255, 255, 255),
    ).save(original)
    materialize_artifact(
        "nydeli",
        project_root=tmp_path,
    )
    called = False

    def fake_run_colors(
        artifact_id: str | None,
        *,
        realization: str | None = None,
        recolor: str | None = None,
    ):
        nonlocal called
        called = True
        assert artifact_id == "nydeli"
        assert realization is None
        assert recolor is None
        raise RuntimeError("color operation reached")

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.run_colors",
        fake_run_colors,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
        ],
    )
    assert called
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "color operation reached"
