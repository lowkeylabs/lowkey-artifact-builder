"""
Tests for the color-analysis CLI command.
"""
# File: tests/cli/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli


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
    Color analysis identifies the artifact whose prepared Artwork is analyzed.
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
    The colors command obtains structured analysis and displays it.
    """

    analyzed: list[str] = []
    displayed: list[object] = []

    expected_matches = object()

    def fake_analyze_artifact_colors(
        artifact_id: str,
    ) -> object:
        analyzed.append(artifact_id)
        return expected_matches

    def fake_display_color_matches(
        matches: object,
    ) -> None:
        displayed.append(matches)

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.display_color_matches",
        fake_display_color_matches,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["colors", "nydeli"],
    )

    assert result.exit_code == 0
    assert analyzed == ["nydeli"]
    assert displayed == [expected_matches]


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
    expected_matches = object()

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

    planned: list[tuple[str, object]] = []
    analyzed: list[tuple[object, object]] = []

    def fake_create_build_plan(
        artifact_id: str,
        *,
        project_root,
    ) -> object:
        planned.append(
            (
                artifact_id,
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
        return expected_matches

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        fake_create_build_plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )
    monkeypatch.chdir(tmp_path)

    result = analyze_artifact_colors("nydeli")

    assert result is expected_matches
    assert planned == [
        (
            "nydeli",
            tmp_path,
        )
    ]
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

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.create_build_plan",
        lambda artifact_id, *, project_root: plan,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_registered_artwork_colors",
        lambda *, manifest, resolver: (),
    )

    def fail_execute(*args, **kwargs) -> None:
        raise AssertionError("color analysis must not execute a build")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.execute_build",
        fail_execute,
    )
    monkeypatch.chdir(tmp_path)

    analyze_artifact_colors("nydeli")
