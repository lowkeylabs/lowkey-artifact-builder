"""
Package registered Shape composition as a laser-ready SVG.
"""
# File: src/lowkey_artifact_builder/model/models/laser/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext

SVG_NS = "http://www.w3.org/2000/svg"
SVG = f"{{{SVG_NS}}}"

ET.register_namespace("", SVG_NS)


def _number(value: float) -> str:
    return format(value, ".12g")


def _load_svg(path: Path) -> ET.Element:
    """
    Load a registered SVG document.
    """
    root = ET.parse(path).getroot()

    if root.tag != f"{SVG}svg":
        raise ValueError(f"Expected SVG document: {path}")

    return root


def _add_structure(
    output: ET.Element,
    composition_path: Path,
) -> None:
    """
    Export registered structural boundaries as unfilled outlines.

    Shape Compose owns structural geometry. Laser reuses that
    geometry without converting the complete structural Base
    into an implicitly filled engraving region.

    Border-label baselines are construction geometry, not
    manufacturing objects. Their corresponding glyph geometry
    is exported separately from the registered label Products.
    """
    source = _load_svg(composition_path)

    structure = ET.SubElement(
        output,
        f"{SVG}g",
        {"id": "structure"},
    )

    construction_ids = {
        "top-border-label-path",
        "bottom-border-label-path",
    }

    for element in source:
        if element.get("id") in construction_ids:
            continue

        component = copy.deepcopy(element)

        component.set("fill", "none")
        component.set("stroke", "black")

        structure.append(component)


def _add_border_labels(
    output: ET.Element,
    directory: Path,
    border_labels: dict[str, Any],
) -> None:
    """
    Export participating registered border-label geometry.

    Each label is an independently identifiable SVG object.

    Shape Compose has already resolved text layout, font
    metrics, glyph geometry, and placement. Laser must not
    reconstruct typography or depend on installed fonts.
    """
    for position in ("top", "bottom"):
        entry = border_labels.get(position)

        if entry is None:
            continue

        source_path = directory / str(entry["path"])
        source = _load_svg(source_path)

        component = ET.SubElement(
            output,
            f"{SVG}g",
            {"id": f"{position}-border-label"},
        )

        for element in source:
            component.append(copy.deepcopy(element))


def _add_artwork(
    output: ET.Element,
    directory: Path,
    artwork: dict[str, Any],
) -> None:
    """
    Export registered Artwork using its persisted common transform.

    The transform maps source Artwork coordinates into registered
    Shape coordinates. Physical sizing is applied by the outer SVG.

    Each Artwork color region remains independently identifiable.
    """
    transform = artwork["transform"]

    scale = float(transform["scale"])
    tx = float(transform["translate_x"])
    ty = float(transform["translate_y"])

    if not all(math.isfinite(v) for v in (scale, tx, ty)):
        raise ValueError("Artwork transform must be finite.")

    if scale <= 0:
        raise ValueError("Artwork scale must be positive.")

    placement = ET.SubElement(
        output,
        f"{SVG}g",
        {
            "id": "artwork",
            "transform": (f"translate({_number(tx)} {_number(ty)}) scale({_number(scale)})"),
        },
    )

    for entry in artwork["components"]:
        index = int(entry["index"])
        source_path = directory / str(entry["path"])
        source = _load_svg(source_path)

        component = ET.SubElement(
            placement,
            f"{SVG}g",
            {"id": f"artwork-{index}"},
        )

        for element in source:
            component.append(copy.deepcopy(element))


def execute(context: StageContext) -> None:
    """
    Produce one physically dimensioned SVG from Shape Compose Products.

    The output contains participating registered geometry in a
    common coordinate system, without Shape extrusion or 3MF
    packaging.
    """
    manifest_path = context.input("shape.compose.manifest")
    output_path = context.output("artifact")

    shape_size = float(context.resolver("shape_size"))

    if not math.isfinite(shape_size) or shape_size <= 0:
        raise ValueError("shape_size must be finite and positive.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    directory = manifest_path.parent
    composition_path = directory / manifest["composition"]

    output = ET.Element(
        f"{SVG}svg",
        {
            "width": f"{_number(shape_size)}mm",
            "height": f"{_number(shape_size)}mm",
            "viewBox": "-0.5 -0.5 1 1",
        },
    )

    _add_structure(
        output,
        composition_path,
    )

    border_labels = manifest.get("border_labels")

    if border_labels is not None:
        _add_border_labels(
            output,
            directory,
            border_labels,
        )

    artwork = manifest.get("artwork")

    if artwork is not None:
        _add_artwork(
            output,
            directory,
            artwork,
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ET.ElementTree(output).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )
