"""
Model-owned resolved-configuration validation.

Validation is distinct from configuration resolution.

Configuration resolution determines effective values. Validation determines
whether resolved values satisfy model-specific invariants.

This module provides the generic mechanisms for declaring, discovering, and
executing model-owned validators. Determining which validators participate in
a particular build belongs to execution-scoped validation.
"""
# File: src/lowkey_artifact_builder/model/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Protocol

# =========================================================
# Resolver protocol
# =========================================================


class ConfigurationResolver(Protocol):
    """
    Resolved configuration and shared reference data available to model
    validation rules.
    """

    def __call__(
        self,
        name: str,
    ) -> object: ...


# =========================================================
# Validator contract
# =========================================================


type ConfigurationValidation = Callable[
    [ConfigurationResolver],
    None,
]


@dataclass(
    frozen=True,
    slots=True,
)
class ConfigurationValidator:
    """
    One model-owned resolved-configuration invariant.

    Parameters identify the resolved configuration governed by the invariant.

    The execution-scoped validation layer uses this declaration to determine
    whether the invariant is relevant to required execution.

    Validate performs the model-owned semantic check. A validator may inspect
    any of its governed parameters, allowing cross-parameter invariants to be
    expressed without placing model-specific knowledge in generic planning or
    validation infrastructure.
    """

    parameters: tuple[str, ...]

    validate: ConfigurationValidation


# =========================================================
# Validator discovery
# =========================================================


def get_model_validators(
    model_package: str,
) -> tuple[ConfigurationValidator, ...]:
    """
    Return validators declared by one model package.

    A model may optionally provide a ``validation`` module containing a
    ``VALIDATORS`` tuple. Models without such a module declare no
    configuration validators.

    Discovery returns validators in their declared order and does not
    execute them.

    Import failures raised from inside an existing validation module are
    allowed to propagate. Only absence of the validation module itself
    means that the model declares no validators.
    """

    module_name = f"{model_package}.validation"

    try:
        module = import_module(
            module_name,
        )

    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return ()

        raise

    return _get_declared_validators(
        module,
    )


def get_named_model_validators(
    model_name: str,
) -> tuple[ConfigurationValidator, ...]:
    """
    Return configuration validators for one named built-in model.

    Model implementation package discovery belongs to the model subsystem.
    Callers identify a model by its public model name and need not know the
    package layout used by built-in model implementations.

    A model without a discoverable built-in implementation package declares
    no discoverable configuration validators. This permits programmatically
    defined and synthetic models to participate in generic planning and
    execution without requiring an implementation package.

    Errors raised while importing an existing model implementation or its
    validation module are not suppressed.
    """

    model_package = f"lowkey_artifact_builder.model.models.{model_name}"

    try:
        import_module(
            model_package,
        )
    except ModuleNotFoundError as exc:
        if exc.name == model_package:
            return ()

        raise

    return get_model_validators(
        model_package,
    )


def _get_declared_validators(
    module: ModuleType,
) -> tuple[ConfigurationValidator, ...]:
    """
    Return validators declared by an imported validation module.
    """

    validators = getattr(
        module,
        "VALIDATORS",
        (),
    )

    if not isinstance(validators, tuple):
        raise TypeError(f"{module.__name__}.VALIDATORS must be a tuple.")

    if not all(isinstance(validator, ConfigurationValidator) for validator in validators):
        raise TypeError(
            f"{module.__name__}.VALIDATORS must contain only ConfigurationValidator instances."
        )

    return validators


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
        validator.validate(
            resolver,
        )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ConfigurationResolver",
    "ConfigurationValidator",
    "get_model_validators",
    "get_named_model_validators",
    "validate_configuration",
]
