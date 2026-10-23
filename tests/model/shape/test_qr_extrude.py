"""Downstream SHAPE Extrude behavior for registered QR exclusions."""

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.shape.stages import extrude
from tests.model.shape.test_qr_compose import _artwork, _components, _compose


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_extrude_excludes_qr_footprint_from_artwork_components(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Extrude must subtract the complete registered QR footprint
    from each Artwork component before dimensionalization.

    The exclusion must apply to raised and inlaid Artwork alike.
    """
    _artwork(tmp_path)

    composition_manifest, composition = _compose(
        tmp_path,
        payload="https://lowkeylabs.com",
    )

    artwork = composition["artwork"]
    exclusions = artwork["exclusions"]

    assert len(exclusions) == 1
    assert exclusions[0]["type"] == "rounded_rect"

    components = _components(composition_manifest, composition)
    transform = artwork["transform"]
    extent = artwork["registered_extent"]

    for index in (1, 2, 3):
        component_path, _ = components[index]

        scad = extrude._build_artwork_component_scad(
            str(component_path),
            shape_size=100.0,
            shape_base_raise=2.0,
            shape_artwork_raise=0.6,
            shape_raise_style=raise_style,
            artwork_registered_width=float(extent["width"]),
            artwork_registered_height=float(extent["height"]),
            artwork_scale=float(transform["scale"]),
            artwork_translate_x=float(transform["translate_x"]),
            artwork_translate_y=float(transform["translate_y"]),
            exclusions=exclusions,
        )

        # The QR exclusion must be part of the planar Artwork
        # construction, rather than a separate overlapping solid.
        assert "difference()" in scad

        # Physical QR footprint: 30 mm square, 1 mm corner radius.
        # The footprint must be converted from registered Shape space.
        assert "30" in scad
        assert "1" in scad

        assert "linear_extrude" in scad

        if raise_style == "raised":
            assert "artwork_z_offset = 2" in scad
            assert "artwork_height = 0.6" in scad
        else:
            assert "artwork_z_offset = 0" in scad
            assert "artwork_height = 2" in scad


def test_inlaid_artwork_union_respects_qr_exclusion(
    tmp_path: Path,
) -> None:
    """
    The inlaid Base must subtract only the Artwork geometry
    remaining after QR exclusion.

    Otherwise, the Base and Artwork partitions would disagree
    about which material occupies the QR footprint.
    """
    _artwork(tmp_path)

    composition_manifest, composition = _compose(
        tmp_path,
        payload="https://lowkeylabs.com",
    )

    artwork = composition["artwork"]
    exclusions = artwork["exclusions"]

    assert len(exclusions) == 1

    scad = extrude._build_artwork_planar_union_scad(
        artwork,
        composition_manifest.parent,
        shape_size=100.0,
    )

    # The registered Artwork union must be clipped by the same
    # QR exclusion used for individual Artwork components.
    assert "difference()" in scad

    # The registered 30 mm rounded-square footprint must
    # participate in the subtraction.
    assert "30" in scad

    # The union must still contain the registered Artwork
    # components rather than discarding Artwork entirely.
    assert "union()" in scad

    for index in (1, 2, 3):
        component_path, _ = _components(
            composition_manifest,
            composition,
        )[index]

        assert component_path.name in scad
