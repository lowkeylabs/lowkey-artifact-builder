"""
Tests for the color-analysis CLI command.
"""
# File: tests/cli/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.model import ProductRef

# =========================================================
# Test support
# =========================================================


def _patch_artwork_identity_resolver(
    monkeypatch,
) -> None:
    """
    Resolve the configured Artwork identity used by color-analysis tests.
    """

    def fake_get_resolver(
        artifact_id: str,
        *,
        project_root,
    ):
        assert artifact_id == "nydeli"

        values = {
            "model": "artwork",
            "realization": "default",
        }

        return values.__getitem__

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.get_resolver",
        fake_get_resolver,
    )


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


def test_colors_requires_an_artifact_id() -> None:
    """
    Color analysis identifies the artifact whose registered Artwork is analyzed.
    """

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["colors"],
    )

    assert result.exit_code != 0
    assert "ARTIFACT_ID" in result.output


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
    ) -> object:
        analyzed.append(
            artifact_id,
        )
        return expected_analysis

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


def test_analyze_artifact_colors_uses_registered_artwork_manifest(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Artifact color analysis consumes the planned registered Artwork manifest.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    resolver = object()
    expected_analysis = object()

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

    planned: list[
        tuple[
            str,
            str,
            tuple[ProductRef, ...],
            Path,
        ]
    ] = []
    analyzed: list[tuple[object, object]] = []

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str,
        targets: tuple[ProductRef, ...],
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
        return plan

    def fake_analyze_registered_artwork_colors(
        *,
        manifest,
        resolver,
    ) -> object:
        analyzed.append(
            (
                manifest,
                resolver,
            )
        )
        return expected_analysis

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )
    monkeypatch.chdir(
        tmp_path,
    )

    result = analyze_artifact_colors(
        "nydeli",
    )

    assert result is expected_analysis
    assert len(planned) == 1

    artifact_id, realization, targets, project_root = planned[0]

    assert artifact_id == "nydeli"
    assert realization == "default"
    assert project_root == tmp_path

    assert len(targets) == 1

    target = targets[0]

    assert target.artifact == "nydeli"
    assert target.model == "artwork"
    assert target.realization == "default"
    assert target.stage == "vector"
    assert target.product == "manifest"

    assert analyzed == [
        (
            manifest,
            resolver,
        )
    ]


def test_analyze_artifact_colors_does_not_execute_build(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis reads persistent Artwork products without executing a build.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"

    plan = SimpleNamespace(
        resolver=object(),
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

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: object(),
    )

    def fail_execute(
        *args,
        **kwargs,
    ) -> None:
        raise AssertionError("color analysis must not execute a build")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.execute_build",
        fail_execute,
    )
    monkeypatch.chdir(
        tmp_path,
    )

    analyze_artifact_colors(
        "nydeli",
    )


def test_analyze_artifact_colors_does_not_modify_configuration(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis is a read-only configuration diagnostic.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"

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
                products=(
                    SimpleNamespace(
                        name="manifest",
                        path=manifest,
                    ),
                ),
            ),
        ),
    )

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: object(),
    )

    def fail_write(
        *args,
        **kwargs,
    ) -> None:
        raise AssertionError("color analysis must not modify configuration")

    monkeypatch.setattr(
        "lowkey_artifact_builder.config.write_artifact_config",
        fail_write,
    )

    monkeypatch.chdir(
        tmp_path,
    )

    analyze_artifact_colors(
        "nydeli",
    )


def test_analyze_artifact_colors_does_not_require_standalone_artwork_configuration(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Registered Artwork color analysis does not require standalone stages.

    Color analysis requires the registered vector manifest, so standalone
    extrusion and packaging must not participate in the requested plan.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    planned_targets: list[tuple[ProductRef, ...]] = []

    manifest = tmp_path / "products.json"
    resolver = object()

    plan = SimpleNamespace(
        resolver=resolver,
        stages=(
            SimpleNamespace(
                name="prepare",
                products=(),
            ),
            SimpleNamespace(
                name="raster",
                products=(),
            ),
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

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str | None = None,
        targets: tuple[ProductRef, ...] | None = None,
        project_root: Path,
    ) -> object:
        assert artifact_id == "nydeli"
        assert realization == "default"
        assert project_root == tmp_path

        if targets is None:
            raise AssertionError("color analysis must not request a complete Artwork plan")

        planned_targets.append(
            targets,
        )

        return plan

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: object(),
    )

    monkeypatch.chdir(
        tmp_path,
    )

    analyze_artifact_colors(
        "nydeli",
    )

    assert len(planned_targets) == 1

    targets = planned_targets[0]

    assert len(targets) == 1

    target = targets[0]

    assert target.artifact == "nydeli"
    assert target.model == "artwork"
    assert target.realization == "default"
    assert target.stage == "vector"
    assert target.product == "manifest"
