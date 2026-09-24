"""
Tests for operator recoloring through the colors command.
"""
# File: tests/cli/test_recolor.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest

import lowkey_artifact_builder.cli.cmd_color as cmd_color
from lowkey_artifact_builder.colors import (
    ColorAssignment,
    ColorAssignmentResult,
    MeasuredColor,
    PaletteColor,
)
from lowkey_artifact_builder.config import (
    load_artifact_config,
)
from lowkey_artifact_builder.engine import BuildPlan
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)

# =========================================================
# Printer recolor
# =========================================================


def test_recolor_printer_persists_system_palette_at_artifact_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    printer recolor pins the system/default printer palette at Artifact scope.

    The selected palette comes from unresolved system configuration rather
    than the Artifact's currently effective printer_colors.
    """

    resolver = Mock()
    resolver.system_value.return_value = [
        "system-black",
        "system-white",
        "system-red",
    ]
    resolver.return_value = [
        "artifact-black",
        "artifact-white",
        "artifact-blue",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
        raising=False,
    )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        lambda artifact_id, *, project_root: (),
    )

    persisted: list[
        tuple[
            str,
            str | None,
            tuple[str, ...],
            Path,
        ]
    ] = []

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        persisted.append(
            (
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
        raising=False,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        recolor="printer",
    )

    assert analysis is expected_analysis

    resolver.system_value.assert_called_once_with(
        "printer_colors",
    )

    resolver.assert_not_called()

    assert persisted == [
        (
            "nydeli",
            None,
            (
                "system-black",
                "system-white",
                "system-red",
            ),
            tmp_path,
        )
    ]


def test_recolor_printer_persists_system_palette_at_realization_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped printer recolor pins the system/default printer palette
    only at the selected Realization scope.
    """

    resolver = Mock()
    resolver.system_value.return_value = [
        "system-black",
        "system-white",
        "system-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
        raising=False,
    )

    persisted: list[
        tuple[
            str,
            str | None,
            tuple[str, ...],
            Path,
        ]
    ] = []

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        persisted.append(
            (
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
        raising=False,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda artifact_id, *, realization, project_root: None,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        realization="shape_ornament",
        recolor="printer",
    )

    assert analysis is expected_analysis

    resolver.system_value.assert_called_once_with(
        "printer_colors",
    )

    assert persisted == [
        (
            "nydeli",
            "shape_ornament",
            (
                "system-black",
                "system-white",
                "system-red",
            ),
            tmp_path,
        )
    ]


# =========================================================
# Printer-color persistence
# =========================================================


def test_persist_printer_colors_updates_artifact_scope(
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped persistence stores printer_colors at Artifact scope while
    preserving unrelated Artifact configuration.
    """

    path = tmp_path / "artifacts" / "nydeli" / "artifact.toml"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        """
model = "artwork"
source = "nydeli.png"
artwork_size = 90.0
printer_colors = ["old-black", "old-white"]

[realizations.shape_ornament]
variant = "shape.ornament"
printer_colors = ["ornament-black", "ornament-red"]
""".lstrip(),
        encoding="utf-8",
    )

    cmd_color._persist_printer_colors(
        "nydeli",
        realization=None,
        printer_colors=(
            "system-black",
            "system-white",
            "system-red",
        ),
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config["printer_colors"] == [
        "system-black",
        "system-white",
        "system-red",
    ]

    assert config["source"] == "nydeli.png"
    assert config["artwork_size"] == 90.0

    assert config["realizations"]["shape_ornament"]["printer_colors"] == [
        "ornament-black",
        "ornament-red",
    ]


def test_persist_printer_colors_updates_realization_scope(
    tmp_path: Path,
) -> None:
    """
    Realization-scoped persistence stores printer_colors only on the selected
    Realization while preserving Artifact and sibling Realization values.
    """

    path = tmp_path / "artifacts" / "nydeli" / "artifact.toml"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        """
model = "artwork"
source = "nydeli.png"
printer_colors = ["artifact-black", "artifact-white"]

[realizations.shape_default]
variant = "shape.default"
printer_colors = ["default-black", "default-white"]

[realizations.shape_ornament]
variant = "shape.ornament"
shape_size = 95.0
printer_colors = ["ornament-black", "ornament-red"]
""".lstrip(),
        encoding="utf-8",
    )

    cmd_color._persist_printer_colors(
        "nydeli",
        realization="shape_ornament",
        printer_colors=(
            "system-black",
            "system-white",
            "system-red",
        ),
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config["printer_colors"] == [
        "artifact-black",
        "artifact-white",
    ]

    assert config["realizations"]["shape_default"] == {
        "variant": "shape.default",
        "printer_colors": [
            "default-black",
            "default-white",
        ],
    }

    assert config["realizations"]["shape_ornament"] == {
        "variant": "shape.ornament",
        "shape_size": 95.0,
        "printer_colors": [
            "system-black",
            "system-white",
            "system-red",
        ],
    }


def test_recolor_library_persists_library_palette_at_artifact_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    library recolor pins the effective Library palette at Artifact scope.
    """

    resolver = Mock()
    resolver.return_value = [
        "library-black",
        "library-white",
        "library-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
        raising=False,
    )

    persisted: list[
        tuple[
            str,
            str | None,
            tuple[str, ...],
            Path,
        ]
    ] = []

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        persisted.append(
            (
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        lambda artifact_id, *, project_root: (),
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        recolor="library",
    )

    assert analysis is expected_analysis

    resolver.assert_called_once_with(
        "library_colors",
    )

    resolver.system_value.assert_not_called()

    assert persisted == [
        (
            "nydeli",
            None,
            (
                "library-black",
                "library-white",
                "library-red",
            ),
            tmp_path,
        )
    ]


def test_recolor_library_persists_library_palette_at_realization_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped library recolor pins the effective Library palette only
    at the selected Realization scope.
    """

    resolver = Mock()
    resolver.return_value = [
        "library-black",
        "library-white",
        "library-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
        raising=False,
    )

    persisted: list[
        tuple[
            str,
            str | None,
            tuple[str, ...],
            Path,
        ]
    ] = []

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        persisted.append(
            (
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda artifact_id, *, realization, project_root: None,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        realization="shape_ornament",
        recolor="library",
    )

    assert analysis is expected_analysis

    resolver.assert_called_once_with(
        "library_colors",
    )

    resolver.system_value.assert_not_called()

    assert persisted == [
        (
            "nydeli",
            "shape_ornament",
            (
                "library-black",
                "library-white",
                "library-red",
            ),
            tmp_path,
        )
    ]


def test_persist_printer_colors_preserves_artifact_document_presentation(
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped printer-color persistence preserves existing comments and
    surrounding Artifact configuration presentation.
    """

    path = tmp_path / "artifacts" / "nydeli" / "artifact.toml"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        """
model = "artwork"

# Preserve this source explanation.
source = "nydeli.png"

# Existing printer selection.
printer_colors = ["old-black", "old-white"]
""".lstrip(),
        encoding="utf-8",
    )

    cmd_color._persist_printer_colors(
        "nydeli",
        realization=None,
        printer_colors=(
            "system-black",
            "system-white",
            "system-red",
        ),
        project_root=tmp_path,
    )

    text = path.read_text(
        encoding="utf-8",
    )

    assert "# Preserve this source explanation." in text
    assert "# Existing printer selection." in text
    assert 'source = "nydeli.png"' in text


def test_recolor_reset_removes_artifact_printer_colors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped reset removes the Artifact printer_colors override and
    restores normal inheritance.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    reset: list[
        tuple[
            str,
            str | None,
            Path,
        ]
    ] = []

    def fake_reset_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> None:
        reset.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_reset_printer_colors",
        fake_reset_printer_colors,
        raising=False,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        recolor="reset",
    )

    assert analysis is expected_analysis

    assert reset == [
        (
            "nydeli",
            None,
            tmp_path,
        )
    ]


def test_recolor_reset_removes_realization_printer_colors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped reset removes only the selected Realization's
    printer_colors override and restores inheritance for that Realization.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    reset: list[
        tuple[
            str,
            str | None,
            Path,
        ]
    ] = []

    def fake_reset_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> None:
        reset.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_reset_printer_colors",
        fake_reset_printer_colors,
        raising=False,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda artifact_id, *, realization, project_root: None,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        realization="shape_ornament",
        recolor="reset",
    )

    assert analysis is expected_analysis

    assert reset == [
        (
            "nydeli",
            "shape_ornament",
            tmp_path,
        )
    ]


def test_recolor_reset_all_realizations_removes_realization_printer_colors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    reset-all-realizations removes printer_colors from every Realization
    customization in the selected Artifact scope.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    reset: list[
        tuple[
            str,
            Path,
        ]
    ] = []

    def fake_reset_all_realization_printer_colors(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> None:
        reset.append(
            (
                artifact_id,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_reset_all_realization_printer_colors",
        fake_reset_all_realization_printer_colors,
        raising=False,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        recolor="reset-all-realizations",
    )

    assert analysis is expected_analysis

    assert reset == [
        (
            "nydeli",
            tmp_path,
        )
    ]


def test_artifact_recolor_reports_retained_realization_printer_colors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped recolor reports Realization-specific printer_colors
    overrides that remain authoritative after Artifact-level persistence.
    """

    resolver = Mock()
    resolver.system_value.return_value = [
        "system-black",
        "system-white",
        "system-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        lambda artifact_id, *, project_root: (),
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda artifact_id, *, realization, printer_colors, project_root: None,
    )

    monkeypatch.setattr(
        cmd_color,
        "get_realization_configurations_with_value",
        lambda artifact_id, name, *, project_root: (
            "shape_default",
            "shape_ornament",
        ),
        raising=False,
    )

    reported: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_realization_printer_colors",
        lambda realizations: reported.append(realizations),
        raising=False,
    )

    expected_analysis = object()

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: expected_analysis,
    )

    analysis = cmd_color.run_colors(
        "nydeli",
        recolor="printer",
    )

    assert analysis is expected_analysis

    assert reported == [
        (
            "shape_default",
            "shape_ornament",
        )
    ]


def test_artifact_library_recolor_reports_retained_realization_printer_colors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped Library recolor reports Realization-specific printer_colors
    overrides that remain authoritative.
    """

    resolver = Mock()
    resolver.return_value = [
        "library-black",
        "library-white",
        "library-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda artifact_id, *, realization, printer_colors, project_root: None,
    )

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        lambda artifact_id, *, project_root: (),
    )

    reported: list[str] = []

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_printer_color_overrides",
        lambda artifact_id, *, project_root: reported.append(artifact_id),
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: object(),
    )

    cmd_color.run_colors(
        "nydeli",
        recolor="library",
    )

    assert reported == [
        "nydeli",
    ]


def test_realization_recolor_does_not_report_other_realization_overrides(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped recolor does not issue the Artifact-scope retained
    override report.
    """

    resolver = Mock()
    resolver.system_value.return_value = [
        "system-black",
        "system-white",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda artifact_id, *, realization, printer_colors, project_root: None,
    )

    reported: list[str] = []

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_printer_color_overrides",
        lambda artifact_id, *, project_root: reported.append(artifact_id),
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        lambda artifact_id, *, realization: object(),
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda artifact_id, *, realization, project_root: None,
    )

    cmd_color.run_colors(
        "nydeli",
        realization="shape_ornament",
        recolor="printer",
    )

    assert reported == []


def test_retained_printer_color_overrides_are_silent_when_none_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact recolor emits no retained-override report when no explicit
    Realization printer_colors overrides exist.
    """

    monkeypatch.setattr(
        cmd_color,
        "get_realization_configurations_with_value",
        lambda artifact_id, name, *, project_root: (),
    )

    reported: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_realization_printer_colors",
        lambda realizations: reported.append(realizations),
    )

    cmd_color._report_retained_printer_color_overrides(
        "nydeli",
        project_root=tmp_path,
    )

    assert reported == []


def test_recolor_existing_artwork_final_uses_effective_printer_assignments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Recoloring an Artwork Realization updates its existing final 3MF from
    effective Printer assignments without executing build stages.
    """

    final_path = tmp_path / "dog.artwork_default.3mf"
    final_path.touch()

    printer_assignments = ColorAssignmentResult(
        assignments=(
            ColorAssignment(
                measured=MeasuredColor(
                    index=1,
                    rgb=(200, 0, 0),
                ),
                color=PaletteColor(
                    name="fire-engine-red",
                    rgb=(220, 38, 38),
                ),
                distance=1.0,
            ),
            ColorAssignment(
                measured=MeasuredColor(
                    index=2,
                    rgb=(250, 250, 250),
                ),
                color=PaletteColor(
                    name="cold-white",
                    rgb=(245, 245, 240),
                ),
                distance=2.0,
            ),
        ),
        distance=3.0,
    )

    analysis = ArtworkColorAnalysis(
        system_assignments=printer_assignments,
        printer_assignments=printer_assignments,
        library_assignments=printer_assignments,
        catalog_assignments=printer_assignments,
    )

    plan = SimpleNamespace(
        artifact_id="dog",
        realization_name="artwork_default",
        model_name="artwork",
        stages=(
            SimpleNamespace(
                name="package",
                products=(
                    SimpleNamespace(
                        name="artifact",
                        path=final_path,
                    ),
                ),
            ),
        ),
    )

    updates: list[
        tuple[
            Path,
            str,
            dict[str, PaletteColor],
        ]
    ] = []

    monkeypatch.setattr(
        cmd_color,
        "_resolve_existing_final_realization",
        lambda artifact_id, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_analyze_existing_artwork_colors",
        lambda resolved_plan: analysis,
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda path, *, artifact_id, colors: updates.append(
            (
                path,
                artifact_id,
                colors,
            )
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail("recoloring must not execute build stages"),
    )

    cmd_color._recolor_existing_final(
        "dog",
        realization="artwork_default",
        project_root=tmp_path,
    )

    assert updates == [
        (
            final_path,
            "dog",
            {
                "artwork-1": PaletteColor(
                    name="fire-engine-red",
                    rgb=(220, 38, 38),
                ),
                "artwork-2": PaletteColor(
                    name="cold-white",
                    rgb=(245, 245, 240),
                ),
            },
        )
    ]


def test_recolor_existing_shape_final_updates_only_artwork_assignments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Recoloring a Shape Realization updates participating Artwork components
    from effective Printer assignments without replacing Shape-owned semantic
    colors or executing build stages.
    """

    final_path = tmp_path / "dog.shape_ornament.3mf"
    final_path.touch()

    printer_assignments = ColorAssignmentResult(
        assignments=(
            ColorAssignment(
                measured=MeasuredColor(
                    index=1,
                    rgb=(200, 0, 0),
                ),
                color=PaletteColor(
                    name="fire-engine-red",
                    rgb=(220, 38, 38),
                ),
                distance=1.0,
            ),
            ColorAssignment(
                measured=MeasuredColor(
                    index=2,
                    rgb=(250, 250, 250),
                ),
                color=PaletteColor(
                    name="cold-white",
                    rgb=(245, 245, 240),
                ),
                distance=2.0,
            ),
        ),
        distance=3.0,
    )

    artwork = ArtworkColorAnalysis(
        system_assignments=printer_assignments,
        printer_assignments=printer_assignments,
        library_assignments=printer_assignments,
        catalog_assignments=printer_assignments,
    )

    plan = SimpleNamespace(
        artifact_id="dog",
        realization_name="shape_ornament",
        model_name="shape",
        stages=(
            SimpleNamespace(
                name="package",
                products=(
                    SimpleNamespace(
                        name="artifact",
                        path=final_path,
                    ),
                ),
            ),
        ),
    )

    updates: list[
        tuple[
            Path,
            str,
            dict[str, PaletteColor],
        ]
    ] = []

    monkeypatch.setattr(
        cmd_color,
        "_resolve_existing_final_realization",
        lambda artifact_id, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_analyze_existing_shape_artwork_colors",
        lambda resolved_plan: artwork,
        raising=False,
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda path, *, artifact_id, colors: updates.append(
            (
                path,
                artifact_id,
                colors,
            )
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail("recoloring must not execute build stages"),
    )

    cmd_color._recolor_existing_final(
        "dog",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert updates == [
        (
            final_path,
            "dog",
            {
                "artwork-1": PaletteColor(
                    name="fire-engine-red",
                    rgb=(220, 38, 38),
                ),
                "artwork-2": PaletteColor(
                    name="cold-white",
                    rgb=(245, 245, 240),
                ),
            },
        )
    ]


def test_recolor_existing_shape_final_without_artwork_does_not_update_colors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    A Shape Realization without participating Artwork has no physical Artwork
    assignments to apply to its final 3MF.

    Shape-owned semantic colors are not recolor targets.
    """

    final_path = tmp_path / "dog.shape_ornament.3mf"
    final_path.touch()

    plan = SimpleNamespace(
        artifact_id="dog",
        realization_name="shape_ornament",
        model_name="shape",
        stages=(
            SimpleNamespace(
                name="package",
                products=(
                    SimpleNamespace(
                        name="artifact",
                        path=final_path,
                    ),
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_existing_final_realization",
        lambda artifact_id, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_analyze_existing_shape_artwork_colors",
        lambda resolved_plan: None,
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: pytest.fail("Shape-owned semantic colors must not be recolored"),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail("recoloring must not execute build stages"),
    )

    cmd_color._recolor_existing_final(
        "dog",
        realization="shape_ornament",
        project_root=tmp_path,
    )


def test_resolve_existing_final_realization_plans_without_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Existing-final recoloring may use normal planning to resolve the selected
    Realization and its product paths, but resolution must not execute build
    stages.
    """

    plan = SimpleNamespace(
        artifact_id="dog",
        realization_name="shape_ornament",
        model_name="shape",
    )

    calls: list[
        tuple[
            str,
            str,
            Path,
        ]
    ] = []

    def fake_create_build_plan(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> object:
        calls.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )
        return plan

    monkeypatch.setattr(
        cmd_color,
        "create_build_plan",
        fake_create_build_plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail(
            "resolving an existing final must not execute build stages"
        ),
    )

    result = cmd_color._resolve_existing_final_realization(
        "dog",
        "shape_ornament",
        tmp_path,
    )

    assert result is plan

    assert calls == [
        (
            "dog",
            "shape_ornament",
            tmp_path,
        )
    ]


def test_recolor_existing_final_rejects_missing_final_without_building(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Recoloring requires an already-existing final 3MF.

    A missing final product is a prerequisite failure and must not cause
    geometry-producing build stages to execute.
    """

    final_path = tmp_path / "dog.artwork_default.3mf"
    # note that there is NO TOUCH here!

    plan = SimpleNamespace(
        artifact_id="dog",
        realization_name="artwork_default",
        model_name="artwork",
        stages=(
            SimpleNamespace(
                name="package",
                products=(
                    SimpleNamespace(
                        name="artifact",
                        path=final_path,
                    ),
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_existing_final_realization",
        lambda artifact_id, realization, project_root: plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "_analyze_existing_artwork_colors",
        lambda resolved_plan: pytest.fail("missing final must be detected before color analysis"),
    )

    monkeypatch.setattr(
        cmd_color,
        "update_component_colors",
        lambda *args, **kwargs: pytest.fail("missing final must not be updated"),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail("missing final must not trigger build execution"),
    )

    with pytest.raises(
        RuntimeError,
        match="existing final 3MF",
    ):
        cmd_color._recolor_existing_final(
            "dog",
            realization="artwork_default",
            project_root=tmp_path,
        )


def test_analyze_existing_artwork_colors_uses_existing_manifest_without_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Existing-final recoloring analyzes an already-existing registered Artwork
    manifest without executing build stages to create or refresh it.
    """

    manifest_path = tmp_path / "registered-artwork.json"
    manifest_path.touch()

    resolver = object()

    plan = cast(
        BuildPlan,
        SimpleNamespace(
            resolver=resolver,
            stages=(
                SimpleNamespace(
                    name="vector",
                    products=(
                        SimpleNamespace(
                            name="manifest",
                            path=manifest_path,
                        ),
                    ),
                ),
            ),
        ),
    )

    expected = object()

    calls: list[
        tuple[
            Path,
            object,
        ]
    ] = []

    def fake_analyze_registered_artwork_colors(
        *,
        manifest: Path,
        resolver: object,
    ) -> object:
        calls.append(
            (
                manifest,
                resolver,
            )
        )
        return expected

    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail(
            "existing Artwork color analysis must not execute build stages"
        ),
    )

    result = cmd_color._analyze_existing_artwork_colors(
        plan,
    )

    assert result is expected

    assert calls == [
        (
            manifest_path,
            resolver,
        )
    ]


def test_analyze_existing_artwork_colors_rejects_missing_manifest_without_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Existing-final recoloring requires the registered Artwork manifest to
    already exist and must not rebuild it when it is missing.
    """

    manifest_path = tmp_path / "registered-artwork.json"

    plan = cast(
        BuildPlan,
        SimpleNamespace(
            resolver=object(),
            stages=(
                SimpleNamespace(
                    name="vector",
                    products=(
                        SimpleNamespace(
                            name="manifest",
                            path=manifest_path,
                        ),
                    ),
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        lambda *args, **kwargs: pytest.fail("missing manifest must not be analyzed"),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail("missing manifest must not trigger build execution"),
    )

    with pytest.raises(
        RuntimeError,
        match="registered Artwork manifest",
    ):
        cmd_color._analyze_existing_artwork_colors(
            plan,
        )


def test_analyze_existing_shape_artwork_colors_uses_bound_existing_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Existing-final Shape recoloring follows the Shape Realization's bound
    Artwork dependency and analyzes its already-existing registered manifest
    without executing build stages.
    """

    manifest_path = tmp_path / "bound-artwork-manifest.json"
    manifest_path.touch()

    dependency = SimpleNamespace(
        product_ref=SimpleNamespace(
            model="artwork",
            stage="vector",
            product="manifest",
        ),
    )

    artwork_resolver = object()

    artwork_plan = SimpleNamespace(
        resolver=artwork_resolver,
        stages=(
            SimpleNamespace(
                name="vector",
                products=(
                    SimpleNamespace(
                        name="manifest",
                        path=manifest_path,
                    ),
                ),
            ),
        ),
    )

    shape_plan = cast(
        BuildPlan,
        SimpleNamespace(
            project_root=tmp_path,
            planned_product_dependencies=(dependency,),
        ),
    )

    expected = object()

    dependency_calls: list[
        tuple[
            object,
            Path,
        ]
    ] = []

    def fake_create_product_dependency_build_plan(
        selected_dependency: object,
        *,
        project_root: Path,
    ) -> object:
        dependency_calls.append(
            (
                selected_dependency,
                project_root,
            )
        )
        return artwork_plan

    analysis_calls: list[
        tuple[
            Path,
            object,
        ]
    ] = []

    def fake_analyze_registered_artwork_colors(
        *,
        manifest: Path,
        resolver: object,
    ) -> object:
        analysis_calls.append(
            (
                manifest,
                resolver,
            )
        )
        return expected

    monkeypatch.setattr(
        cmd_color,
        "create_product_dependency_build_plan",
        fake_create_product_dependency_build_plan,
    )

    monkeypatch.setattr(
        cmd_color,
        "analyze_registered_artwork_colors",
        fake_analyze_registered_artwork_colors,
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail(
            "existing Shape recoloring must not execute build stages"
        ),
    )

    result = cmd_color._analyze_existing_shape_artwork_colors(
        shape_plan,
    )

    assert result is expected

    assert dependency_calls == [
        (
            dependency,
            tmp_path,
        )
    ]

    assert analysis_calls == [
        (
            manifest_path,
            artwork_resolver,
        )
    ]


def test_analyze_existing_shape_artwork_colors_returns_none_without_artwork_dependency(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    A Shape Realization without a participating Artwork dependency has no
    Artwork colors to apply during existing-final recoloring.
    """

    shape_plan = cast(
        BuildPlan,
        SimpleNamespace(
            project_root=tmp_path,
            planned_product_dependencies=(),
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "create_product_dependency_build_plan",
        lambda *args, **kwargs: pytest.fail("no Artwork producer plan should be created"),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail(
            "existing Shape recoloring must not execute build stages"
        ),
    )

    assert (
        cmd_color._analyze_existing_shape_artwork_colors(
            shape_plan,
        )
        is None
    )


def test_analyze_existing_shape_artwork_colors_rejects_multiple_artwork_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Existing-final Shape recoloring requires an unambiguous registered Artwork
    manifest dependency.
    """

    first_dependency = SimpleNamespace(
        product_ref=SimpleNamespace(
            model="artwork",
            stage="vector",
            product="manifest",
        ),
    )

    second_dependency = SimpleNamespace(
        product_ref=SimpleNamespace(
            model="artwork",
            stage="vector",
            product="manifest",
        ),
    )

    shape_plan = cast(
        BuildPlan,
        SimpleNamespace(
            project_root=tmp_path,
            planned_product_dependencies=(
                first_dependency,
                second_dependency,
            ),
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "create_product_dependency_build_plan",
        lambda *args, **kwargs: pytest.fail("ambiguous Artwork dependencies must not be followed"),
    )

    monkeypatch.setattr(
        cmd_color,
        "execute_dependency_build",
        lambda *args, **kwargs: pytest.fail(
            "existing Shape recoloring must not execute build stages"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="exactly one registered Artwork manifest dependency",
    ):
        cmd_color._analyze_existing_shape_artwork_colors(
            shape_plan,
        )


def test_recolor_library_updates_selected_realization_existing_final(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped library recoloring persists the selected palette,
    recolors that Realization's existing final 3MF, then reports analysis.
    """

    resolver = Mock()
    resolver.return_value = [
        "library-black",
        "library-white",
        "library-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    expected_analysis = object()
    events: list[tuple[object, ...]] = []

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
    )

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor",
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        events.append(
            (
                "analyze",
                artifact_id,
                realization,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )

    result = cmd_color.run_colors(
        "dog",
        realization="shape_ornament",
        recolor="library",
    )

    assert result is expected_analysis

    assert events == [
        (
            "persist",
            "dog",
            "shape_ornament",
            (
                "library-black",
                "library-white",
                "library-red",
            ),
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_ornament",
            tmp_path,
        ),
        (
            "analyze",
            "dog",
            "shape_ornament",
        ),
    ]


def test_recolor_printer_updates_selected_realization_existing_final(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped printer recoloring persists the System palette,
    recolors that Realization's existing final 3MF, then reports analysis.
    """

    resolver = Mock()
    resolver.system_value.return_value = [
        "system-black",
        "system-white",
        "system-red",
    ]

    plan = SimpleNamespace(
        resolver=resolver,
    )

    expected_analysis = object()
    events: list[tuple[object, ...]] = []

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: plan,
    )

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor",
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        events.append(
            (
                "analyze",
                artifact_id,
                realization,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )

    result = cmd_color.run_colors(
        "dog",
        realization="shape_ornament",
        recolor="printer",
    )

    assert result is expected_analysis

    assert events == [
        (
            "persist",
            "dog",
            "shape_ornament",
            (
                "system-black",
                "system-white",
                "system-red",
            ),
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_ornament",
            tmp_path,
        ),
        (
            "analyze",
            "dog",
            "shape_ornament",
        ),
    ]


def test_recolor_reset_updates_selected_realization_existing_final(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Realization-scoped reset removes the selected printer_colors override,
    recolors that Realization's existing final 3MF from inherited
    configuration, then reports analysis.
    """

    expected_analysis = object()
    events: list[tuple[object, ...]] = []

    monkeypatch.chdir(
        tmp_path,
    )

    def fake_reset_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "reset",
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_reset_printer_colors",
        fake_reset_printer_colors,
    )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor",
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        events.append(
            (
                "analyze",
                artifact_id,
                realization,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )

    result = cmd_color.run_colors(
        "dog",
        realization="shape_ornament",
        recolor="reset",
    )

    assert result is expected_analysis

    assert events == [
        (
            "reset",
            "dog",
            "shape_ornament",
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_ornament",
            tmp_path,
        ),
        (
            "analyze",
            "dog",
            "shape_ornament",
        ),
    ]


def test_resolve_artifact_recolor_realizations_includes_canonical_and_explicit_realizations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped recoloring selects every applicable Realization, including
    canonical Realizations that do not require explicit Artifact configuration
    and additional explicitly configured Realizations.
    """

    expected = (
        "artwork_default",
        "shape_default",
        "shape_ornament",
        "gift_ornament",
    )

    monkeypatch.setattr(
        cmd_color,
        "get_realization_names",
        lambda artifact_id, *, project_root: expected,
        raising=False,
    )

    result = cmd_color._resolve_artifact_recolor_realizations(
        "dog",
        project_root=tmp_path,
    )

    assert result == expected


def test_prepare_artifact_recolor_rejects_missing_final_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped recoloring validates every selected Realization before
    configuration or final-3MF mutation begins.

    If any selected Realization lacks its existing final 3MF, preparation
    fails without recoloring any Realization.
    """

    realizations = (
        "artwork_default",
        "shape_default",
        "shape_ornament",
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_artifact_recolor_realizations",
        lambda artifact_id, *, project_root: realizations,
    )

    plans: dict[str, object] = {}

    for realization in realizations:
        final_path = tmp_path / realization / "artifact.3mf"

        if realization != "shape_default":
            final_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            final_path.touch()

        plans[realization] = SimpleNamespace(
            artifact_id="dog",
            realization_name=realization,
            model_name="artwork" if realization == "artwork_default" else "shape",
            stages=(
                SimpleNamespace(
                    name="package",
                    products=(
                        SimpleNamespace(
                            name="artifact",
                            path=final_path,
                        ),
                    ),
                ),
            ),
        )

    resolved: list[str] = []

    def fake_resolve_existing_final_realization(
        artifact_id: str,
        realization: str,
        project_root: Path,
    ) -> object:
        resolved.append(realization)
        return plans[realization]

    monkeypatch.setattr(
        cmd_color,
        "_resolve_existing_final_realization",
        fake_resolve_existing_final_realization,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda *args, **kwargs: pytest.fail(
            "Artifact recolor preparation must not mutate final 3MFs"
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda *args, **kwargs: pytest.fail(
            "Artifact recolor preparation must not mutate configuration"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="existing final 3MF",
    ):
        cmd_color._prepare_artifact_recolor(
            "dog",
            project_root=tmp_path,
        )

    assert resolved == list(realizations)


def test_prepare_artifact_recolor_rejects_missing_recolor_source_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped recoloring validates the recolor source for every selected
    Realization before configuration or final-3MF mutation begins.

    Failure in one Realization must not prevent the remaining selected
    Realizations from being validated.
    """

    def make_plan(
        realization: str,
        model_name: str,
    ) -> BuildPlan:
        final_path = tmp_path / realization / "artifact.3mf"

        final_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        final_path.touch()

        return cast(
            BuildPlan,
            SimpleNamespace(
                artifact_id="dog",
                realization_name=realization,
                model_name=model_name,
                stages=(
                    SimpleNamespace(
                        name="package",
                        products=(
                            SimpleNamespace(
                                name="artifact",
                                path=final_path,
                            ),
                        ),
                    ),
                ),
            ),
        )

    plans = (
        make_plan(
            "artwork_default",
            "artwork",
        ),
        make_plan(
            "shape_default",
            "shape",
        ),
        make_plan(
            "shape_ornament",
            "shape",
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_artifact_recolor_realizations",
        lambda artifact_id, *, project_root: tuple(plan.realization_name for plan in plans),
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_existing_final_realization",
        lambda artifact_id, realization, project_root: next(
            plan for plan in plans if plan.realization_name == realization
        ),
    )

    validated: list[str] = []

    def fake_validate_existing_recolor_source(
        plan: BuildPlan,
    ) -> None:
        validated.append(
            plan.realization_name,
        )

        if plan.realization_name == "shape_default":
            raise RuntimeError("Recoloring requires an existing registered Artwork manifest")

    monkeypatch.setattr(
        cmd_color,
        "_validate_existing_recolor_source",
        fake_validate_existing_recolor_source,
        raising=False,
    )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        lambda *args, **kwargs: pytest.fail(
            "Artifact recolor preparation must not mutate final 3MFs"
        ),
    )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        lambda *args, **kwargs: pytest.fail(
            "Artifact recolor preparation must not mutate configuration"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="registered Artwork manifest",
    ):
        cmd_color._prepare_artifact_recolor(
            "dog",
            project_root=tmp_path,
        )

    assert validated == [
        "artwork_default",
        "shape_default",
        "shape_ornament",
    ]


def test_recolor_printer_at_artifact_scope_prepares_before_persisting_and_recoloring(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped printer recoloring validates the complete Realization scope
    before mutating Artifact configuration or any existing final 3MF.

    After successful preparation, Artifact printer_colors are persisted once
    and every prepared Realization is recolored independently.
    """

    resolver = Mock()
    resolver.system_value.return_value = [
        "system-black",
        "system-white",
        "system-red",
    ]

    recolor_scope = SimpleNamespace(
        resolver=resolver,
    )

    prepared_plans = (
        cast(
            BuildPlan,
            SimpleNamespace(
                realization_name="artwork_default",
            ),
        ),
        cast(
            BuildPlan,
            SimpleNamespace(
                realization_name="shape_default",
            ),
        ),
        cast(
            BuildPlan,
            SimpleNamespace(
                realization_name="shape_ornament",
            ),
        ),
    )

    events: list[tuple[object, ...]] = []

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: recolor_scope,
    )

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        events.append(
            (
                "prepare",
                artifact_id,
                project_root,
            )
        )
        return prepared_plans

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor",
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_printer_color_overrides",
        lambda artifact_id, *, project_root: None,
    )

    expected_analysis = object()

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        events.append(
            (
                "analyze",
                artifact_id,
                realization,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )

    result = cmd_color.run_colors(
        "dog",
        recolor="printer",
    )

    assert result is expected_analysis

    assert events == [
        (
            "prepare",
            "dog",
            tmp_path,
        ),
        (
            "persist",
            "dog",
            None,
            (
                "system-black",
                "system-white",
                "system-red",
            ),
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "artwork_default",
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_default",
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_ornament",
            tmp_path,
        ),
        (
            "analyze",
            "dog",
            None,
        ),
    ]


def test_recolor_library_at_artifact_scope_prepares_before_persisting_and_recoloring(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Artifact-scoped Library recoloring validates the complete Realization scope
    before mutating Artifact configuration or any existing final 3MF.

    After successful preparation, the Library palette is persisted once as
    Artifact printer_colors and every prepared Realization is recolored
    independently.
    """

    resolver = Mock()
    resolver.return_value = [
        "library-black",
        "library-white",
        "library-red",
    ]

    recolor_scope = SimpleNamespace(
        resolver=resolver,
    )

    prepared_plans = (
        cast(
            BuildPlan,
            SimpleNamespace(
                realization_name="artwork_default",
            ),
        ),
        cast(
            BuildPlan,
            SimpleNamespace(
                realization_name="shape_default",
            ),
        ),
        cast(
            BuildPlan,
            SimpleNamespace(
                realization_name="shape_ornament",
            ),
        ),
    )

    events: list[tuple[object, ...]] = []

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_color,
        "_resolve_recolor_scope",
        lambda artifact_id, *, realization, project_root: recolor_scope,
    )

    def fake_prepare_artifact_recolor(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[BuildPlan, ...]:
        events.append(
            (
                "prepare",
                artifact_id,
                project_root,
            )
        )
        return prepared_plans

    monkeypatch.setattr(
        cmd_color,
        "_prepare_artifact_recolor",
        fake_prepare_artifact_recolor,
    )

    def fake_persist_printer_colors(
        artifact_id: str,
        *,
        realization: str | None,
        printer_colors: tuple[str, ...],
        project_root: Path,
    ) -> None:
        events.append(
            (
                "persist",
                artifact_id,
                realization,
                printer_colors,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_persist_printer_colors",
        fake_persist_printer_colors,
    )

    def fake_recolor_existing_final(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> None:
        events.append(
            (
                "recolor",
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_color,
        "_recolor_existing_final",
        fake_recolor_existing_final,
    )

    monkeypatch.setattr(
        cmd_color,
        "_report_retained_printer_color_overrides",
        lambda artifact_id, *, project_root: None,
    )

    expected_analysis = object()

    def fake_analyze_artifact_colors(
        artifact_id: str,
        *,
        realization: str | None = None,
    ) -> object:
        events.append(
            (
                "analyze",
                artifact_id,
                realization,
            )
        )
        return expected_analysis

    monkeypatch.setattr(
        cmd_color,
        "analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )

    result = cmd_color.run_colors(
        "dog",
        recolor="library",
    )

    assert result is expected_analysis

    assert events == [
        (
            "prepare",
            "dog",
            tmp_path,
        ),
        (
            "persist",
            "dog",
            None,
            (
                "library-black",
                "library-white",
                "library-red",
            ),
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "artwork_default",
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_default",
            tmp_path,
        ),
        (
            "recolor",
            "dog",
            "shape_ornament",
            tmp_path,
        ),
        (
            "analyze",
            "dog",
            None,
        ),
    ]
