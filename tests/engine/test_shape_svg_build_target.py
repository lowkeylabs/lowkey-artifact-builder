"""First-class SHAPE SVG selection through the artifact-build API.

Phase 2, Slice A: an explicitly requested SVG is a terminal
manufacturing Product. The existing 3MF default remains compatible.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_artifact_build_plans,
    execute_artifact_build,
)
from lowkey_artifact_builder.model import ProductRef

ARTIFACT_ID = "svg-target"


def _configure(root: Path) -> None:
    write_artifact_config(
        ARTIFACT_ID,
        {
            "realizations": {
                "coaster_front": {"variant": "shape.coaster"},
                "coaster_back": {"variant": "shape.coaster"},
            },
        },
        project_root=root,
    )


def _svg_ref(realization: str) -> ProductRef:
    return ProductRef(
        artifact=ARTIFACT_ID,
        model="shape",
        realization=realization,
        stage="compose",
        product="artifact",
    )


def _root(root: Path, realization: str) -> Path:
    return root / "artifacts" / ARTIFACT_ID / "shape" / realization


def test_svg_target_plans_only_required_shape_stages(
    tmp_path: Path,
) -> None:
    """SVG selection ends at Compose without 3MF stages."""
    _configure(tmp_path)

    plans = create_artifact_build_plans(
        ARTIFACT_ID,
        realization="coaster_front",
        product="svg",
        project_root=tmp_path,
    )

    assert len(plans) == 1
    plan = plans[0]

    assert plan.targets == (_svg_ref("coaster_front"),)
    assert tuple(stage.name for stage in plan.stages) == (
        "structure",
        "compose",
    )


def test_svg_build_produces_independent_realization_products(
    tmp_path: Path,
) -> None:
    """Two requested SVGs are independently addressable."""
    _configure(tmp_path)

    for realization in ("coaster_front", "coaster_back"):
        execute_artifact_build(
            ARTIFACT_ID,
            realization=realization,
            product="svg",
            project_root=tmp_path,
        )

    for realization in ("coaster_front", "coaster_back"):
        base = _root(tmp_path, realization)

        svg = base / "20-compose" / "artifact.svg"
        assert svg.is_file()
        assert svg.stat().st_size > 0

        document = ET.parse(svg).getroot()
        assert document.tag == "{http://www.w3.org/2000/svg}svg"
        assert document.get("width")
        assert document.get("height")
        assert document.get("viewBox")

        assert not (base / "30-extrude").exists()
        assert not (base / "40-package").exists()


def test_explicit_3mf_target_preserves_existing_workflow(
    tmp_path: Path,
) -> None:
    """Explicit 3MF still uses the established package Product."""
    _configure(tmp_path)

    plans = create_artifact_build_plans(
        ARTIFACT_ID,
        realization="coaster_front",
        product="3mf",
        project_root=tmp_path,
    )

    assert len(plans) == 1
    assert plans[0].targets == (
        ProductRef(
            artifact=ARTIFACT_ID,
            model="shape",
            realization="coaster_front",
            stage="package",
            product="artifact",
        ),
    )


def test_omitted_target_selects_svg_default(
    tmp_path: Path,
) -> None:
    """Omitting Product selection targets the canonical SHAPE Compose SVG."""
    _configure(tmp_path)

    plans = create_artifact_build_plans(
        ARTIFACT_ID,
        realization="coaster_front",
        project_root=tmp_path,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.targets == (_svg_ref("coaster_front"),)

    assert tuple(stage.name for stage in plan.stages) == (
        "structure",
        "compose",
    )
