"""
Tests for operator recoloring through the colors command.
"""
# File: tests/cli/test_recolor.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import lowkey_artifact_builder.cli.cmd_color as cmd_color
from lowkey_artifact_builder.config import (
    load_artifact_config,
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
