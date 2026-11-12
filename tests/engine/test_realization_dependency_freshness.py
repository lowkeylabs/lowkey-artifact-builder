"""
Selected Artwork Realization dependency fingerprint isolation.

Each Shape Realization consumes only the Artwork Product selected by
its producer's effective representation and processing configuration.

Changes to a selected producer's required fingerprint invalidate its
consumer without invalidating unrelated consumers. Changes to
unselected Artwork products do not affect consumer fingerprints.

These tests do not execute manufacturing stages.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    ProductFingerprint,
    create_build_plan,
    create_required_fingerprints,
)
from lowkey_artifact_builder.model import ProductRef

ARTIFACT_ID = "example"


def _configure(project_root: Path) -> None:
    write_artifact_config(
        ARTIFACT_ID,
        {
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
                        "manifest": {
                            "artifact": ARTIFACT_ID,
                            "realization": "artwork_color",
                        },
                    },
                },
                "coaster_engrave": {
                    "variant": "shape.coaster",
                    "product_dependencies": {
                        "manifest": {
                            "artifact": ARTIFACT_ID,
                            "realization": "artwork_vector",
                        },
                    },
                },
            },
        },
        project_root=project_root,
    )


def _shape_plan(project_root: Path, realization: str):
    return create_build_plan(
        ARTIFACT_ID,
        realization=realization,
        targets=(
            ProductRef(
                artifact=ARTIFACT_ID,
                model="shape",
                realization=realization,
                stage="compose",
                product="artifact",
            ),
        ),
        project_root=project_root,
    )


def _fingerprint(value: str) -> ProductFingerprint:
    return ProductFingerprint(
        algorithm="sha256",
        value=value,
    )


def _required(
    plan,
    producer_fingerprints: dict[str, ProductFingerprint],
) -> dict[str, ProductFingerprint]:
    def resolve(dependency):
        return producer_fingerprints[dependency.binding.realization]

    return create_required_fingerprints(
        plan,
        product_dependency_fingerprint=resolve,
    )


def test_selected_artwork_change_invalidates_only_its_consumer(
    tmp_path: Path,
) -> None:
    """Changing one bound vector producer invalidates only its Shape consumer."""
    _configure(tmp_path)

    print_plan = _shape_plan(tmp_path, "coaster_print")
    engrave_plan = _shape_plan(tmp_path, "coaster_engrave")

    initial = {
        "artwork_default": _fingerprint("raster-v1"),
        "artwork_color": _fingerprint("color-v1"),
        "artwork_vector": _fingerprint("vector-v1"),
    }
    changed = {
        **initial,
        "artwork_color": _fingerprint("color-v2"),
    }

    print_before = _required(print_plan, initial)
    print_after = _required(print_plan, changed)
    engrave_before = _required(engrave_plan, initial)
    engrave_after = _required(engrave_plan, changed)

    assert print_before["structure"] == print_after["structure"]
    assert print_before["compose"] != print_after["compose"]

    assert engrave_before["structure"] == engrave_after["structure"]
    assert engrave_before["compose"] == engrave_after["compose"]


def test_selected_raster_artwork_fingerprint_participates_in_compose(
    tmp_path: Path,
) -> None:
    """
    A source-preserving raster Artwork producer invalidates Compose
    when its selected fingerprint changes.

    Both raster Artwork Products, artifact and metadata, must be
    selected from the same producer Realization.

    Changes to an unrelated vector producer do not invalidate Compose,
    and neither change invalidates Shape structure.
    """
    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": "source.png",
            "realizations": {
                "artwork_raster": {
                    "variant": "artwork.default",
                    "artwork_representation": "raster",
                    "artwork_processing": "none",
                },
                "artwork_vector": {
                    "variant": "artwork.default",
                },
                "coaster_print": {
                    "variant": "shape.coaster",
                    "product_dependencies": {
                        "manifest": {
                            "artifact": ARTIFACT_ID,
                            "realization": "artwork_raster",
                        },
                        "raster_artwork": {
                            "artifact": ARTIFACT_ID,
                            "realization": "artwork_raster",
                        },
                        "raster_metadata": {
                            "artifact": ARTIFACT_ID,
                            "realization": "artwork_raster",
                        },
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    plan = _shape_plan(tmp_path, "coaster_print")

    # Raster Artwork requires two selected registered Products.
    # The vector manifest must not participate.
    dependencies = {
        dependency.binding.dependency.name: dependency
        for dependency in plan.planned_product_dependencies
    }

    assert set(dependencies) == {
        "raster_artwork",
        "raster_metadata",
    }

    assert dependencies["raster_artwork"].product_ref == ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization="artwork_raster",
        stage="raster_source",
        product="artifact",
    )

    assert dependencies["raster_metadata"].product_ref == ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization="artwork_raster",
        stage="raster_source",
        product="metadata",
    )

    initial = {
        "artwork_raster": _fingerprint("raster-v1"),
        "artwork_vector": _fingerprint("vector-v1"),
    }

    first = _required(plan, initial)
    repeated = _required(plan, initial)

    changed_raster = _required(
        plan,
        {
            **initial,
            "artwork_raster": _fingerprint("raster-v2"),
        },
    )

    changed_vector = _required(
        plan,
        {
            **initial,
            "artwork_vector": _fingerprint("vector-v2"),
        },
    )

    # Fingerprinting is deterministic.
    assert first["compose"] == repeated["compose"]

    # The selected raster Artwork participates in Compose.
    assert first["compose"] != changed_raster["compose"]

    # The unrelated vector producer does not participate.
    assert first["compose"] == changed_vector["compose"]

    # Neither Artwork change affects Shape structure.
    assert first["structure"] == changed_raster["structure"]
    assert first["structure"] == changed_vector["structure"]


def test_unselected_artwork_fingerprint_is_not_requested(
    tmp_path: Path,
) -> None:
    """Fingerprinting consults bound producers, not unrelated siblings."""
    _configure(tmp_path)
    plan = _shape_plan(tmp_path, "coaster_print")

    requested: set[str] = set()
    producer_fingerprints = {
        "artwork_color": _fingerprint("color-v1"),
        "artwork_default": _fingerprint("raster-v1"),
    }

    def resolve(dependency):
        realization = dependency.binding.realization
        requested.add(realization)
        return producer_fingerprints[realization]

    fingerprints = create_required_fingerprints(
        plan,
        product_dependency_fingerprint=resolve,
    )

    assert "compose" in fingerprints
    assert "artwork_default" not in requested
    assert "artwork_color" in requested
    assert "artwork_vector" not in requested
    assert requested <= producer_fingerprints.keys()
