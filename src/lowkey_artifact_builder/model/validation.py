"""
Model-owned resolved-configuration validation.

Validation is distinct from configuration resolution.

Configuration resolution determines effective values. Validation determines
whether resolved values satisfy model-specific invariants.

This module provides only the generic mechanism for executing model validators.
Determining which validators participate in a particular build belongs to
planning.
"""
# File: src/lowkey_artifact_builder/model/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

# =========================================================
# Resolver protocol
# =========================================================


class ConfigurationResolver(Protocol):
    """
    Provide read access to resolved configuration values.

    Validators depend only on resolved configuration access rather than
    on the concrete configuration Resolver implementation.
    """

    def __call__(
        self,
        name: str,
    ) -> object:
        """
        Return one resolved configuration value.
        """
        ...


# =========================================================
# Validator contract
# =========================================================


type ConfigurationValidator = Callable[
    [ConfigurationResolver],
    None,
]


# =========================================================
# Validation
# =========================================================


def validate_configuration(
    resolver: ConfigurationResolver,
    *,
    validators: tuple[ConfigurationValidator, ...],
) -> None:
    """
    Apply model-owned validators to resolved configuration.

    Validators execute in their declared order.

    A model with no validators is valid by default.

    Validators signal invalid configuration by raising the appropriate
    configuration error. Validation errors are intentionally not caught
    or transformed here.
    """

    for validator in validators:
        validator(resolver)


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ConfigurationResolver",
    "ConfigurationValidator",
    "validate_configuration",
]
