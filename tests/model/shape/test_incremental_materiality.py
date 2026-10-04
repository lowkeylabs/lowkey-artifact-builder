"""
Tests for Shape incremental parameter materiality.

Shape stage fingerprints establish the boundary at which a configuration
change becomes material to manufacturing work.

Physical printer-color policy belongs exclusively to Package. Changing only
physical color policy must therefore preserve every upstream geometry
fingerprint.

Artwork-fill participation and height belong to Extrude. Changing
shape_artwork_fill_raise must therefore preserve registered geometry while
invalidating Extrude and downstream Package.
"""
# File: tests/model/shape/test_incremental_materiality.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedProduct,
    PlannedStage,
    create_required_fingerprints,
)
from lowkey_artifact_builder.model.models.shape import MODEL

# =========================================================
# Helpers
# =========================================================


def _shape_resolver(
    *,
    overrides: dict[str, object] | None = None,
) -> Resolver:
    """
    Construct the resolved Shape configuration needed by its StageSpecs.

    Values unrelated to the behavior under test remain fixed so fingerprint
    differences identify only the parameter whose materiality is being
    exercised.
    """

    values: dict[str, object] = {
        "shape_geometry": "circle",
        "shape_sides": 8,
        "shape_rotation": 0.0,
        "shape_size": 100.0,
        "shape_base_raise": 2.0,
        "shape_raise_style": "raised",
        "shape_outer_ridge_width": 0.0,
        "shape_outer_ridge_raise": 1.0,
        "shape_outer_ridge_style": "integrated",
        "shape_artwork_raise": 1.0,
        "shape_artwork_fill_raise": 0.0,
        "printer_colors": [
            "white",
            "black",
        ],
        "shape_base_color": "white",
    }

    if overrides is not None:
        values.update(
            overrides,
        )

    return Resolver(
        values=values,
        provenance={name: "test" for name in values},
        colors={
            "white": {
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
            "black": {
                "rgb": [
                    0,
                    0,
                    0,
                ],
            },
            "red": {
                "rgb": [
                    255,
                    0,
                    0,
                ],
            },
        },
    )


def _shape_plan(
    tmp_path: Path,
    *,
    overrides: dict[str, object] | None = None,
) -> BuildPlan:
    """
    Construct a complete Shape BuildPlan for fingerprint comparison.

    No external Artwork product is bound because this test concerns
    Shape-owned parameter materiality rather than cross-artifact dependency
    freshness.
    """

    artifact_dir = tmp_path / "artifacts" / "example"

    stages = tuple(
        PlannedStage(
            spec=stage,
            products=tuple(
                PlannedProduct(
                    spec=product,
                    path=(
                        artifact_dir
                        / "shape"
                        / "shape_default"
                        / f"{stage.id:02d}-{stage.name}"
                        / product.path
                    ),
                )
                for product in stage.products
            ),
        )
        for stage in MODEL.stages
    )

    return BuildPlan(
        artifact_id="example",
        model=MODEL,
        realization_name="shape_default",
        resolver=_shape_resolver(
            overrides=overrides,
        ),
        project_root=tmp_path,
        artifact_dir=artifact_dir,
        stages=stages,
    )


# =========================================================
# Physical-color materiality
# =========================================================


@pytest.mark.parametrize(
    ("parameter", "before_value", "after_value"),
    [
        (
            "printer_colors",
            ["white", "black"],
            ["red", "black"],
        ),
        (
            "shape_base_color",
            "white",
            "red",
        ),
        (
            "shape_outer_ridge_color",
            "white",
            "red",
        ),
        (
            "shape_artwork_fill_color",
            "white",
            "red",
        ),
        (
            "shape_loop_color",
            "white",
            "red",
        ),
    ],
)
def test_shape_physical_color_change_invalidates_only_package(
    tmp_path: Path,
    parameter: str,
    before_value: object,
    after_value: object,
) -> None:
    """
    Changing Shape physical-color policy preserves all upstream geometry.

    Physical printer-color assignment belongs exclusively to Package.
    Structure, Compose, and Extrude therefore retain identical required
    fingerprints while Package receives a different required fingerprint.
    """

    before = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                parameter: before_value,
            },
        )
    )

    after = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                parameter: after_value,
            },
        )
    )

    assert after["structure"] == before["structure"]
    assert after["compose"] == before["compose"]
    assert after["extrude"] == before["extrude"]

    assert after["package"] != before["package"]


# =========================================================
# Artwork-fill geometry materiality
# =========================================================


def test_shape_artwork_fill_raise_change_invalidates_extrude_and_package(
    tmp_path: Path,
) -> None:
    """
    Changing Artwork-fill height preserves registered geometry only.

    shape_artwork_fill_raise controls physical fill participation and height.
    It is therefore material to Extrude. Package depends on Extrude and must
    consequently receive a new required fingerprint as well.
    """

    before = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                "shape_artwork_fill_raise": 0.0,
            },
        )
    )

    after = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                "shape_artwork_fill_raise": 0.6,
            },
        )
    )

    assert after["structure"] == before["structure"]
    assert after["compose"] == before["compose"]

    assert after["extrude"] != before["extrude"]
    assert after["package"] != before["package"]


# =========================================================
# Raise-style materiality
# =========================================================


def test_shape_raise_style_change_invalidates_extrude_and_package(
    tmp_path: Path,
) -> None:
    """
    Changing Shape raise style preserves registered geometry only.

    shape_raise_style controls physical dimensionalization at Extrude.
    Structure and Compose therefore retain identical required fingerprints,
    while Extrude and downstream Package receive new required fingerprints.
    """

    before = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                "shape_raise_style": "raised",
            },
        )
    )

    after = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                "shape_raise_style": "inlaid",
            },
        )
    )

    assert after["structure"] == before["structure"]
    assert after["compose"] == before["compose"]

    assert after["extrude"] != before["extrude"]
    assert after["package"] != before["package"]


@pytest.mark.parametrize(
    ("parameter", "before_value", "after_value"),
    [
        (
            "shape_loop_inner_diameter",
            0.0,
            4.0,
        ),
        (
            "shape_loop_width",
            1.0,
            2.0,
        ),
        (
            "shape_loop_position",
            0,
            90,
        ),
        (
            "shape_loop_raise",
            2.0,
            3.0,
        ),
    ],
)
def test_shape_loop_geometry_change_invalidates_extrude_and_package(
    tmp_path: Path,
    parameter: str,
    before_value: object,
    after_value: object,
) -> None:
    """
    Changing Shape Loop physical geometry preserves registered geometry.

    Loop physical dimensionalization belongs to Extrude. Structure and
    Compose therefore retain identical required fingerprints while Extrude
    and downstream Package receive different required fingerprints.
    """

    before = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                parameter: before_value,
            },
        )
    )

    after = create_required_fingerprints(
        _shape_plan(
            tmp_path,
            overrides={
                parameter: after_value,
            },
        )
    )

    assert after["structure"] == before["structure"]
    assert after["compose"] == before["compose"]

    assert after["extrude"] != before["extrude"]
    assert after["package"] != before["package"]
