"""Realization-scoped Product dependency selection for existing Artwork.

A consuming SHAPE Realization may override its Artifact's Product binding
without changing sibling Realizations or the canonical fallback.

SHAPE declares both vector and source-preserving raster Artwork dependencies.
The planner may bind both; representation selection is separate from binding.

These tests verify realization-scoped planning, not manufacture.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedProductDependency,
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


def _selected_raster_product(realization: str) -> ProductRef:
    return ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization=realization,
        stage="raster_source",
        product="artifact",
    )


def _planned_dependencies(
    plan: BuildPlan,
) -> dict[str, PlannedProductDependency]:
    """Index planned dependencies by their declared binding names."""
    return {
        dependency.binding.dependency.name or dependency.binding.dependency.product: dependency
        for dependency in plan.planned_product_dependencies
    }


def test_two_shape_realizations_select_distinct_artwork_products(
    tmp_path: Path,
) -> None:
    """
    Vector Artwork bindings are scoped to consumer Realizations.

    Each Shape Realization selects its configured Artwork producer.
    Because both producers use default vector Artwork, only the vector
    manifest participates in each BuildPlan.
    """
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

        dependencies = _planned_dependencies(plan)

        # Default vector Artwork selects only its vector manifest.
        assert set(dependencies) == {
            "manifest",
        }

        vector = dependencies["manifest"]

        # Each consumer retains its own configured producer.
        assert vector.product_ref == _selected_artwork_product(producer)

        assert vector.path == (
            tmp_path
            / "artifacts"
            / ARTIFACT_ID
            / "artwork"
            / producer
            / "30-vector"
            / "products.json"
        )

        # Compose receives the selected producer's vector manifest.
        compose = next(stage for stage in plan.stages if stage.name == "compose")

        context = create_planned_stage_context(
            plan,
            compose,
        )

        assert context.inputs["artwork.vector.manifest"] == vector.path

        # The alternative raster representation is not planned
        # or exposed to Compose.
        assert "raster_artwork" not in dependencies
        assert "raster_artwork" not in context.inputs
        assert "artwork.raster_source.artifact" not in context.inputs


def test_realization_binding_overrides_artifact_binding_without_leaking(
    tmp_path: Path,
) -> None:
    """The Artifact-level vector binding remains the fallback."""
    _configure(
        tmp_path,
        artifact_binding="artwork_vector",
        print_binding="artwork_color",
        engrave_binding=None,
    )

    print_plan = _shape_svg_plan(tmp_path, "coaster_print")
    engrave_plan = _shape_svg_plan(tmp_path, "coaster_engrave")

    print_dependencies = _planned_dependencies(print_plan)
    engrave_dependencies = _planned_dependencies(engrave_plan)

    assert print_dependencies["manifest"].product_ref == (
        _selected_artwork_product("artwork_color")
    )
    assert engrave_dependencies["manifest"].product_ref == (
        _selected_artwork_product("artwork_vector")
    )


def test_unconfigured_consumer_retains_implicit_default_binding(
    tmp_path: Path,
) -> None:
    """An explicit sibling selection does not disable legacy fallback."""
    _configure(
        tmp_path,
        print_binding="artwork_color",
        engrave_binding=None,
    )

    print_plan = _shape_svg_plan(tmp_path, "coaster_print")
    engrave_plan = _shape_svg_plan(tmp_path, "coaster_engrave")

    print_dependencies = _planned_dependencies(print_plan)
    engrave_dependencies = _planned_dependencies(engrave_plan)

    assert print_dependencies["manifest"].product_ref == (
        _selected_artwork_product("artwork_color")
    )
    assert engrave_dependencies["manifest"].product_ref == (
        _selected_artwork_product("artwork_default")
    )


def test_selected_artwork_product_has_targeted_producer_closure(
    tmp_path: Path,
) -> None:
    """The producer planner receives the selected vector Realization."""
    _configure(tmp_path)

    consumer_plan = _shape_svg_plan(tmp_path, "coaster_print")
    dependency = _planned_dependencies(consumer_plan)["manifest"]

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


def test_explicit_raster_binding_is_scoped_to_consumer_realization(
    tmp_path: Path,
) -> None:
    """
    An explicit raster binding is scoped to its consumer Realization.

    Binding a raster dependency does not itself select raster Artwork.
    The producer's effective representation determines which dependency
    participates in the BuildPlan.

    Both producers use default vector Artwork, so only their vector
    manifests should be planned.
    """
    _configure(tmp_path)

    configuration: dict[str, object] = {
        "source": "source.png",
        "realizations": {
            "artwork_color": {
                "variant": "artwork.default",
            },
            "artwork_vector": {
                "variant": "artwork.default",
            },
            "coaster_print": {
                "variant": "shape.coaster",
                "product_dependencies": {
                    "manifest": _artwork_binding("artwork_color"),
                    "raster_artwork": _artwork_binding("artwork_color"),
                },
            },
            "coaster_engrave": _shape_realization("artwork_vector"),
        },
    }

    write_artifact_config(
        ARTIFACT_ID,
        configuration,
        project_root=tmp_path,
    )

    print_plan = _shape_svg_plan(
        tmp_path,
        "coaster_print",
    )
    engrave_plan = _shape_svg_plan(
        tmp_path,
        "coaster_engrave",
    )

    print_dependencies = _planned_dependencies(print_plan)
    engrave_dependencies = _planned_dependencies(engrave_plan)

    # Both producers use default vector Artwork. The explicit raster
    # binding does not make the raster product an active dependency.
    assert set(print_dependencies) == {"manifest"}
    assert set(engrave_dependencies) == {"manifest"}

    # The print consumer retains its explicitly selected producer.
    assert print_dependencies["manifest"].product_ref == (
        _selected_artwork_product("artwork_color")
    )

    # The sibling consumer retains its independent producer binding.
    assert engrave_dependencies["manifest"].product_ref == (
        _selected_artwork_product("artwork_vector")
    )

    # The raster product is not planned for either vector consumer.
    assert "raster_artwork" not in print_dependencies
    assert "raster_artwork" not in engrave_dependencies


def test_default_artwork_selects_only_vector_dependency(
    tmp_path: Path,
) -> None:
    """Default vector Artwork excludes the raster producer dependency."""
    _configure(
        tmp_path,
        print_binding=None,
        engrave_binding=None,
    )

    plan = _shape_svg_plan(
        tmp_path,
        "coaster_print",
    )

    dependencies = _planned_dependencies(plan)

    assert set(dependencies) == {
        "manifest",
    }

    vector = dependencies["manifest"]

    assert vector.product_ref == _selected_artwork_product("artwork_default")

    compose = next(stage for stage in plan.stages if stage.name == "compose")

    context = create_planned_stage_context(
        plan,
        compose,
    )

    assert context.inputs["artwork.vector.manifest"] == vector.path
    assert "artwork.raster_source.artifact" not in context.inputs
    assert "artwork.raster_source.metadata" not in context.inputs


def test_source_preserving_raster_artwork_selects_only_raster_dependency(
    tmp_path: Path,
) -> None:
    """Raster Artwork excludes the vector producer dependency."""
    _configure(
        tmp_path,
        print_binding=None,
        engrave_binding=None,
    )

    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": "source.png",
            "artwork_representation": "raster",
            "artwork_processing": "none",
            "realizations": {
                "coaster_print": _shape_realization(),
            },
        },
        project_root=tmp_path,
    )

    plan = _shape_svg_plan(
        tmp_path,
        "coaster_print",
    )

    dependencies = _planned_dependencies(plan)

    assert set(dependencies) == {
        "raster_artwork",
    }

    raster = dependencies["raster_artwork"]

    assert raster.product_ref == _selected_raster_product("artwork_default")

    compose = next(stage for stage in plan.stages if stage.name == "compose")

    context = create_planned_stage_context(
        plan,
        compose,
    )

    assert context.inputs["raster_artwork"] == raster.path
    assert "artwork.vector.manifest" not in context.inputs
