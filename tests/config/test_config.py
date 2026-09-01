"""
Tests for artifact configuration loading, persistence, and resolution.
"""
# File: tests/config/test_config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit

from lowkey_artifact_builder.config import (
    ConfigError,
    artifact_config_path,
    get_product_dependency_binding,
    get_resolver,
    has_product_dependency_binding,
    load_artifact_config,
    update_artifact_config,
    write_artifact_config,
)
from lowkey_artifact_builder.model import (
    ProductDependencyBinding,
    ProductDependencySpec,
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
# Artifact paths
# =========================================================


def test_artifact_config_path(
    tmp_path: Path,
) -> None:
    """
    Artifact configuration has a deterministic project-relative path.
    """

    path = artifact_config_path(
        "nydeli",
        project_root=tmp_path,
    )

    assert path == (tmp_path / "artifacts" / "nydeli" / "artifact.toml")


@pytest.mark.parametrize(
    "artifact_id",
    [
        "",
        ".",
        "..",
        "foo/bar",
        r"foo\bar",
    ],
)
def test_artifact_config_path_rejects_invalid_ids(
    tmp_path: Path,
    artifact_id: str,
) -> None:
    """
    Artifact IDs cannot escape the artifacts directory.
    """

    with pytest.raises(ConfigError):
        artifact_config_path(
            artifact_id,
            project_root=tmp_path,
        )


# =========================================================
# Artifact loading
# =========================================================


def test_load_missing_artifact_config(
    tmp_path: Path,
) -> None:
    """
    Missing artifact configuration is valid during initial setup.
    """

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config == {}


# =========================================================
# Artifact writing
# =========================================================


def test_write_artifact_config(
    tmp_path: Path,
) -> None:
    """
    Artifact configuration can be created from sparse values.
    """

    path = write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "new-york-deli-blimp.png",
            "printer_colors": [
                "black",
                "white",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    assert path.is_file()

    assert path == (tmp_path / "artifacts" / "nydeli" / "artifact.toml")

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config == {
        "model": "artwork",
        "source": "new-york-deli-blimp.png",
        "printer_colors": [
            "black",
            "white",
            "red",
        ],
    }


def test_write_artifact_config_replaces_existing_document(
    tmp_path: Path,
) -> None:
    """
    Exact writes replace the previous artifact definition.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "old.png",
            "artwork_raise": 0.8,
        },
        project_root=tmp_path,
    )

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "new.png",
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config == {
        "model": "artwork",
        "source": "new.png",
    }


def test_write_artifact_config_rejects_invalid_model(
    tmp_path: Path,
) -> None:
    """
    A model, when supplied, must be a nonempty string.
    """

    with pytest.raises(
        ConfigError,
        match="model",
    ):
        write_artifact_config(
            "nydeli",
            {
                "model": "",
            },
            project_root=tmp_path,
        )


# =========================================================
# Artifact updating
# =========================================================


def test_update_artifact_config_creates_document(
    tmp_path: Path,
) -> None:
    """
    Updating a nonexistent artifact creates artifact.toml.
    """

    path = update_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "new-york-deli-blimp.png",
        },
        project_root=tmp_path,
    )

    assert path.is_file()

    assert load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    ) == {
        "model": "artwork",
        "source": "new-york-deli-blimp.png",
    }


def test_update_artifact_config_preserves_other_values(
    tmp_path: Path,
) -> None:
    """
    Updating selected artifact values preserves unrelated values.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "old.png",
            "printer_colors": [
                "black",
                "white",
                "red",
            ],
            "artwork_raise": 0.8,
        },
        project_root=tmp_path,
    )

    update_artifact_config(
        "nydeli",
        {
            "source": "new.png",
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config == {
        "model": "artwork",
        "source": "new.png",
        "printer_colors": [
            "black",
            "white",
            "red",
        ],
        "artwork_raise": 0.8,
    }


def test_update_artifact_config_merges_parameters_table(
    tmp_path: Path,
) -> None:
    """
    Updating [parameters] merges rather than replaces the table.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "parameters": {
                "artwork_raise": 0.8,
                "artwork_pixels": 512,
            },
        },
        project_root=tmp_path,
    )

    update_artifact_config(
        "nydeli",
        {
            "parameters": {
                "artwork_raise": 1.0,
            },
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "nydeli",
        project_root=tmp_path,
    )

    assert config["parameters"] == {
        "artwork_raise": 1.0,
        "artwork_pixels": 512,
    }


def test_update_artifact_config_preserves_comments(
    tmp_path: Path,
) -> None:
    """
    tomlkit preserves existing comments during artifact updates.
    """

    path = tmp_path / "artifacts" / "nydeli" / "artifact.toml"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        ('model = "artwork"\n\n# Preserve this explanation.\nsource = "old.png"\n'),
        encoding="utf-8",
    )

    update_artifact_config(
        "nydeli",
        {
            "source": "new.png",
        },
        project_root=tmp_path,
    )

    text = path.read_text(
        encoding="utf-8",
    )

    assert "# Preserve this explanation." in text
    assert 'source = "new.png"' in text


def test_updated_artifact_remains_valid_toml(
    tmp_path: Path,
) -> None:
    """
    An updated artifact remains a valid TOML document.
    """

    path = update_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "new-york-deli-blimp.png",
            "printer_colors": [
                "black",
                "white",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    document = tomlkit.parse(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert document["model"] == "artwork"


# =========================================================
# Resolver identity
# =========================================================


def test_resolver_reads_artifact_model(
    tmp_path: Path,
) -> None:
    """
    Existing artifact configuration determines its model.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "source": "new-york-deli-blimp.png",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artifact_id") == "nydeli"
    assert resolver("model") == "artwork"

    assert resolver.source("artifact_id") == "artifact"

    assert resolver.source("model") == "artifact"


def test_resolver_accepts_model_during_initial_setup(
    tmp_path: Path,
) -> None:
    """
    Initial setup may supply the model before artifact.toml exists.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artifact_id") == "nydeli"
    assert resolver("model") == "artwork"

    assert resolver.source("model") == "setup"


def test_resolver_requires_model_for_unconfigured_artifact(
    tmp_path: Path,
) -> None:
    """
    A new artifact cannot be resolved until its model is known.
    """

    with pytest.raises(
        ConfigError,
        match="does not define a model",
    ):
        get_resolver(
            "nydeli",
            project_root=tmp_path,
        )


def test_resolver_rejects_model_conflict(
    tmp_path: Path,
) -> None:
    """
    A supplied model cannot contradict artifact.toml.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="declares model",
    ):
        get_resolver(
            "nydeli",
            model="circular",
            project_root=tmp_path,
        )


# =========================================================
# Model defaults
# =========================================================


def test_artwork_model_defaults_are_resolved(
    tmp_path: Path,
) -> None:
    """
    Artwork parameters.toml contributes model defaults.

    Island cleanup is expressed as raster pixel area and is therefore
    independent of physical artwork size.

    Physical artwork size is intentionally not defaulted because it
    must be supplied by workspace or artifact configuration.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_raise") == 1.0
    assert resolver("artwork_pixels") == 1024
    assert resolver("artwork_min_island_area") == 34


def test_artwork_fill_color_is_derived_from_printer_colors(
    tmp_path: Path,
) -> None:
    """
    Artwork fill color defaults to the configured printer color
    perceptually closest to ideal white.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-white", "test-blue"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "test-white"
    assert resolver.source("artwork_fill_color") == "derived"


def test_artwork_fill_color_derivation_preserves_catalog_identity(
    tmp_path: Path,
) -> None:
    """
    Derived fill color preserves the identity of the selected
    physical printer color rather than substituting `white`.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["black", "cold-white", "silver"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "cold-white"


def test_artwork_fill_color_derivation_uses_perceptual_color_distance(
    tmp_path: Path,
) -> None:
    """
    Fill-color derivation selects the printer color nearest ideal
    white according to the shared perceptual color semantics.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-green", "test-white"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "test-white"


def test_artwork_fill_color_derivation_preserves_printer_order_for_ties(
    tmp_path: Path,
) -> None:
    """
    Equal-distance fill candidates are selected deterministically
    according to configured printer-color order.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-blue"]

[colors.test-red]
manufacturer = "test"
filament = "Test Red"
rgb = [200, 200, 200]

[colors.test-blue]
manufacturer = "test"
filament = "Test Blue"
rgb = [200, 200, 200]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "test-red"


def test_artwork_fill_color_derivation_accepts_duplicate_printer_colors(
    tmp_path: Path,
) -> None:
    """
    Fill-color derivation accepts duplicate printer colors.

    Multiple printer heads may intentionally contain the same semantic
    color, so deriving the fill color must not require printer color
    identities to be unique.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-white", "test-white"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "test-white"


def test_explicit_artwork_fill_color_overrides_derivation(
    tmp_path: Path,
) -> None:
    """
    Explicit Artwork fill configuration takes precedence over
    the model derivation.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-white", "test-blue"]
artwork_fill_color = "test-blue"
artwork_colors = ["test-red", "test-white", "test-blue"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "test-blue"
    assert resolver.source("artwork_fill_color") == "workspace (overrides derived)"


def test_derived_artwork_fill_color_is_present_in_derived_artwork_colors(
    tmp_path: Path,
) -> None:
    """
    Default Artwork palette and fill derivations remain mutually
    consistent because both are derived from printer colors.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-white", "test-blue"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    artwork_colors = resolver("artwork_colors")
    artwork_fill_color = resolver("artwork_fill_color")

    assert artwork_fill_color in artwork_colors


def test_explicit_artwork_colors_do_not_change_fill_color_derivation(
    tmp_path: Path,
) -> None:
    """
    Explicit Artwork colors do not influence fill-color derivation.

    Unless explicitly configured itself, artwork_fill_color derives from
    printer_colors even when artwork_colors has been independently
    configured.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
printer_colors = ["test-red", "test-white", "test-blue"]
artwork_colors = ["test-red", "test-blue"]
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_colors") == [
        "test-red",
        "test-blue",
    ]
    assert resolver("artwork_fill_color") == "test-white"

    assert resolver.source("artwork_colors") == "workspace (overrides derived)"
    assert resolver.source("artwork_fill_color") == "derived"


def test_artwork_envelope_mode_is_a_model_default(
    tmp_path: Path,
) -> None:
    """
    Artwork envelope derivation has a model-owned default.

    The default is model-owned configuration rather than stage-local
    fallback behavior.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_envelope_mode") is not None
    assert resolver.source("artwork_envelope_mode") == "model"


def test_artwork_fill_color_can_be_explicitly_configured(
    tmp_path: Path,
) -> None:
    """
    Artwork fill color may explicitly select a non-white palette color.

    The configured fill color is ordinary semantic color policy rather
    than a special requirement for white.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
artwork_colors = ["test-red", "test-blue"]
artwork_fill_color = "test-red"
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_fill_color") == "test-red"


def test_artwork_palette_does_not_require_white_when_fill_color_is_configured(
    tmp_path: Path,
) -> None:
    """
    Artwork palettes do not require white.

    A palette containing no white color is valid when artwork_fill_color
    selects another member of the configured Artwork palette.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
artwork_colors = ["test-red", "test-blue"]
artwork_fill_color = "test-blue"
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_colors") == [
        "test-red",
        "test-blue",
    ]
    assert resolver("artwork_fill_color") == "test-blue"


def test_artwork_size_has_no_default(
    tmp_path: Path,
) -> None:
    """
    Artwork size must be supplied by workspace or artifact
    configuration.

    There is intentionally no model default because artwork size is a
    significant physical artifact dimension that setup should request
    when it is otherwise unresolved.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert not resolver.has("artwork_size")

    with pytest.raises(
        ConfigError,
        match="Unknown configuration value 'artwork_size'",
    ):
        resolver("artwork_size")


def test_workspace_can_supply_artwork_size(
    tmp_path: Path,
) -> None:
    """
    Workspace configuration may satisfy the artwork size requirement.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
artwork_size = 70.0
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_size") == 70.0

    assert resolver.source("artwork_size") == "workspace"


def test_shape_model_defaults_are_resolved(
    tmp_path: Path,
) -> None:
    """
    Shape parameters.toml contributes structural, color, and Artwork defaults.

    The baseline Shape defaults to circle geometry with polygon defaults
    available for side count and rotation. Physical size and base thickness
    have model defaults. The base color defaults to white.

    Outer-ridge width defaults to zero so the existing no-ridge Shape remains
    the default artifact. Ridge raise defaults to 1 mm and integrated is the
    default ridge style if a ridge is enabled. Ridge color is derived from the
    resolved base color rather than independently defaulted.

    Incorporated Artwork defaults to a 1 mm Shape-owned physical raise.
    Artwork fill is disabled by default through the explicit "none"
    semantic fill color.
    """

    resolver = get_resolver(
        "shape-example",
        model="shape",
        project_root=tmp_path,
    )

    assert resolver("shape_geometry") == "circle"
    assert resolver("shape_sides") == 8
    assert resolver("shape_rotation") == 0.0

    assert resolver("shape_size") == 100.0
    assert resolver("shape_base_raise") == 2.0
    assert resolver("shape_base_color") == "white"

    assert resolver("shape_outer_ridge_width") == 0.0
    assert resolver("shape_outer_ridge_raise") == 1.0
    assert resolver("shape_outer_ridge_style") == "integrated"
    assert resolver("shape_outer_ridge_color") == "white"

    assert resolver("shape_artwork_raise") == 1.0

    assert resolver.has("shape_artwork_fill_color")
    assert resolver("shape_artwork_fill_color") == "none"

    assert resolver.source("shape_geometry") == "model"
    assert resolver.source("shape_sides") == "model"
    assert resolver.source("shape_rotation") == "model"

    assert resolver.source("shape_size") == "model"
    assert resolver.source("shape_base_raise") == "model"
    assert resolver.source("shape_base_color") == "model"

    assert resolver.source("shape_outer_ridge_width") == "model"
    assert resolver.source("shape_outer_ridge_raise") == "model"
    assert resolver.source("shape_outer_ridge_style") == "model"
    assert resolver.source("shape_outer_ridge_color") == "derived"

    assert resolver.source("shape_artwork_raise") == "model"
    assert resolver.source("shape_artwork_fill_color") == "model (overrides derived)"


# =========================================================
# Configuration precedence
# =========================================================


def test_workspace_overrides_model_default(
    tmp_path: Path,
) -> None:
    """
    Workspace parameters override model defaults.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
artwork_raise = 0.8
""".lstrip(),
    )

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_raise") == 0.8

    assert resolver.source("artwork_raise") == "workspace"


def test_artifact_overrides_workspace(
    tmp_path: Path,
) -> None:
    """
    Artifact parameters override workspace parameters.
    """

    _write_workspace(
        tmp_path,
        """
[parameters]
artwork_raise = 0.8
""".lstrip(),
    )

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "artwork_raise": 1.2,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artwork_raise") == 1.2

    assert resolver.source("artwork_raise") == "artifact"


def test_artifact_parameters_table_overrides_top_level(
    tmp_path: Path,
) -> None:
    """
    [parameters] wins over a duplicate sparse top-level value.
    """

    write_artifact_config(
        "nydeli",
        {
            "model": "artwork",
            "artwork_raise": 0.8,
            "parameters": {
                "artwork_raise": 1.2,
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artwork_raise") == 1.2
    assert resolver.source("artwork_raise") == "artifact"


def test_shape_base_color_may_be_overridden(
    tmp_path: Path,
) -> None:
    """
    Artifact configuration may override the Shape base color.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "red",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    assert resolver("shape_base_color") == "red"
    assert resolver.source("shape_base_color") == "artifact"


def test_shape_outer_ridge_color_may_override_base_color(
    tmp_path: Path,
) -> None:
    """
    An explicit ridge color overrides its derived base-color default.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "white",
                "shape_outer_ridge_color": "red",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    assert resolver("shape_base_color") == "white"
    assert resolver("shape_outer_ridge_color") == "red"

    assert resolver.source("shape_base_color") == "artifact"
    assert resolver.source("shape_outer_ridge_color") == "artifact (overrides derived)"


def test_shape_explicit_ridge_color_is_independent_of_base_color(
    tmp_path: Path,
) -> None:
    """
    An explicit ridge color does not follow a separately resolved base color.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "black",
                "shape_outer_ridge_color": "red",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    assert resolver("shape_base_color") == "black"
    assert resolver("shape_outer_ridge_color") == "red"

    assert resolver.source("shape_base_color") == "artifact"
    assert resolver.source("shape_outer_ridge_color") == "artifact (overrides derived)"


# =========================================================
# System parameters
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
# Derived values
# =========================================================


def test_artwork_colors_are_derived_from_printer_colors(
    tmp_path: Path,
) -> None:
    """
    Artwork colors default to the configured printer colors.
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

    assert resolver("artwork_colors") == (
        "black",
        "white",
        "red",
    )

    assert resolver.source("artwork_colors") == "derived"


def test_duplicate_printer_colors_are_preserved_in_artwork_colors(
    tmp_path: Path,
) -> None:
    """
    Multiple printer heads may intentionally contain the same color.

    Derived artwork colors preserve printer color order and duplicate
    color positions.
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

    assert resolver("artwork_colors") == (
        "black",
        "white",
        "red",
        "red",
    )

    assert resolver.source("artwork_colors") == "derived"


def test_configured_value_can_override_derivation(
    tmp_path: Path,
) -> None:
    """
    Explicit artwork colors override the derived printer colors.
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
            "artwork_colors": [
                "black",
                "red",
            ],
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artwork_colors") == [
        "black",
        "red",
    ]

    assert resolver.source("artwork_colors") == "artifact (overrides derived)"


def test_shape_outer_ridge_color_derives_from_resolved_base_color(
    tmp_path: Path,
) -> None:
    """
    The default ridge color follows the resolved base color.

    The ridge default is a derived configuration relationship rather
    than an independent literal model default.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "black",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    assert resolver("shape_base_color") == "black"
    assert resolver("shape_outer_ridge_color") == "black"

    assert resolver.source("shape_base_color") == "artifact"
    assert resolver.source("shape_outer_ridge_color") == "derived"


# =========================================================
# Resolver introspection
# =========================================================


def test_resolver_names_include_configured_and_derived_values(
    tmp_path: Path,
) -> None:
    """
    Resolver introspection includes both configured and derived names.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    names = resolver.names()

    assert "artifact_id" in names
    assert "model" in names
    assert "printer_colors" in names
    assert "artwork_raise" in names
    assert "artwork_colors" in names


def test_unknown_parameter_raises_config_error(
    tmp_path: Path,
) -> None:
    """
    Unknown configuration names fail clearly.
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="Unknown configuration value",
    ):
        resolver("does_not_exist")


def test_write_artifact_config_preserves_product_dependency_binding(
    tmp_path: Path,
) -> None:
    """
    Artifact configuration may persist a concrete producer binding for
    a declarative product dependency.
    """

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
            "product_dependencies": {
                "geometry": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "geometry",
                    "artifact": "nydeli",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "consumer",
        project_root=tmp_path,
    )

    assert config["product_dependencies"] == {
        "geometry": {
            "model": "artwork",
            "stage": "vector",
            "product": "geometry",
            "artifact": "nydeli",
            "realization": "default",
        },
    }


def test_update_artifact_config_preserves_other_product_dependency_bindings(
    tmp_path: Path,
) -> None:
    """
    Updating one product dependency binding preserves sibling bindings.
    """

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
            "product_dependencies": {
                "geometry": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "geometry",
                    "artifact": "first",
                    "realization": "default",
                },
                "mask": {
                    "model": "artwork",
                    "stage": "raster",
                    "product": "mask",
                    "artifact": "second",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    update_artifact_config(
        "consumer",
        {
            "product_dependencies": {
                "geometry": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "geometry",
                    "artifact": "replacement",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "consumer",
        project_root=tmp_path,
    )

    assert config["product_dependencies"]["geometry"]["artifact"] == "replacement"
    assert config["product_dependencies"]["mask"]["artifact"] == "second"


def test_has_product_dependency_binding_returns_false_when_unconfigured(
    tmp_path: Path,
) -> None:
    """
    An unconfigured declarative product dependency is not active.

    Declaring a potential product dependency does not require every
    artifact realization to bind that dependency.
    """

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
        },
        project_root=tmp_path,
    )

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    assert (
        has_product_dependency_binding(
            "consumer",
            dependency,
            project_root=tmp_path,
        )
        is False
    )


def test_has_product_dependency_binding_returns_true_when_configured(
    tmp_path: Path,
) -> None:
    """
    A configured declarative product dependency is active.

    Binding presence is determined by artifact configuration without
    resolving or validating the complete binding.
    """

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
            "product_dependencies": {
                "geometry": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "geometry",
                    "artifact": "nydeli",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    assert (
        has_product_dependency_binding(
            "consumer",
            dependency,
            project_root=tmp_path,
        )
        is True
    )


def test_get_product_dependency_binding(
    tmp_path: Path,
) -> None:
    """
    Artifact configuration binds a declarative product dependency to a
    concrete producer artifact and realization.
    """

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
            "product_dependencies": {
                "geometry": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "geometry",
                    "artifact": "nydeli",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    binding = get_product_dependency_binding(
        "consumer",
        dependency,
        project_root=tmp_path,
    )

    assert binding == ProductDependencyBinding(
        dependency=dependency,
        artifact="nydeli",
        realization="default",
    )


def test_get_product_dependency_binding_rejects_missing_binding(
    tmp_path: Path,
) -> None:
    """
    A required declarative dependency must have a configured producer
    binding.
    """

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
        },
        project_root=tmp_path,
    )

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    with pytest.raises(
        ConfigError,
        match="geometry",
    ):
        get_product_dependency_binding(
            "consumer",
            dependency,
            project_root=tmp_path,
        )


def test_get_product_dependency_binding_rejects_mismatched_definition(
    tmp_path: Path,
) -> None:
    """
    A configured binding must describe the declarative dependency being
    bound.
    """

    write_artifact_config(
        "consumer",
        {
            "model": "consumer",
            "product_dependencies": {
                "geometry": {
                    "model": "other",
                    "stage": "prepare",
                    "product": "different",
                    "artifact": "nydeli",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    with pytest.raises(
        ConfigError,
        match="geometry",
    ):
        get_product_dependency_binding(
            "consumer",
            dependency,
            project_root=tmp_path,
        )


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
