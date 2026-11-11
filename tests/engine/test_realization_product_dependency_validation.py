"""Validate concrete producers selected by Realization-scoped Product bindings.

Phase 1, Slice B: a binding must identify an existing, compatible producer
Realization capable of producing the required registered Product.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import create_build_plan
from lowkey_artifact_builder.engine.plan import BuildPlanError
from lowkey_artifact_builder.model import ProductRef

ARTIFACT_ID = "example"
CONSUMER = "coaster_print"


def _configure(project_root: Path, producer: str) -> None:
    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": "source.png",
            "realizations": {
                "artwork_color": {"variant": "artwork.default"},
                CONSUMER: {
                    "variant": "shape.coaster",
                    "product_dependencies": {
                        "manifest": {
                            "artifact": ARTIFACT_ID,
                            "realization": producer,
                        },
                    },
                },
            },
        },
        project_root=project_root,
    )


def _plan(project_root: Path):
    return create_build_plan(
        ARTIFACT_ID,
        realization=CONSUMER,
        targets=(
            ProductRef(
                artifact=ARTIFACT_ID,
                model="shape",
                realization=CONSUMER,
                stage="compose",
                product="artifact",
            ),
        ),
        project_root=project_root,
    )


def test_rejects_unknown_selected_artwork_realization(tmp_path: Path) -> None:
    _configure(tmp_path, "artwork_missing")

    with pytest.raises(BuildPlanError, match=r"artwork_missing"):
        _plan(tmp_path)


def test_rejects_selected_realization_of_wrong_model(tmp_path: Path) -> None:
    _configure(tmp_path, CONSUMER)

    with pytest.raises(BuildPlanError, match=r"coaster_print"):
        _plan(tmp_path)


def test_accepts_existing_compatible_artwork_realization(tmp_path: Path) -> None:
    _configure(tmp_path, "artwork_color")

    plan = _plan(tmp_path)

    assert plan.planned_product_dependencies[0].product_ref == ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization="artwork_color",
        stage="vector",
        product="manifest",
    )
