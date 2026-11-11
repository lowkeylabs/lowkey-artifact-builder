
"""
Selected Artwork Realization dependency fingerprint isolation.

Each Shape Realization consumes the registered Product of its selected
Artwork Realization. A change to one producer's required fingerprint
must affect its consumer without invalidating an unrelated consumer.

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
        return producer_fingerprints[
            dependency.binding.realization
        ]

    return create_required_fingerprints(
        plan,
        product_dependency_fingerprint=resolve,
    )


def test_selected_artwork_change_invalidates_only_its_consumer(
    tmp_path: Path,
) -> None:
    """
    A changed Artwork producer fingerprint affects only its bound Shape.

    Shape structural geometry does not depend on Artwork. The selected
    Artwork dependency enters the Shape compose stage.
    """
    _configure(tmp_path)

    print_plan = _shape_plan(tmp_path, "coaster_print")
    engrave_plan = _shape_plan(tmp_path, "coaster_engrave")

    initial = {
        "artwork_color": _fingerprint("color-v1"),
        "artwork_vector": _fingerprint("vector-v1"),
    }

    changed = {
        "artwork_color": _fingerprint("color-v2"),
        "artwork_vector": _fingerprint("vector-v1"),
    }

    print_before = _required(print_plan, initial)
    print_after = _required(print_plan, changed)

    engrave_before = _required(engrave_plan, initial)
    engrave_after = _required(engrave_plan, changed)

    assert print_before["structure"] == print_after["structure"]
    assert print_before["compose"] != print_after["compose"]

    assert engrave_before["structure"] == engrave_after["structure"]
    assert engrave_before["compose"] == engrave_after["compose"]


def test_selected_artwork_fingerprint_participates_in_compose(
    tmp_path: Path,
) -> None:
    """
    Compose provenance depends on the selected producer's fingerprint.

    Repeating the same producer fingerprint yields deterministic
    consumer fingerprints.
    """
    _configure(tmp_path)

    plan = _shape_plan(tmp_path, "coaster_print")

    first = _required(
        plan,
        {
            "artwork_color": _fingerprint("color-v1"),
        },
    )

    repeated = _required(
        plan,
        {
            "artwork_color": _fingerprint("color-v1"),
        },
    )

    changed = _required(
        plan,
        {
            "artwork_color": _fingerprint("color-v2"),
        },
    )

    assert first["compose"] == repeated["compose"]
    assert first["compose"] != changed["compose"]


def test_unselected_artwork_fingerprint_is_not_requested(
    tmp_path: Path,
) -> None:
    """
    Fingerprinting a Shape must not consult sibling Artwork Realizations.
    """
    _configure(tmp_path)

    plan = _shape_plan(tmp_path, "coaster_print")

    requested: list[str] = []

    def resolve(dependency):
        realization = dependency.binding.realization
        requested.append(realization)

        assert realization == "artwork_color"

        return _fingerprint("color-v1")

    fingerprints = create_required_fingerprints(
        plan,
        product_dependency_fingerprint=resolve,
    )

    assert "compose" in fingerprints
    assert requested == ["artwork_color"]
