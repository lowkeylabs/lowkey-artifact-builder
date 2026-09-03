"""
Tests for the color-analysis CLI command.
"""
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


def test_analyze_artifact_colors_targets_registered_artwork_manifest(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis plans only the registered Artwork manifest it requires.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

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

    planned: list[
        tuple[
            str,
            str,
            tuple[ProductRef, ...],
            Path,
        ]
    ] = []

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

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        lambda plan: object(),
        raising=False,
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


def test_analyze_artifact_colors_realizes_target_before_analysis(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Color analysis realizes its targeted Artwork products before reading them.

    Realization uses normal dependency-aware build orchestration rather than
    directly invoking Artwork producer stages.
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

    actions: list[tuple[str, object]] = []

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )

    def fake_execute_dependency_build(
        build_plan,
    ) -> object:
        assert build_plan is plan

        actions.append(
            (
                "execute",
                build_plan,
            )
        )

        manifest.write_text(
            "{}",
            encoding="utf-8",
        )

        return object()

    def fake_analyze_registered_artwork_colors(
        *,
        manifest: Path,
        resolver,
    ) -> object:
        assert manifest.is_file()

        actions.append(
            (
                "analyze",
                manifest,
            )
        )

        return expected_analysis

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fake_execute_dependency_build,
        raising=False,
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

    assert actions == [
        (
            "execute",
            plan,
        ),
        (
            "analyze",
            manifest,
        ),
    ]


def test_analyze_artifact_colors_reuses_current_registered_artwork(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Current persistent Artwork remains subject to normal incremental execution.

    Color analysis does not invent its own filesystem-existence shortcut.
    The targeted plan is still passed through normal orchestration, which owns
    the decision to reuse current products without producer execution.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"
    manifest.write_text(
        "{}",
        encoding="utf-8",
    )

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

    executed: list[object] = []
    analyzed: list[tuple[Path, object]] = []

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, realization, targets, project_root: plan,
    )

    def fake_execute_dependency_build(
        build_plan,
    ) -> object:
        executed.append(
            build_plan,
        )
        return object()

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

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fake_execute_dependency_build,
        raising=False,
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
    assert executed == [plan]
    assert analyzed == [
        (
            manifest,
            resolver,
        )
    ]


def test_analyze_artifact_colors_does_not_modify_configuration(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Demand-driven color analysis remains a read-only configuration diagnostic.
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

    def fake_execute_dependency_build(
        build_plan,
    ) -> object:
        assert build_plan is plan

        manifest.write_text(
            "{}",
            encoding="utf-8",
        )

        return object()

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fake_execute_dependency_build,
        raising=False,
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


def test_analyze_artifact_colors_does_not_require_standalone_artwork_stages(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Demand-driven color analysis stops at registered Artwork.

    The targeted plan may contain prepare, raster, and vector, but standalone
    extrusion and packaging are not requested merely to perform analysis.
    """

    from lowkey_artifact_builder.cli.cmd_color import (
        analyze_artifact_colors,
    )

    manifest = tmp_path / "products.json"

    plan = SimpleNamespace(
        resolver=object(),
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

        return plan

    def fake_execute_dependency_build(
        build_plan,
    ) -> object:
        assert build_plan is plan

        stage_names = tuple(stage.name for stage in build_plan.stages)

        assert stage_names == (
            "prepare",
            "raster",
            "vector",
        )
        assert "extrude" not in stage_names
        assert "package" not in stage_names

        manifest.write_text(
            "{}",
            encoding="utf-8",
        )

        return object()

    _patch_artwork_identity_resolver(
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.execute_dependency_build",
        fake_execute_dependency_build,
        raising=False,
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


def test_analyze_artifact_colors_propagates_realization_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Color analysis stops when required product realization fails.

    A failure from normal dependency-aware build orchestration propagates
    rather than allowing analysis to continue against an unavailable
    registered Artwork manifest.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    resolver = Mock()

    resolver.side_effect = lambda name: {
        "model": "artwork",
        "realization": "default",
    }[name]

    monkeypatch.setattr(
        cmd_color,
        "get_resolver",
        Mock(
            return_value=resolver,
        ),
    )

    manifest = tmp_path / "registered" / "products.json"

    plan = Mock()
    plan.resolver = resolver
    plan.stages = (
        Mock(
            name="vector",
            products=(
                Mock(
                    name="manifest",
                    path=manifest,
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "create_build_plan",
        Mock(
            return_value=plan,
        ),
    )

    realization_error = RuntimeError("registered Artwork realization failed")

    execute = Mock(
        side_effect=realization_error,
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        execute,
    )

    analyze = Mock()

    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        analyze,
    )

    with pytest.raises(
        RuntimeError,
        match="registered Artwork realization failed",
    ):
        cmd_color.analyze_artifact_colors(
            "nydeli",
        )

    execute.assert_called_once_with(
        plan,
    )

    analyze.assert_not_called()
