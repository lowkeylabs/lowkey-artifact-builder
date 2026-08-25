"""
Command-line stage binding parsing.

This module translates human-oriented command-line bindings into the
typed mappings consumed by independent stage execution.

Binding parsing is intentionally independent of model and stage
semantics. The engine remains responsible for determining whether
input, parameter, and output names are valid for a requested stage.
"""
# File: src/lowkey_artifact_builder/cli/bindings.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

# =========================================================
# Errors
# =========================================================


class BindingError(ValueError):
    """
    Raised when a command-line binding cannot be parsed.
    """


# =========================================================
# Public interface
# =========================================================


def parse_path_bindings(
    bindings: Iterable[str],
    *,
    project_root: Path,
) -> dict[str, Path]:
    """
    Parse command-line NAME=PATH bindings.

    Relative paths are interpreted relative to project_root. Absolute
    paths are preserved.

    Binding names are treated as opaque semantic identifiers. This
    function does not determine whether a name is valid for any
    particular model or stage.

    A semantic name may appear at most once.
    """

    result: dict[str, Path] = {}

    for binding in bindings:
        name, value = _split_binding(
            binding,
            expected="NAME=PATH",
        )

        if not value:
            raise BindingError(f"Binding {binding!r} has an empty path.")

        if name in result:
            raise BindingError(f"Duplicate binding name {name!r}.")

        path = Path(
            value,
        )

        if not path.is_absolute():
            path = project_root / path

        result[name] = path

    return result


def parse_parameter_bindings(
    bindings: Iterable[str],
) -> dict[str, object]:
    """
    Parse command-line NAME=VALUE parameter bindings.

    Simple scalar values are inferred for human-friendly command-line
    use:

    - integer syntax becomes int;
    - floating-point syntax becomes float;
    - 'true' and 'false' become bool;
    - all other values remain strings.

    Empty parameter values are valid and become empty strings.

    Parameter names are treated as opaque semantic identifiers. This
    function does not determine whether a name is valid for any
    particular model or stage.

    A semantic name may appear at most once.
    """

    result: dict[str, object] = {}

    for binding in bindings:
        name, value = _split_binding(
            binding,
            expected="NAME=VALUE",
        )

        if name in result:
            raise BindingError(f"Duplicate binding name {name!r}.")

        result[name] = _parse_parameter_value(
            value,
        )

    return result


# =========================================================
# Binding syntax
# =========================================================


def _split_binding(
    binding: str,
    *,
    expected: str,
) -> tuple[str, str]:
    """
    Split one command-line binding at its first equals sign.

    Equals signs following the first separator are part of the binding
    value.
    """

    if "=" not in binding:
        raise BindingError(f"Invalid binding {binding!r}; expected {expected}.")

    name, value = binding.split(
        "=",
        1,
    )

    if not name:
        raise BindingError(f"Binding {binding!r} has an empty name.")

    return (
        name,
        value,
    )


# =========================================================
# Parameter values
# =========================================================


_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")

_FLOAT_PATTERN = re.compile(
    r"""
    ^[+-]?
    (?:
        (?:
            \d+\.\d*
            |
            \d*\.\d+
        )
        (?:
            [eE][+-]?\d+
        )?
        |
        \d+[eE][+-]?\d+
    )
    $
    """,
    re.VERBOSE,
)


def _parse_parameter_value(
    value: str,
) -> object:
    """
    Infer one simple command-line parameter value.

    Inference is deliberately conservative. Only unambiguous integer,
    floating-point, and lowercase boolean forms are converted. All
    other text remains a string.
    """

    if value == "true":
        return True

    if value == "false":
        return False

    if _INTEGER_PATTERN.fullmatch(
        value,
    ):
        return int(
            value,
        )

    if _FLOAT_PATTERN.fullmatch(
        value,
    ):
        return float(
            value,
        )

    return value


# =========================================================
# Exports
# =========================================================


__all__ = [
    "BindingError",
    "parse_parameter_bindings",
    "parse_path_bindings",
]
