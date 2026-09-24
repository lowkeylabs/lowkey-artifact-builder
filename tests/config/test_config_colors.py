"""
Tests for color-related configuration resolution.
"""
# File: tests/config/test_config_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
    load_artifact_config,
    update_realization_config,
    write_artifact_config,
)

# =========================================================
# Helpers
# =========================================================


def _write_workspace(
    project_root: Path,
    text: str,
) -> None:
    """
    Write workspace.toml in a temporary project.
    """

    (project_root / "workspace.toml").write_text(
        text,
        encoding="utf-8",
    )


# =========================================================
# Printer colors
# =========================================================


def test_system_printer_colors_are_available(
    tmp_path: Path,
) -> None:
    """
    System printer configuration participates in resolution.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    printer_colors = resolver("printer_colors")

    assert isinstance(printer_colors, list)
    assert printer_colors
    assert resolver.source("printer_colors") == "system"


def test_artifact_can_override_printer_colors(
    tmp_path: Path,
) -> None:
    """
    An artifact may use a palette different from the system printer
    palette.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "printer_colors": [
                "black",
                "white",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("printer_colors") == [
        "black",
        "white",
        "red",
    ]

    assert resolver.source("printer_colors") == "artifact"


# =========================================================
# Printer-color persistence
# =========================================================


def test_update_realization_config_updates_printer_colors(
    tmp_path: Path,
) -> None:
    """
    Updating Realization printer colors changes only the selected Realization.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "nydeli.png",
            "printer_colors": [
                "artifact-black",
                "artifact-white",
            ],
            "realizations": {
                "shape_default": {
                    "variant": "shape.default",
                    "printer_colors": [
                        "default-black",
                        "default-white",
                    ],
                },
                "shape_ornament": {
                    "variant": "shape.ornament",
                    "shape_size": 95.0,
                    "printer_colors": [
                        "ornament-black",
                        "ornament-red",
                    ],
                },
            },
        },
        project_root=tmp_path,
    )

    update_realization_config(
        "nydeli",
        "shape_ornament",
        {
            "printer_colors": [
                "system-black",
                "system-white",
                "system-red",
            ],
        },
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

    assert config["realizations"]["shape_default"]["printer_colors"] == [
        "default-black",
        "default-white",
    ]

    assert config["realizations"]["shape_ornament"] == {
        "variant": "shape.ornament",
        "shape_size": 95.0,
        "printer_colors": [
            "system-black",
            "system-white",
            "system-red",
        ],
    }


def test_update_realization_printer_colors_preserves_document_presentation(
    tmp_path: Path,
) -> None:
    """
    Updating Realization printer colors preserves existing Artifact and
    Realization comments.
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

[realizations.shape_ornament]
# Preserve this Realization explanation.
variant = "shape.ornament"
printer_colors = ["ornament-black", "ornament-red"]
""".lstrip(),
        encoding="utf-8",
    )

    update_realization_config(
        "nydeli",
        "shape_ornament",
        {
            "printer_colors": [
                "system-black",
                "system-white",
                "system-red",
            ],
        },
        project_root=tmp_path,
    )

    text = path.read_text(
        encoding="utf-8",
    )

    assert "# Preserve this source explanation." in text
    assert "# Preserve this Realization explanation." in text
    assert 'source = "nydeli.png"' in text
    assert 'variant = "shape.ornament"' in text


def test_update_realization_config_materializes_canonical_realization(
    tmp_path: Path,
) -> None:
    """
    Updating an implicit canonical Realization materializes only its sparse
    Realization-specific customization.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "nydeli.png",
            "printer_colors": [
                "artifact-black",
                "artifact-white",
            ],
        },
        project_root=tmp_path,
    )

    update_realization_config(
        "nydeli",
        "shape_ornament",
        {
            "printer_colors": [
                "system-black",
                "system-white",
                "system-red",
            ],
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config["model"] == "artwork"
    assert config["source"] == "nydeli.png"

    assert config["printer_colors"] == [
        "artifact-black",
        "artifact-white",
    ]

    assert config["realizations"] == {
        "shape_ornament": {
            "printer_colors": [
                "system-black",
                "system-white",
                "system-red",
            ],
        },
    }


def test_update_realization_config_materializes_missing_canonical_realization(
    tmp_path: Path,
) -> None:
    """
    Updating an implicit canonical Realization materializes it alongside
    existing explicit Realization customizations.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "nydeli.png",
            "printer_colors": [
                "artifact-black",
                "artifact-white",
            ],
            "realizations": {
                "shape_default": {
                    "printer_colors": [
                        "default-black",
                        "default-white",
                    ],
                },
            },
        },
        project_root=tmp_path,
    )

    update_realization_config(
        "nydeli",
        "shape_ornament",
        {
            "printer_colors": [
                "system-black",
                "system-white",
                "system-red",
            ],
        },
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

    assert config["realizations"] == {
        "shape_default": {
            "printer_colors": [
                "default-black",
                "default-white",
            ],
        },
        "shape_ornament": {
            "printer_colors": [
                "system-black",
                "system-white",
                "system-red",
            ],
        },
    }


# =========================================================
# Library colors
# =========================================================


def test_library_colors_are_a_system_default(
    tmp_path: Path,
) -> None:
    """
    The local filament library is supplied by system configuration.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    library_colors = resolver("library_colors")

    assert isinstance(library_colors, list)
    assert library_colors
    assert resolver.source("library_colors") == "system"


def test_workspace_may_override_library_colors(
    tmp_path: Path,
) -> None:
    """
    Workspace configuration may override the local filament library.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
library_colors = ["test-red", "test-green"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("library_colors") == [
        "test-red",
        "test-green",
    ]
    assert resolver.source("library_colors") == "workspace"


def test_artifact_may_override_library_colors(
    tmp_path: Path,
) -> None:
    """
    Artifact configuration may override the local filament library.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
library_colors = ["test-red", "test-green"]
""".lstrip(),
    )

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "parameters": {
                "library_colors": [
                    "test-blue",
                    "test-yellow",
                ],
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("library_colors") == [
        "test-blue",
        "test-yellow",
    ]
    assert resolver.source("library_colors") == "artifact"


# =========================================================
# Color catalog
# =========================================================


def test_color_catalog_is_available(
    tmp_path: Path,
) -> None:
    """
    System color reference data is available separately from parameters.

    Distinct physical filament products retain distinct catalog identities.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver.has_color("red")
    assert resolver.has_color("fire-engine-red")

    red = resolver.color("red")

    assert red["manufacturer"] == "eSUN"
    assert red["filament"] == "Red"
    assert red["rgb"] == [
        180,
        2,
        0,
    ]

    fire_engine_red = resolver.color(
        "fire-engine-red",
    )

    assert fire_engine_red["manufacturer"] == "eSUN"
    assert fire_engine_red["filament"] == "Fire Engine Red"
    assert fire_engine_red["rgb"] == [
        187,
        32,
        40,
    ]


def test_unknown_color_raises_config_error(
    tmp_path: Path,
) -> None:
    """
    Looking up an unknown catalog color fails clearly.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="Unknown color",
    ):
        resolver.color("not-a-color")


# =========================================================
# Artwork color count
# =========================================================


def test_artifact_color_count_is_derived_from_printer_color_count(
    tmp_path: Path,
) -> None:
    """
    Artwork color count defaults to the configured printer capacity.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "printer_colors": [
                "black",
                "white",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artifact_color_count") == 3
    assert resolver.source("artifact_color_count") == "derived"


def test_duplicate_printer_colors_contribute_to_artifact_color_count(
    tmp_path: Path,
) -> None:
    """
    Artifact color capacity follows configured printer positions.

    Multiple printer heads may intentionally contain the same semantic
    color, so duplicate printer colors still contribute to the default
    Artifact color count.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "printer_colors": [
                "black",
                "white",
                "red",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artifact_color_count") == 4
    assert resolver.source("artifact_color_count") == "derived"


def test_explicit_artifact_color_count_overrides_derivation(
    tmp_path: Path,
) -> None:
    """
    Explicit Artifact color count overrides the printer-derived default.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "printer_colors": [
                "black",
                "white",
                "red",
                "blue",
                "green",
            ],
            "artifact_color_count": 3,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artifact_color_count") == 3
    assert resolver.source("artifact_color_count") == "artifact (overrides derived)"


def test_workspace_artifact_color_count_participates_in_configuration_precedence(
    tmp_path: Path,
) -> None:
    """
    Artifact color count participates in ordinary configuration precedence.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["black", "white", "red", "blue", "green"]
artifact_color_count = 4
""".lstrip(),
    )

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "parameters": {
                "artifact_color_count": 3,
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artifact_color_count") == 3
    assert resolver.source("artifact_color_count") == "artifact (overrides derived)"


def test_resolving_artifact_color_count_does_not_create_artifact_colors(
    tmp_path: Path,
) -> None:
    """
    Artifact colors are persistent product information, not configuration.

    Resolving the configured trace cardinality must not synthesize an
    artifact_colors configuration value.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artifact_color_count") == len(
        resolver("printer_colors"),
    )

    assert "artifact_colors" not in resolver.names()

    with pytest.raises(
        ConfigError,
        match="Unknown configuration value 'artifact_colors'",
    ):
        resolver("artifact_colors")


def test_artwork_configuration_has_no_fill_color(
    tmp_path: Path,
) -> None:
    """
    Artwork no longer has a configured fill-color semantic.

    Surrounding fill geometry belongs to consuming models such as Shape,
    not to registered Artwork.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert "artwork_fill_color" not in resolver.names()

    with pytest.raises(
        ConfigError,
        match="Unknown configuration value 'artwork_fill_color'",
    ):
        resolver("artwork_fill_color")


def test_system_printer_colors_remain_available_after_artifact_override(
    tmp_path: Path,
) -> None:
    """
    System printer colors remain available independently of the effective
    resolved printer colors.

    Artifact overrides affect normal resolution but do not replace the
    underlying system-default printer palette.
    """

    system_resolver = get_resolver(
        "system-reference",
        model="artwork",
        project_root=tmp_path,
    )

    system_printer_colors = system_resolver(
        "printer_colors",
    )

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "printer_colors": [
                "black",
                "white",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver(
        "printer_colors",
    ) == [
        "black",
        "white",
        "red",
    ]

    assert (
        resolver.system_value(
            "printer_colors",
        )
        == system_printer_colors
    )
