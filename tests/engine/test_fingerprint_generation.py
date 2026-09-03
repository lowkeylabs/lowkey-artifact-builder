"""
Tests for deterministic build-context fingerprint generation.

Build-context fingerprints identify the semantic inputs that determine
persistent stage products.

These tests establish canonical fingerprint generation independently of
BuildPlan integration, completion persistence, filesystem evidence
gathering, execution-plan construction, and stage execution.
"""
# File: tests/engine/test_fingerprint_generation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.engine import (
    ProductFingerprint,
    create_product_fingerprint,
)

# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    *,
    parameters: dict[str, object] | None = None,
    inputs: dict[str, str] | None = None,
    operation: str = "artwork.vector.v1",
) -> ProductFingerprint:
    """
    Create a representative build-context fingerprint.
    """

    return create_product_fingerprint(
        parameters=parameters
        or {
            "size": 100.0,
            "materials": [
                "primary",
                "secondary",
            ],
        },
        inputs=inputs
        or {
            "mask": "mask-fingerprint",
            "colors": "colors-fingerprint",
        },
        operation=operation,
    )


# =========================================================
# Representation
# =========================================================


def test_created_fingerprint_uses_sha256() -> None:
    """
    Build-context fingerprints use the repository fingerprint algorithm.
    """

    fingerprint = _fingerprint()

    assert fingerprint.algorithm == "sha256"


def test_created_fingerprint_has_sha256_value() -> None:
    """
    Generated SHA-256 fingerprints contain a hexadecimal digest.
    """

    fingerprint = _fingerprint()

    assert len(fingerprint.value) == 64

    int(
        fingerprint.value,
        16,
    )


# =========================================================
# Determinism
# =========================================================


def test_same_build_context_produces_same_fingerprint() -> None:
    """
    Equivalent build contexts produce identical fingerprints.
    """

    assert _fingerprint() == _fingerprint()


def test_parameter_mapping_order_does_not_change_fingerprint() -> None:
    """
    Mapping insertion order is not semantically significant.
    """

    left = create_product_fingerprint(
        parameters={
            "artwork_size": 100.0,
            "artwork_raise": 1.0,
        },
        inputs={
            "mask": "mask-fingerprint",
        },
        operation="artwork.vector.v1",
    )

    right = create_product_fingerprint(
        parameters={
            "artwork_raise": 1.0,
            "artwork_size": 100.0,
        },
        inputs={
            "mask": "mask-fingerprint",
        },
        operation="artwork.vector.v1",
    )

    assert left == right


def test_input_mapping_order_does_not_change_fingerprint() -> None:
    """
    Input mapping insertion order is not semantically significant.
    """

    left = create_product_fingerprint(
        parameters={
            "artwork_size": 100.0,
        },
        inputs={
            "mask": "mask-fingerprint",
            "colors": "colors-fingerprint",
        },
        operation="artwork.vector.v1",
    )

    right = create_product_fingerprint(
        parameters={
            "artwork_size": 100.0,
        },
        inputs={
            "colors": "colors-fingerprint",
            "mask": "mask-fingerprint",
        },
        operation="artwork.vector.v1",
    )

    assert left == right


def test_nested_mapping_order_does_not_change_fingerprint() -> None:
    """
    Canonicalization applies recursively to nested mappings.
    """

    left = create_product_fingerprint(
        parameters={
            "settings": {
                "width": 100,
                "height": 80,
            },
        },
        inputs={},
        operation="example.v1",
    )

    right = create_product_fingerprint(
        parameters={
            "settings": {
                "height": 80,
                "width": 100,
            },
        },
        inputs={},
        operation="example.v1",
    )

    assert left == right


# =========================================================
# Parameter sensitivity
# =========================================================


def test_parameter_value_change_changes_fingerprint() -> None:
    """
    A changed resolved parameter invalidates the previous build context.
    """

    old = _fingerprint(
        parameters={
            "artwork_size": 100.0,
        },
    )

    new = _fingerprint(
        parameters={
            "artwork_size": 120.0,
        },
    )

    assert old != new


def test_parameter_name_change_changes_fingerprint() -> None:
    """
    Parameter identity participates in the build context.
    """

    left = _fingerprint(
        parameters={
            "artwork_size": 100.0,
        },
    )

    right = _fingerprint(
        parameters={
            "other_size": 100.0,
        },
    )

    assert left != right


def test_parameter_sequence_order_changes_fingerprint() -> None:
    """
    Sequence order remains semantically significant.
    """

    left = _fingerprint(
        parameters={
            "materials": [
                "primary",
                "secondary",
            ],
        },
    )

    right = _fingerprint(
        parameters={
            "materials": [
                "secondary",
                "primary",
            ],
        },
    )

    assert left != right


# =========================================================
# Input sensitivity
# =========================================================


def test_input_fingerprint_change_changes_fingerprint() -> None:
    """
    A changed upstream input invalidates the previous build context.
    """

    old = _fingerprint(
        inputs={
            "mask": "old-mask",
        },
    )

    new = _fingerprint(
        inputs={
            "mask": "new-mask",
        },
    )

    assert old != new


def test_input_identity_change_changes_fingerprint() -> None:
    """
    Logical input identity participates in the build context.
    """

    left = _fingerprint(
        inputs={
            "mask": "same-fingerprint",
        },
    )

    right = _fingerprint(
        inputs={
            "colors": "same-fingerprint",
        },
    )

    assert left != right


def test_added_input_changes_fingerprint() -> None:
    """
    Adding another dependency changes the required build context.
    """

    old = _fingerprint(
        inputs={
            "mask": "mask-fingerprint",
        },
    )

    new = _fingerprint(
        inputs={
            "mask": "mask-fingerprint",
            "colors": "colors-fingerprint",
        },
    )

    assert old != new


# =========================================================
# Operation sensitivity
# =========================================================


def test_operation_change_changes_fingerprint() -> None:
    """
    Changing the producing operation invalidates previous products.
    """

    old = _fingerprint(
        operation="artwork.vector.v1",
    )

    new = _fingerprint(
        operation="artwork.vector.v2",
    )

    assert old != new


# =========================================================
# Domain separation
# =========================================================


def test_parameter_and_input_namespaces_are_distinct() -> None:
    """
    Equivalent text in different semantic namespaces is not interchangeable.
    """

    parameter_context = create_product_fingerprint(
        parameters={
            "value": "abc",
        },
        inputs={},
        operation="example.v1",
    )

    input_context = create_product_fingerprint(
        parameters={},
        inputs={
            "value": "abc",
        },
        operation="example.v1",
    )

    assert parameter_context != input_context


def test_operation_and_parameter_namespaces_are_distinct() -> None:
    """
    Operation identity cannot collide with equivalent parameter text.
    """

    operation_context = create_product_fingerprint(
        parameters={},
        inputs={},
        operation="abc",
    )

    parameter_context = create_product_fingerprint(
        parameters={
            "operation": "abc",
        },
        inputs={},
        operation="",
    )

    assert operation_context != parameter_context
