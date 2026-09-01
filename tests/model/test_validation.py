"""
Tests for model-owned configuration validation.
"""
# File: tests/model/test_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.model.validation import (
    ConfigurationResolver,
    ConfigurationValidator,
    get_model_validators,
    validate_configuration,
)

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal resolved-configuration source for validation tests.
    """

    def __init__(
        self,
        values: dict[str, object],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]


def _require_string(
    value: object,
) -> str:
    """
    Narrow a resolved test value to a string.
    """

    if not isinstance(value, str):
        raise TypeError("Expected a string.")

    return value


def _require_string_collection(
    value: object,
) -> tuple[str, ...]:
    """
    Narrow a resolved test value to a collection of strings.
    """

    if not isinstance(value, list | tuple):
        raise TypeError("Expected a list or tuple.")

    if not all(isinstance(item, str) for item in value):
        raise TypeError("Expected only strings.")

    return tuple(value)


def _write_model_package(
    root: Path,
    *,
    name: str,
    validation_source: str | None = None,
) -> Path:
    """
    Create a minimal importable model package for discovery tests.
    """

    package = root / name

    package.mkdir()

    (package / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    if validation_source is not None:
        (package / "validation.py").write_text(
            validation_source,
            encoding="utf-8",
        )

    return package


def _write_test_model_root(
    tmp_path: Path,
    *,
    package_name: str,
    model_name: str = "model",
    validation_source: str | None = None,
) -> str:
    """
    Create an isolated top-level package containing one test model.

    Each discovery test uses a distinct top-level package name so Python's
    import cache cannot retain a package path created by another test.
    """

    package_root = tmp_path / package_name

    package_root.mkdir()

    (package_root / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    _write_model_package(
        package_root,
        name=model_name,
        validation_source=validation_source,
    )

    return f"{package_name}.{model_name}"


# =========================================================
# Model validation
# =========================================================


def test_model_with_no_validators_is_valid() -> None:
    """
    Models are not required to define configuration validators.
    """

    resolver = StubResolver({})

    validate_configuration(
        resolver,
        validators=(),
    )


def test_model_validator_declares_relevant_parameters() -> None:
    """
    A model validator explicitly declares the configuration governed by
    its invariant.
    """

    def validate_pair(
        resolver: ConfigurationResolver,
    ) -> None:
        del resolver

    validator = ConfigurationValidator(
        parameters=(
            "left",
            "right",
        ),
        validate=validate_pair,
    )

    assert validator.parameters == (
        "left",
        "right",
    )


def test_model_validator_can_inspect_multiple_resolved_values() -> None:
    """
    Model validators may express cross-parameter invariants.
    """

    observed: list[tuple[object, object]] = []

    def validate_pair(
        resolver: ConfigurationResolver,
    ) -> None:
        observed.append(
            (
                resolver("left"),
                resolver("right"),
            )
        )

    validator = ConfigurationValidator(
        parameters=(
            "left",
            "right",
        ),
        validate=validate_pair,
    )

    resolver = StubResolver(
        {
            "left": "alpha",
            "right": "beta",
        }
    )

    validate_configuration(
        resolver,
        validators=(validator,),
    )

    assert observed == [
        (
            "alpha",
            "beta",
        )
    ]


def test_valid_model_configuration_passes_validation() -> None:
    """
    A satisfied model invariant allows validation to complete.
    """

    def validate_membership(
        resolver: ConfigurationResolver,
    ) -> None:
        selected = _require_string(
            resolver("selected"),
        )
        allowed = _require_string_collection(
            resolver("allowed"),
        )

        if selected not in allowed:
            raise ConfigError("selected must belong to allowed.")

    validator = ConfigurationValidator(
        parameters=(
            "selected",
            "allowed",
        ),
        validate=validate_membership,
    )

    resolver = StubResolver(
        {
            "selected": "red",
            "allowed": ("red", "blue"),
        }
    )

    validate_configuration(
        resolver,
        validators=(validator,),
    )


def test_invalid_model_configuration_raises_config_error() -> None:
    """
    A violated model invariant fails configuration validation.
    """

    def validate_membership(
        resolver: ConfigurationResolver,
    ) -> None:
        selected = _require_string(
            resolver("selected"),
        )
        allowed = _require_string_collection(
            resolver("allowed"),
        )

        if selected not in allowed:
            raise ConfigError("selected must belong to allowed.")

    validator = ConfigurationValidator(
        parameters=(
            "selected",
            "allowed",
        ),
        validate=validate_membership,
    )

    resolver = StubResolver(
        {
            "selected": "green",
            "allowed": ("red", "blue"),
        }
    )

    with pytest.raises(
        ConfigError,
        match="selected must belong to allowed",
    ):
        validate_configuration(
            resolver,
            validators=(validator,),
        )


def test_validating_configuration_executes_validators_in_declaration_order() -> None:
    """
    Generic validation preserves model validator declaration order.
    """

    observed: list[str] = []

    def validate_first(
        resolver: ConfigurationResolver,
    ) -> None:
        del resolver
        observed.append("first")

    def validate_second(
        resolver: ConfigurationResolver,
    ) -> None:
        del resolver
        observed.append("second")

    resolver = StubResolver({})

    validate_configuration(
        resolver,
        validators=(
            ConfigurationValidator(
                parameters=("first",),
                validate=validate_first,
            ),
            ConfigurationValidator(
                parameters=("second",),
                validate=validate_second,
            ),
        ),
    )

    assert observed == [
        "first",
        "second",
    ]


# =========================================================
# Model validator discovery
# =========================================================


def test_model_without_validation_module_has_no_validators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A model need not declare configuration validators.
    """

    model_package = _write_test_model_root(
        tmp_path,
        package_name="validation_test_models_plain",
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    validators = get_model_validators(
        model_package,
    )

    assert validators == ()


def test_model_validation_module_declares_validators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Validators declared by a model are discovered in declaration order.
    """

    model_package = _write_test_model_root(
        tmp_path,
        package_name="validation_test_models_declared",
        validation_source="""
from lowkey_artifact_builder.model.validation import ConfigurationValidator


def validate_first(resolver):
    pass


def validate_second(resolver):
    pass


VALIDATORS = (
    ConfigurationValidator(
        parameters=("first",),
        validate=validate_first,
    ),
    ConfigurationValidator(
        parameters=("second",),
        validate=validate_second,
    ),
)
""",
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    validators = get_model_validators(
        model_package,
    )

    assert tuple(validator.validate.__name__ for validator in validators) == (
        "validate_first",
        "validate_second",
    )

    assert tuple(validator.parameters for validator in validators) == (
        ("first",),
        ("second",),
    )


def test_discovering_model_validators_does_not_execute_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Validator discovery does not itself perform configuration validation.
    """

    model_package = _write_test_model_root(
        tmp_path,
        package_name="validation_test_models_not_executed",
        validation_source="""
from lowkey_artifact_builder.model.validation import ConfigurationValidator


def validate_configuration(resolver):
    raise RuntimeError("validator executed")


VALIDATORS = (
    ConfigurationValidator(
        parameters=("value",),
        validate=validate_configuration,
    ),
)
""",
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    validators = get_model_validators(
        model_package,
    )

    assert len(validators) == 1


def test_discovered_model_validator_receives_resolved_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Discovered validators use the generic resolved-configuration contract.
    """

    model_package = _write_test_model_root(
        tmp_path,
        package_name="validation_test_models_resolved",
        validation_source="""
from lowkey_artifact_builder.model.validation import ConfigurationValidator


def validate_pair(resolver):
    left = resolver("left")
    right = resolver("right")

    if left != right:
        raise RuntimeError("resolved values differ")


VALIDATORS = (
    ConfigurationValidator(
        parameters=(
            "left",
            "right",
        ),
        validate=validate_pair,
    ),
)
""",
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    validators = get_model_validators(
        model_package,
    )

    resolver = StubResolver(
        {
            "left": "same",
            "right": "same",
        }
    )

    validate_configuration(
        resolver,
        validators=validators,
    )
