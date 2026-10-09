"""
End-to-end acceptance tests for Coin artifact production.
"""
# File: tests/acceptance/test_coin_to_3mf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plans,
    execute_dependency_build,
)
from lowkey_artifact_builder.formats.threemf import read


@pytest.mark.slow
def test_coin_builds_from_packaged_shape_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A configured Coin builds through the ordinary dependency graph.

    Requesting only the Coin causes its two packaged Shape dependencies to
    manufacture first. Coin then consumes those persistent Shape Products,
    composes complete Faces, and packages the resulting two-sided physical
    object without requiring Coin-specific orchestration.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Configure two independent Shape producers
    # -----------------------------------------------------

    write_artifact_config(
        "face-a",
        {
            "model": "shape",
            "realizations": {
                "shape_default": {
                    "shape_base_color": "test-white",
                },
            },
        },
        project_root=project_root,
    )

    write_artifact_config(
        "face-b",
        {
            "model": "shape",
            "realizations": {
                "shape_default": {
                    "shape_raise_style": "inlaid",
                    "shape_base_color": "test-red",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Coin consumer
    # -----------------------------------------------------

    write_artifact_config(
        "coin-example",
        {
            "model": "coin",
            "product_dependencies": {
                "faceA": {
                    "model": "shape",
                    "stage": "package",
                    "product": "artifact",
                    "artifact": "face-a",
                    "realization": "shape_default",
                },
                "faceB": {
                    "model": "shape",
                    "stage": "package",
                    "product": "artifact",
                    "artifact": "face-b",
                    "realization": "shape_default",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Nothing has been manufactured
    # -----------------------------------------------------

    face_a_root = project_root / "artifacts" / "face-a" / "shape" / "shape_default"

    face_b_root = project_root / "artifacts" / "face-b" / "shape" / "shape_default"

    coin_root = project_root / "artifacts" / "coin-example" / "coin" / "coin_default"

    assert not face_a_root.exists()
    assert not face_b_root.exists()
    assert not coin_root.exists()

    # -----------------------------------------------------
    # Plan only the Coin
    # -----------------------------------------------------

    plans = create_build_plans(
        "coin-example",
        realization="coin_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "coin-example"
    assert plan.model_name == "coin"
    assert plan.realization_name == "coin_default"

    assert tuple(stage.spec.name for stage in plan.stages) == (
        "compose",
        "package",
    )

    # -----------------------------------------------------
    # Build through dependency-aware orchestration
    # -----------------------------------------------------

    execute_dependency_build(
        plan,
    )

    # -----------------------------------------------------
    # Both packaged Shape dependencies were manufactured
    # -----------------------------------------------------

    face_a_artifact = face_a_root / "40-package" / "artifact.3mf"

    face_b_artifact = face_b_root / "40-package" / "artifact.3mf"

    assert face_a_artifact.is_file()
    assert face_b_artifact.is_file()

    # -----------------------------------------------------
    # Coin physical Product and packaged Product exist
    # -----------------------------------------------------

    physical = coin_root / "10-compose" / "products.json"

    artifact = coin_root / "20-package" / "artifact.3mf"

    assert physical.is_file()
    assert artifact.is_file()
    assert artifact.stat().st_size > 0

    # -----------------------------------------------------
    # Final Coin contains both complete Face identities
    # -----------------------------------------------------

    components = read(
        artifact,
    )

    by_name = {component.name: component for component in components}

    assert set(by_name) == {
        "faceA-base - test-white",
        "faceB-base - test-red",
    }

    assert by_name["faceA-base - test-white"].color is not None
    assert by_name["faceA-base - test-white"].color.name == "test-white"

    assert by_name["faceB-base - test-red"].color is not None
    assert by_name["faceB-base - test-red"].color.name == "test-red"

    # -----------------------------------------------------
    # The two Faces occupy opposite sides of the mating plane
    # -----------------------------------------------------

    face_a_z = tuple(vertex[2] for vertex in by_name["faceA-base - test-white"].mesh.vertices)

    face_b_z = tuple(vertex[2] for vertex in by_name["faceB-base - test-red"].mesh.vertices)

    assert min(face_a_z) >= 0.0
    assert max(face_b_z) <= 0.0
