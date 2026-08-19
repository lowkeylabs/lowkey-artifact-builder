"""
Tests for artifact configuration loading, persistence, and resolution.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit

from lowkey_artifact_builder.config import (
    ConfigError,
    artifact_config_path,
    get_resolver,
    load_artifact_config,
    update_artifact_config,
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
    assert resolver("artwork_min_island_area") == 0.16
    assert resolver("artwork_island_connectivity") == 8

    assert resolver.source("artwork_raise") == "model"


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

    assert resolver("printer_colors") == [
        "brown",
        "black",
        "gold",
        "white",
        "silver",
    ]

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
    """

    resolver = get_resolver(
        "nydeli",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver.has_color("red")

    red = resolver.color("red")

    assert red["manufacturer"] == "eSUN"
    assert red["filament"] == "Fire Engine Red"
    assert red["rgb"] == [
        220,
        38,
        38,
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
    Artwork color count is the length of printer_colors.
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

    assert resolver("artwork_colors") == 3

    assert resolver.source("artwork_colors") == "derived"


def test_duplicate_printer_colors_count_as_available_colors(
    tmp_path: Path,
) -> None:
    """
    Multiple printer heads may intentionally contain the same color.

    artwork_colors therefore reflects the number of configured printer
    color positions rather than the number of unique color names.
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

    assert resolver("artwork_colors") == 4


def test_configured_value_can_override_derivation(
    tmp_path: Path,
) -> None:
    """
    Explicit configuration wins over a derived value.
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
            "artwork_colors": 2,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "nydeli",
        project_root=tmp_path,
    )

    assert resolver("artwork_colors") == 2

    assert resolver.source("artwork_colors") == "artifact (overrides derived)"


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
