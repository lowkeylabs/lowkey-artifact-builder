"""
Tests for Coin product-targeted planning.

Coin exposes its physical component collection as an independently realizable
Product before final 3MF packaging. These tests establish that the Coin model
declaration participates correctly in dependency-driven minimal realization.
"""
# File: tests/model/coin/test_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import create_build_plan
from lowkey_artifact_builder.model import ProductRef


def test_coin_physical_product_stops_before_packaging(
    tmp_path: Path,
) -> None:
    """
    Targeting the physical Coin Product realizes only Coin composition.

    Compose retains both packaged Shape Product dependencies because they are
    required to construct the physical Coin. Final Coin packaging is a
    downstream consumer and must not participate merely because it belongs to
    the complete Coin workflow.
    """

    write_artifact_config(
        "example",
        {
            "model": "coin",
        },
        project_root=tmp_path,
    )

    target = ProductRef(
        artifact="example",
        model="coin",
        realization="coin_default",
        stage="compose",
        product="physical",
    )

    plan = create_build_plan(
        "example",
        model_name="coin",
        realization="coin_default",
        targets=(target,),
        project_root=tmp_path,
    )

    assert plan.targets == (target,)

    assert tuple(stage.name for stage in plan.stages) == ("compose",)

    assert tuple(
        (
            dependency.name,
            dependency.model,
            dependency.stage,
            dependency.product,
        )
        for dependency in plan.product_dependencies
    ) == (
        (
            "faceA",
            "shape",
            "package",
            "artifact",
        ),
        (
            "faceB",
            "shape",
            "package",
            "artifact",
        ),
    )

    assert all(stage.name != "package" for stage in plan.stages)


@pytest.mark.parametrize(
    (
        "face_a_artifact",
        "face_a_realization",
        "face_b_artifact",
        "face_b_realization",
    ),
    (
        (
            "shape-a",
            "shape_default",
            "shape-a",
            "shape_default",
        ),
        (
            "shape-a",
            "shape_default",
            "shape-a",
            "shape_inlaid",
        ),
        (
            "shape-a",
            "shape_default",
            "shape-b",
            "shape_default",
        ),
    ),
    ids=(
        "same-packaged-shape",
        "different-realizations",
        "different-artifacts",
    ),
)
def test_coin_faces_bind_independently_to_packaged_shape_products(
    tmp_path: Path,
    face_a_artifact: str,
    face_a_realization: str,
    face_b_artifact: str,
    face_b_realization: str,
) -> None:
    """
    Coin Face roles independently bind to complete packaged Shape Products.

    The two Faces may consume the same packaged Shape Product, different Shape
    Realizations of one Artifact, or packaged Shapes belonging to different
    Artifacts. Planning preserves each semantic Face role while resolving the
    configured producer identity.
    """

    write_artifact_config(
        "coin-example",
        {
            "model": "coin",
            "product_dependencies": {
                "faceA": {
                    "model": "shape",
                    "stage": "package",
                    "product": "artifact",
                    "artifact": face_a_artifact,
                    "realization": face_a_realization,
                },
                "faceB": {
                    "model": "shape",
                    "stage": "package",
                    "product": "artifact",
                    "artifact": face_b_artifact,
                    "realization": face_b_realization,
                },
            },
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "coin-example",
        model_name="coin",
        realization="coin_default",
        project_root=tmp_path,
    )

    assert tuple(
        (
            dependency.binding.dependency.name,
            dependency.binding.artifact,
            dependency.binding.realization,
            dependency.binding.dependency.model,
            dependency.binding.dependency.stage,
            dependency.binding.dependency.product,
        )
        for dependency in plan.planned_product_dependencies
    ) == (
        (
            "faceA",
            face_a_artifact,
            face_a_realization,
            "shape",
            "package",
            "artifact",
        ),
        (
            "faceB",
            face_b_artifact,
            face_b_realization,
            "shape",
            "package",
            "artifact",
        ),
    )
