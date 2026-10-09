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
