"""
Tests for command-line stage binding parsing.
"""
# File: tests/cli/test_bindings.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.cli.bindings import (
    BindingError,
    parse_parameter_bindings,
    parse_path_bindings,
)

# =========================================================
# Path bindings
# =========================================================


def test_parse_path_bindings_resolves_relative_path(
    tmp_path: Path,
) -> None:
    """
    Relative binding paths are resolved from the project root.
    """

    result = parse_path_bindings(
        ("raster.manifest=external/products.json",),
        project_root=tmp_path,
    )

    assert result == {
        "raster.manifest": (tmp_path / "external" / "products.json"),
    }


def test_parse_path_bindings_preserves_absolute_path(
    tmp_path: Path,
) -> None:
    """
    Absolute binding paths remain absolute.
    """

    path = (tmp_path / "external" / "products.json").resolve()

    result = parse_path_bindings(
        (f"raster.manifest={path}",),
        project_root=tmp_path,
    )

    assert result == {
        "raster.manifest": path,
    }


def test_parse_path_bindings_accepts_multiple_bindings(
    tmp_path: Path,
) -> None:
    """
    Repeated path bindings produce one semantic path mapping.
    """

    result = parse_path_bindings(
        (
            "trace=external/trace.svg",
            "manifest=external/products.json",
        ),
        project_root=tmp_path,
    )

    assert result == {
        "trace": (tmp_path / "external" / "trace.svg"),
        "manifest": (tmp_path / "external" / "products.json"),
    }


def test_parse_path_bindings_returns_empty_mapping(
    tmp_path: Path,
) -> None:
    """
    No path bindings produce an empty mapping.
    """

    result = parse_path_bindings(
        (),
        project_root=tmp_path,
    )

    assert result == {}


def test_parse_path_bindings_rejects_missing_equals(
    tmp_path: Path,
) -> None:
    """
    A path binding must contain a semantic name and path.
    """

    with pytest.raises(
        BindingError,
        match="NAME=PATH",
    ):
        parse_path_bindings(
            ("raster.manifest",),
            project_root=tmp_path,
        )


def test_parse_path_bindings_rejects_empty_name(
    tmp_path: Path,
) -> None:
    """
    A path binding must identify a semantic name.
    """

    with pytest.raises(
        BindingError,
        match="name",
    ):
        parse_path_bindings(
            ("=external/products.json",),
            project_root=tmp_path,
        )


def test_parse_path_bindings_rejects_empty_path(
    tmp_path: Path,
) -> None:
    """
    A path binding must identify a filesystem path.
    """

    with pytest.raises(
        BindingError,
        match="path",
    ):
        parse_path_bindings(
            ("raster.manifest=",),
            project_root=tmp_path,
        )


def test_parse_path_bindings_rejects_duplicate_name(
    tmp_path: Path,
) -> None:
    """
    A semantic path name may be bound only once.
    """

    with pytest.raises(
        BindingError,
        match="Duplicate",
    ):
        parse_path_bindings(
            (
                "manifest=first.json",
                "manifest=second.json",
            ),
            project_root=tmp_path,
        )


def test_parse_path_bindings_preserves_equals_in_path(
    tmp_path: Path,
) -> None:
    """
    Equals signs after the first separator belong to the path.
    """

    result = parse_path_bindings(
        ("manifest=external/a=b.json",),
        project_root=tmp_path,
    )

    assert result == {
        "manifest": (tmp_path / "external" / "a=b.json"),
    }


# =========================================================
# Parameter bindings
# =========================================================


def test_parse_parameter_bindings_parses_integer() -> None:
    """
    Integer parameter values become Python integers.
    """

    result = parse_parameter_bindings(("artwork_colors=5",))

    assert result == {
        "artwork_colors": 5,
    }

    assert isinstance(
        result["artwork_colors"],
        int,
    )


def test_parse_parameter_bindings_parses_float() -> None:
    """
    Floating-point parameter values become Python floats.
    """

    result = parse_parameter_bindings(("artwork_size=90.5",))

    assert result == {
        "artwork_size": 90.5,
    }

    assert isinstance(
        result["artwork_size"],
        float,
    )


def test_parse_parameter_bindings_parses_true() -> None:
    """
    The literal true becomes a Python boolean.
    """

    result = parse_parameter_bindings(("enabled=true",))

    assert result == {
        "enabled": True,
    }


def test_parse_parameter_bindings_parses_false() -> None:
    """
    The literal false becomes a Python boolean.
    """

    result = parse_parameter_bindings(("enabled=false",))

    assert result == {
        "enabled": False,
    }


def test_parse_parameter_bindings_preserves_string() -> None:
    """
    Ordinary parameter text remains a Python string.
    """

    result = parse_parameter_bindings(("label=Happy Holidays",))

    assert result == {
        "label": "Happy Holidays",
    }


def test_parse_parameter_bindings_preserves_empty_string() -> None:
    """
    An explicitly empty parameter value is an empty string.
    """

    result = parse_parameter_bindings(("label=",))

    assert result == {
        "label": "",
    }


def test_parse_parameter_bindings_accepts_multiple_bindings() -> None:
    """
    Repeated parameter options produce one typed value mapping.
    """

    result = parse_parameter_bindings(
        (
            "artwork_size=90",
            "enabled=true",
            "label=portrait",
        )
    )

    assert result == {
        "artwork_size": 90,
        "enabled": True,
        "label": "portrait",
    }


def test_parse_parameter_bindings_returns_empty_mapping() -> None:
    """
    No parameter bindings produce an empty mapping.
    """

    result = parse_parameter_bindings(())

    assert result == {}


def test_parse_parameter_bindings_rejects_missing_equals() -> None:
    """
    A parameter binding must contain a semantic name and value.
    """

    with pytest.raises(
        BindingError,
        match="NAME=VALUE",
    ):
        parse_parameter_bindings(("artwork_size",))


def test_parse_parameter_bindings_rejects_empty_name() -> None:
    """
    A parameter binding must identify a semantic name.
    """

    with pytest.raises(
        BindingError,
        match="name",
    ):
        parse_parameter_bindings(("=90",))


def test_parse_parameter_bindings_rejects_duplicate_name() -> None:
    """
    A semantic parameter name may be bound only once.
    """

    with pytest.raises(
        BindingError,
        match="Duplicate",
    ):
        parse_parameter_bindings(
            (
                "artwork_size=90",
                "artwork_size=100",
            )
        )


def test_parse_parameter_bindings_preserves_equals_in_string() -> None:
    """
    Equals signs after the first separator belong to the value.
    """

    result = parse_parameter_bindings(("label=a=b",))

    assert result == {
        "label": "a=b",
    }


# =========================================================
# Parameter inference
# =========================================================


@pytest.mark.parametrize(
    (
        "text",
        "expected",
    ),
    [
        (
            "0",
            0,
        ),
        (
            "-12",
            -12,
        ),
        (
            "+12",
            12,
        ),
        (
            "0.0",
            0.0,
        ),
        (
            "-12.5",
            -12.5,
        ),
        (
            "+12.5",
            12.5,
        ),
        (
            "true",
            True,
        ),
        (
            "false",
            False,
        ),
        (
            "TRUE",
            "TRUE",
        ),
        (
            "False",
            "False",
        ),
        (
            "1e3",
            1000.0,
        ),
        (
            "portrait",
            "portrait",
        ),
        (
            "90mm",
            "90mm",
        ),
    ],
)
def test_parse_parameter_bindings_infers_simple_values(
    text: str,
    expected: object,
) -> None:
    """
    Parameter inference recognizes only simple scalar forms.
    """

    result = parse_parameter_bindings((f"value={text}",))

    assert result == {
        "value": expected,
    }


# =========================================================
# Semantic isolation
# =========================================================


def test_parameter_parser_does_not_validate_stage_parameter_names() -> None:
    """
    Stage-specific semantic validation belongs to the engine.
    """

    result = parse_parameter_bindings(("whatever=42",))

    assert result == {
        "whatever": 42,
    }


def test_path_parser_does_not_validate_stage_binding_names(
    tmp_path: Path,
) -> None:
    """
    Stage-specific path-name validation belongs to the engine.
    """

    result = parse_path_bindings(
        ("whatever=external/value.dat",),
        project_root=tmp_path,
    )

    assert result == {
        "whatever": (tmp_path / "external" / "value.dat"),
    }
