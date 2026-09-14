"""
Tests for reusable Artwork product Variants.
"""
# File: tests/model/artwork/test_variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.models.artwork import MODEL


def test_charm_and_earrings_are_distinct_looped_artwork_variants() -> None:
    """
    Charm and earrings are reusable looped Artwork configurations.

    Earrings are smaller and thinner than charms. Exact physical
    dimensions remain product-tuning decisions rather than behavioral
    contracts.
    """
    variants = {variant.name: variant for variant in MODEL.variants}

    charm = variants["charm"]
    earrings = variants["earrings"]

    assert charm.parameters["loop_inner_diameter"] > 0.0
    assert earrings.parameters["loop_inner_diameter"] > 0.0

    assert earrings.parameters["artwork_size"] < charm.parameters["artwork_size"]
    assert earrings.parameters["artwork_raise"] < charm.parameters["artwork_raise"]
