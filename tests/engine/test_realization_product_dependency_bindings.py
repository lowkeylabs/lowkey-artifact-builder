"""Realization-scoped Product dependency selection for existing Artwork geometry.

A consuming SHAPE Realization may override its Artifact's Product binding
without changing sibling Realizations or the canonical fallback.

This is the first RED slice of Phase 1; it tests planning, not manufacture.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plan,
    create_planned_stage_context,
    create_product_dependency_build_plan,
)
from lowkey_artifact_builder.model import ProductRef

ARTIFACT_ID = "example"


def _artwork_binding(realization: str) -> dict[str, str]:
    """Use the existing sparse Product-dependency binding format."""
    return {
        "artifact": ARTIFACT_ID,
        "realization": realization,
    }


def _shape_realization(
    artwork_realization: str | None = None,
) -> dict[str, object]:
    """Declare an ordinary coaster with an optional producer override."""
    configuration: dict[str, object] = {"variant": "shape.coaster"}
    if artwork_realization is not None:
        configuration["product_dependencies"] = {
            "manifest": _artwork_binding(artwork_realization),
        }
    return configuration


def _configure(
    project_root: Path,
    *,
    artifact_binding: str | None = None,
    print_binding: str | None = "artwork_color",
    engrave_binding: str | None = "artwork_vector",
) -> None:
    configuration: dict[str, object] = {
        "source": "source.png",
        "realizations": {
            "artwork_color": {"variant": "artwork.default"},
            "artwork_vector": {"variant": "artwork.default"},
            "coaster_print": _shape_realization(print_binding),
            "coaster_engrave": _shape_realization(engrave_binding),
        },
    }
    if artifact_binding is not None:
        configuration["product_dependencies"] = {
            "manifest": _artwork_binding(artifact_binding),
        }

    write_artifact_config(
        ARTIFACT_ID,
        configuration,
        project_root=project_root,
    )


def _svg_target(realization: str) -> ProductRef:
    return ProductRef(
        artifact=ARTIFACT_ID,
        model="shape",
        realization=realization,
        stage="compose",
        product="artifact",
    )


def _shape_svg_plan(project_root: Path, realization: str):
    return create_build_plan(
        ARTIFACT_ID,
        realization=realization,
        targets=(_svg_target(realization),),
        project_root=project_root,
    )


def _selected_artwork_product(realization: str) -> ProductRef:
    return ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization=realization,
        stage="vector",
        product="manifest",
    )


def test_two_shape_realizations_select_distinct_artwork_products(
    tmp_path: Path,
) -> None:
    """Binding is scoped to the consumer Realization, not the Artifact."""
    _configure(tmp_path)

    for consumer, producer in (
        ("coaster_print", "artwork_color"),
        ("coaster_engrave", "artwork_vector"),
    ):
        plan = _shape_svg_plan(tmp_path, consumer)

        assert tuple(stage.name for stage in plan.stages) == (
            "structure",
            "compose",
        )
        assert len(plan.planned_product_dependencies) == 1
        dependency = plan.planned_product_dependencies[0]
        assert dependency.product_ref == _selected_artwork_product(producer)
        assert dependency.path == (
            tmp_path
            / "artifacts"
            / ARTIFACT_ID
            / "artwork"
            / producer
            / "30-vector"
            / "products.json"
        )

        compose = next(stage for stage in plan.stages if stage.name == "compose")
        context = create_planned_stage_context(plan, compose)
        assert context.inputs["artwork.vector.manifest"] == dependency.path


def test_realization_binding_overrides_artifact_binding_without_leaking(
    tmp_path: Path,
) -> None:
    """The Artifact-level binding remains the fallback for other consumers."""
    _configure(
        tmp_path,
        artifact_binding="artwork_vector",
        print_binding="artwork_color",
        engrave_binding=None,
    )

    print_plan = _shape_svg_plan(tmp_path, "coaster_print")
    engrave_plan = _shape_svg_plan(tmp_path, "coaster_engrave")

    assert print_plan.planned_product_dependencies[0].product_ref == (
        _selected_artwork_product("artwork_color")
    )
    assert engrave_plan.planned_product_dependencies[0].product_ref == (
        _selected_artwork_product("artwork_vector")
    )


def test_unconfigured_consumer_retains_implicit_default_binding(
    tmp_path: Path,
) -> None:
    """An explicit sibling selection does not disable the legacy fallback."""
    _configure(
        tmp_path,
        print_binding="artwork_color",
        engrave_binding=None,
    )

    print_plan = _shape_svg_plan(tmp_path, "coaster_print")
    engrave_plan = _shape_svg_plan(tmp_path, "coaster_engrave")

    assert print_plan.planned_product_dependencies[0].product_ref == (
        _selected_artwork_product("artwork_color")
    )
    assert engrave_plan.planned_product_dependencies[0].product_ref == (
        _selected_artwork_product("artwork_default")
    )


def test_selected_artwork_product_has_targeted_producer_closure(
    tmp_path: Path,
) -> None:
    """The existing producer planner receives the selected Realization."""
    _configure(tmp_path)
    consumer_plan = _shape_svg_plan(tmp_path, "coaster_print")
    dependency = consumer_plan.planned_product_dependencies[0]

    producer_plan = create_product_dependency_build_plan(
        dependency,
        project_root=tmp_path,
    )

    assert producer_plan.model_name == "artwork"
    assert producer_plan.realization_name == "artwork_color"
    assert producer_plan.targets == (_selected_artwork_product("artwork_color"),)
    assert tuple(stage.name for stage in producer_plan.stages) == (
        "prepare",
        "raster",
        "vector",
    )
