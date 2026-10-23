"""
Registered composition for the Shape model.

This module establishes the registered-geometry composition boundary for
Shape.

Registered structural Shape geometry and registered Artwork remain
nonphysical through this stage. Physical Shape dimensionalization and
extrusion belong to downstream Shape stages.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import math
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.border_labels import (
    bottom_label_path,
    fit_circular_border_labels,
    top_label_path,
    write_registered_circular_label_svg,
)
from lowkey_artifact_builder.model.models.shape.qr import (
    QR_CORNER_RADIUS_MM,
    QRInterior,
    RegisteredQR,
    compose_qr,
)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_CIRCLE = f"{{{SVG_NAMESPACE}}}circle"
SVG_RECT = f"{{{SVG_NAMESPACE}}}rect"
SVG_POLYGON = f"{{{SVG_NAMESPACE}}}polygon"
SVG_GROUP = f"{{{SVG_NAMESPACE}}}g"
SVG_PATH = f"{{{SVG_NAMESPACE}}}path"


# =========================================================
# Registered Artwork
# =========================================================


@dataclass(frozen=True)
class RegisteredExtent:
    """
    Common registered coordinate extent of an Artwork component collection.
    """

    width: float
    height: float


@dataclass(frozen=True)
class RegisteredBounds:
    """
    Bounds of occupied geometry in a registered coordinate system.
    """

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class RegisteredArtworkComponent:
    """
    One component declared by a registered Artwork manifest.

    Artifact color identity and measured RGB describe the persistent Artwork
    region. Physical printer-color assignment belongs to downstream packaging
    and is not part of registered Shape composition.
    """

    index: int
    path: Path
    artifact_color_index: int
    artifact_color: dict[str, int]


@dataclass(frozen=True)
class RegisteredArtwork:
    """
    Registered Artwork supplied to Shape through an Artwork vector manifest.

    The envelope and every component share the common registered coordinate
    system declared by registered_extent.
    """

    registered_extent: RegisteredExtent
    envelope: Path
    components: tuple[RegisteredArtworkComponent, ...]


@dataclass(frozen=True)
class RegisteredArtworkTransform:
    """
    One common transformation applied to registered Artwork.

    The transformation uniformly scales the registered coordinate system
    to fit within the available region and centers the transformed extent.
    """

    scale: float
    width: float
    height: float
    translate_x: float
    translate_y: float


@dataclass(frozen=True)
class PlacedRegisteredArtworkComponent:
    """
    One registered Artwork component associated with its common transform.

    The component payload remains unchanged and opaque at this boundary.
    """

    component: RegisteredArtworkComponent
    transform: RegisteredArtworkTransform


@dataclass(frozen=True)
class PlacedRegisteredArtwork:
    """
    Registered Artwork positioned within an available region.

    Every component shares the same transformation so their registered
    relationship is preserved.
    """

    transform: RegisteredArtworkTransform
    components: tuple[PlacedRegisteredArtworkComponent, ...]


@dataclass(frozen=True)
class ArtworkPlacementCircle:
    """
    Origin-centered circular placement region for registered Artwork.
    """

    center_x: float
    center_y: float
    radius: float


@dataclass(frozen=True)
class RegisteredArtworkFillRegion:
    """
    Registered Shape region available for Artwork fill.

    The Shape interior is the outer boundary. The authoritative registered
    Artwork envelope, transformed by the common Artwork placement transform,
    is the inner boundary.

    Both boundaries remain in registered Shape coordinates. Physical
    dimensionalization belongs to downstream Shape stages.
    """

    outer_boundary: ET.Element
    inner_boundary: ET.Element


# =========================================================
# Public interface
# =========================================================


def registered_interior_region(
    composition: Path,
) -> ET.Element:
    """
    Return the boundary defining the registered Shape interior region.

    The innermost participating structural feature defines the available
    Shape interior.

    Inner Ridge takes precedence when it participates. Otherwise, the
    Border Label inner boundary defines the interior when Border Labels
    participate. When neither exists, the Outer Ridge inside boundary
    defines the interior when present, falling back to the complete Shape
    boundary.
    """

    root = ET.parse(
        composition,
    ).getroot()

    inner_ridge_boundary = next(
        (element for element in root if element.get("id") == "inner-ridge-inner-boundary"),
        None,
    )

    if inner_ridge_boundary is not None:
        return inner_ridge_boundary

    border_label_boundary = next(
        (element for element in root if element.get("id") == "border-label-inner-boundary"),
        None,
    )

    if border_label_boundary is not None:
        return border_label_boundary

    outer_ridge_boundary = next(
        (element for element in root if element.get("id") == "ridge-inner-boundary"),
        None,
    )

    if outer_ridge_boundary is not None:
        return outer_ridge_boundary

    shape_boundary = next(
        (element for element in root if element.get("id") == "shape-boundary"),
        None,
    )

    if shape_boundary is not None:
        return shape_boundary

    shape_boundary = next(
        (
            element
            for element in root
            if element.tag
            in {
                SVG_CIRCLE,
                SVG_RECT,
                SVG_POLYGON,
            }
        ),
        None,
    )

    if shape_boundary is None:
        raise ValueError("Registered Shape composition requires a Shape boundary.")

    return shape_boundary


def _qr_registered_interior(
    composition: Path,
) -> QRInterior:
    """
    Resolve the available registered Shape interior for QR placement.

    Reuse the existing Shape interior selection policy. Preserve the
    actual circle, rectangle, or polygon boundary so QR containment
    considers the complete square footprint, including its corners.
    """
    boundary = registered_interior_region(composition)

    if boundary.tag == SVG_CIRCLE:
        return QRInterior(
            circle=(
                float(boundary.get("cx", "0.0")),
                float(boundary.get("cy", "0.0")),
                float(boundary.get("r", "0.0")),
            ),
        )

    if boundary.tag == SVG_RECT:
        x = float(boundary.get("x", "0.0"))
        y = float(boundary.get("y", "0.0"))
        width = float(boundary.get("width", "0.0"))
        height = float(boundary.get("height", "0.0"))

        return QRInterior(
            vertices=(
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
            ),
        )

    if boundary.tag == SVG_POLYGON:
        return QRInterior(
            vertices=_read_polygon_points(boundary),
        )

    raise ValueError(
        "QR placement requires a circular, rectangular, or polygonal registered Shape interior."
    )


def _validate_registered_artwork_placement(
    artwork: RegisteredArtwork,
    *,
    transform: RegisteredArtworkTransform,
    placement: ArtworkPlacementCircle,
) -> None:
    """
    Validate actual transformed Artwork envelope containment.

    Measure the maximum distance from the Shape interior center to
    the transformed envelope geometry, rather than using a bounding
    circle centered on the Artwork.

    This permits asymmetric Artwork to move within the interior
    while retaining exact radial containment.
    """
    if not math.isfinite(transform.scale) or transform.scale <= 0.0:
        raise ValueError("Artwork placement requires a positive finite scale.")

    root = ET.parse(artwork.envelope).getroot()
    envelope = next(iter(root), None)

    if envelope is None:
        raise ValueError("Registered Artwork envelope requires geometry.")

    # Map the Shape interior center back into source Artwork coordinates.
    # Uniform scaling preserves distances, so the maximum source-space
    # distance can be scaled back into registered Shape coordinates.
    source_center_x = (placement.center_x - transform.translate_x) / transform.scale

    source_center_y = (placement.center_y - transform.translate_y) / transform.scale

    occupied_radius = (
        _registered_element_radius(
            envelope,
            center_x=source_center_x,
            center_y=source_center_y,
        )
        * transform.scale
    )

    if not math.isfinite(occupied_radius):
        raise ValueError("Artwork placement produces non-finite geometry.")

    if occupied_radius > placement.radius + 1.0e-9:
        raise ValueError("Artwork placement exceeds the available Shape interior.")


def _registered_qr_footprint(
    qr: RegisteredQR,
    *,
    shape_size: float,
) -> dict[str, float | str]:
    """
    Resolve the QR exclusion footprint in registered Shape coordinates.

    The footprint includes the QR quiet zone and has a fixed 1 mm
    corner radius. It is the authoritative geometry shared by the
    QR background and Artwork subtraction.

    Physical dimensionalization remains downstream.
    """
    if shape_size <= 0.0:
        raise ValueError("Shape size must be positive.")

    footprint = qr.footprint

    if footprint.width <= 0.0 or footprint.height <= 0.0:
        raise ValueError("QR footprint must have positive dimensions.")

    corner_radius = QR_CORNER_RADIUS_MM / shape_size

    if 2.0 * corner_radius > min(
        footprint.width,
        footprint.height,
    ):
        raise ValueError("QR footprint is too small for the fixed 1 mm corner radius.")

    return {
        "type": "rounded_rect",
        "x": footprint.x,
        "y": footprint.y,
        "width": footprint.width,
        "height": footprint.height,
        "corner_radius": corner_radius,
    }


def execute(
    context: StageContext,
) -> None:
    """
    Execute registered Shape composition.

    Structural geometry and optional Artwork are composed in registered
    space. Artwork adjustments are applied after automatic fitting.

    A participating QR Code is generated as separate registered dark/light
    geometry without requiring Artwork.

    The canonical SVG is physically dimensioned but remains two-dimensional.
    Color assignment and physical extrusion remain downstream.
    """
    structure_input = context.input("structure.structure")
    composition_output = context.output("composition")
    manifest_output = context.output("manifest")
    artifact_output = context.output("artifact")

    shape_size = float(context.resolver("shape_size"))
    ridge_width = float(context.resolver("shape_outer_ridge_width"))
    ridge_style = str(context.resolver("shape_outer_ridge_style"))
    inner_ridge_width = float(context.resolver("shape_inner_ridge_width"))
    inner_to_outer_ridge_dist = float(context.resolver("shape_inner_to_outer_ridge_dist"))

    border_label_width = float(context.resolver("shape_border_label_width"))
    border_label_max_glyph_height = float(context.resolver("shape_border_label_max_glyph_height"))
    border_label_arc_degrees = float(context.resolver("shape_border_label_arc_degrees"))
    border_label_end_margin = float(context.resolver("shape_border_label_end_margin"))
    border_label_font_family = str(context.resolver("shape_border_label_font_family"))
    top_border_label_text = str(context.resolver("shape_top_border_label_text"))
    bottom_border_label_text = str(context.resolver("shape_bottom_border_label_text"))

    top_font_override = str(context.resolver("shape_top_border_label_font_family"))
    bottom_font_override = str(context.resolver("shape_bottom_border_label_font_family"))
    top_arc_override = float(context.resolver("shape_top_border_label_arc_degrees"))
    bottom_arc_override = float(context.resolver("shape_bottom_border_label_arc_degrees"))

    border_labels: dict[str, dict[str, object] | None] = {
        "top": None,
        "bottom": None,
    }

    if ridge_style in {"integrated", "separate"}:
        border_labels = _compose_ridge(
            structure_input,
            composition_output,
            shape_size=shape_size,
            ridge_width=ridge_width,
            inner_ridge_width=inner_ridge_width,
            inner_to_outer_ridge_dist=inner_to_outer_ridge_dist,
            border_label_width=border_label_width,
            border_label_max_glyph_height=border_label_max_glyph_height,
            border_label_arc_degrees=border_label_arc_degrees,
            border_label_end_margin=border_label_end_margin,
            border_label_font_family=border_label_font_family,
            top_border_label_text=top_border_label_text,
            bottom_border_label_text=bottom_border_label_text,
            border_label_output_directory=manifest_output.parent,
            top_border_label_font_family=top_font_override,
            bottom_border_label_font_family=bottom_font_override,
            top_border_label_arc_degrees=top_arc_override,
            bottom_border_label_arc_degrees=bottom_arc_override,
        )
    else:
        shutil.copyfile(
            structure_input,
            composition_output,
        )

    artwork: RegisteredArtwork | None = None
    artwork_transform: RegisteredArtworkTransform | None = None
    artwork_fill: RegisteredArtworkFillRegion | None = None

    if context.has_input("artwork.vector.manifest"):
        artwork_manifest = context.input("artwork.vector.manifest")
        artwork = load_registered_artwork(artwork_manifest)

        artwork_transform = fit_registered_artwork_to_shape(
            artwork,
            composition=composition_output,
            shape_size=shape_size,
            offset_x=float(context.resolver("shape_artwork_offset_x")),
            offset_y=float(context.resolver("shape_artwork_offset_y")),
            scale=float(context.resolver("shape_artwork_scale")),
        )

        artwork_fill = registered_artwork_fill_region(
            registered_interior_region(composition_output),
            artwork,
            transform=artwork_transform,
        )

    qr: RegisteredQR | None = None
    qr_payload = str(context.resolver("shape_qr_payload"))

    if qr_payload:
        qr = compose_qr(
            manifest_output.parent,
            payload=qr_payload,
            qr_size=float(context.resolver("shape_qr_size")),
            shape_size=shape_size,
            alignment=str(context.resolver("shape_qr_alignment")),
            position=float(context.resolver("shape_qr_position")),
            interior=_qr_registered_interior(composition_output),
        )

    _write_composition_manifest(
        manifest_output,
        composition=composition_output,
        border_labels=border_labels,
        artwork=artwork,
        artwork_transform=artwork_transform,
        artwork_fill=artwork_fill,
        qr=qr,
        shape_size=shape_size,
    )

    _write_artifact_svg(
        artifact_output,
        composition=composition_output,
        border_labels=border_labels,
        artwork=artwork,
        artwork_transform=artwork_transform,
        qr=qr,
        shape_size=shape_size,
    )


def _write_artifact_svg(
    path: Path,
    *,
    composition: Path,
    border_labels: dict[str, dict[str, object] | None],
    artwork: RegisteredArtwork | None,
    artwork_transform: RegisteredArtworkTransform | None,
    qr: RegisteredQR | None,
    shape_size: float,
) -> None:
    """
    Write the canonical, physically dimensioned Shape SVG.

    Registered structural boundaries become filled planar ridge regions.
    Border Labels and QR components reuse persistent registered geometry.

    Artwork retains its component identities, RGB colors, and common
    placement transform. A participating QR excludes its complete rounded
    footprint from Artwork, including the quiet zone.

    Construction geometry and the solid Shape Base are excluded.
    """
    if not math.isfinite(shape_size) or shape_size <= 0.0:
        raise ValueError("Canonical Shape SVG requires positive finite Shape size.")

    composition_root = ET.parse(composition).getroot()

    root = ET.Element(
        f"{{{SVG_NAMESPACE}}}svg",
        {
            "width": f"{shape_size:g}mm",
            "height": f"{shape_size:g}mm",
            "viewBox": "-0.5 -0.5 1 1",
        },
    )

    structural_group = ET.SubElement(
        root,
        SVG_GROUP,
        {"id": "structure"},
    )

    boundaries = {
        element.get("id"): element for element in composition_root if element.get("id") is not None
    }

    shape_boundary = boundaries.get("shape-boundary")

    if shape_boundary is None:
        raise ValueError("Canonical Shape SVG requires a registered Shape boundary.")

    outer_ridge_inner = boundaries.get("ridge-inner-boundary")

    if outer_ridge_inner is not None:
        ET.SubElement(
            structural_group,
            SVG_PATH,
            {
                "id": "outer-ridge",
                "d": (
                    _svg_boundary_path(shape_boundary) + " " + _svg_boundary_path(outer_ridge_inner)
                ),
                "fill": "black",
                "fill-rule": "evenodd",
                "stroke": "none",
            },
        )
    else:
        outline = ET.fromstring(ET.tostring(shape_boundary, encoding="unicode"))
        outline.set("fill", "none")
        outline.set("stroke", "black")
        outline.set("stroke-width", f"{0.1 / shape_size:g}")
        structural_group.append(outline)

    inner_ridge_outer = boundaries.get("inner-ridge-outer-boundary")
    inner_ridge_inner = boundaries.get("inner-ridge-inner-boundary")

    if (inner_ridge_outer is None) != (inner_ridge_inner is None):
        raise ValueError("Canonical Shape SVG requires both inner-ridge boundaries.")

    if inner_ridge_outer is not None and inner_ridge_inner is not None:
        ET.SubElement(
            structural_group,
            SVG_PATH,
            {
                "id": "inner-ridge",
                "d": (
                    _svg_boundary_path(inner_ridge_outer)
                    + " "
                    + _svg_boundary_path(inner_ridge_inner)
                ),
                "fill": "black",
                "fill-rule": "evenodd",
                "stroke": "none",
            },
        )

    # Border Labels are already fitted and vectorized by Compose.
    # Import their registered glyph geometry without repeating typography.

    for position in ("top", "bottom"):
        component = border_labels.get(position)

        if component is None:
            continue

        relative_path = component.get("path")

        if not isinstance(relative_path, str):
            raise ValueError(f"Canonical Shape SVG requires a registered {position} label path.")

        label_group = ET.SubElement(
            root,
            SVG_GROUP,
            {
                "id": f"{position}-border-label",
                "fill": "black",
                "stroke": "none",
            },
        )

        _append_registered_svg(
            label_group,
            path.parent / relative_path,
        )

    # The QR footprint is the authoritative exclusion geometry shared
    # by the manifest, QR background, and Artwork mask.

    footprint: dict[str, float | str] | None = None

    if qr is not None:
        footprint = _registered_qr_footprint(
            qr,
            shape_size=shape_size,
        )

    if artwork is not None:
        if artwork_transform is None:
            raise ValueError("Canonical Shape SVG requires registered Artwork placement.")

        artwork_group = ET.SubElement(
            root,
            SVG_GROUP,
            {
                "id": "artwork",
                "stroke": "none",
            },
        )

        if footprint is not None:
            defs = ET.SubElement(
                root,
                f"{{{SVG_NAMESPACE}}}defs",
            )

            mask = ET.SubElement(
                defs,
                f"{{{SVG_NAMESPACE}}}mask",
                {
                    "id": "qr-artwork-exclusion",
                    "maskUnits": "userSpaceOnUse",
                    "maskContentUnits": "userSpaceOnUse",
                    "x": "-0.5",
                    "y": "-0.5",
                    "width": "1",
                    "height": "1",
                    "style": "mask-type:luminance",
                },
            )

            ET.SubElement(
                mask,
                SVG_RECT,
                {
                    "x": "-0.5",
                    "y": "-0.5",
                    "width": "1",
                    "height": "1",
                    "fill": "white",
                },
            )

            ET.SubElement(
                mask,
                SVG_RECT,
                {
                    "x": f"{float(footprint['x']):g}",
                    "y": f"{float(footprint['y']):g}",
                    "width": f"{float(footprint['width']):g}",
                    "height": f"{float(footprint['height']):g}",
                    "rx": f"{float(footprint['corner_radius']):g}",
                    "ry": f"{float(footprint['corner_radius']):g}",
                    "fill": "black",
                },
            )

            artwork_group.set(
                "mask",
                "url(#qr-artwork-exclusion)",
            )

        transform = artwork_transform

        for component in artwork.components:
            rgb = component.artifact_color
            fill = f"#{rgb['red']:02x}{rgb['green']:02x}{rgb['blue']:02x}"

            component_group = ET.SubElement(
                artwork_group,
                SVG_GROUP,
                {
                    "id": f"artwork-{component.index}",
                    "fill": fill,
                    "transform": (
                        f"translate({transform.translate_x:g} "
                        f"{transform.translate_y:g}) "
                        f"scale({transform.scale:g})"
                    ),
                },
            )

            _append_registered_svg(
                component_group,
                component.path,
                fill=fill,
            )

    # QR is independent of Artwork. Its light background must cover
    # the entire quiet zone, and its dark modules remain a distinct
    # manufacturing component.

    if qr is not None:
        if footprint is None:
            raise ValueError("Canonical Shape SVG requires QR footprint.")

        for name in ("qr-light", "qr-dark"):
            component_path = qr.components.get(name)

            if component_path is None:
                raise ValueError(f"Canonical Shape SVG requires registered {name} geometry.")

            qr_group = ET.SubElement(
                root,
                SVG_GROUP,
                {
                    "id": name,
                    "fill": "white" if name == "qr-light" else "black",
                    "stroke": "none",
                },
            )

            if name == "qr-light":
                ET.SubElement(
                    qr_group,
                    SVG_RECT,
                    {
                        "x": f"{float(footprint['x']):g}",
                        "y": f"{float(footprint['y']):g}",
                        "width": f"{float(footprint['width']):g}",
                        "height": f"{float(footprint['height']):g}",
                        "rx": f"{float(footprint['corner_radius']):g}",
                        "ry": f"{float(footprint['corner_radius']):g}",
                    },
                )

            _append_registered_svg(
                qr_group,
                component_path,
            )

    ET.register_namespace("", SVG_NAMESPACE)

    ET.ElementTree(root).write(
        path,
        encoding="unicode",
        xml_declaration=True,
    )


def _append_registered_svg(
    destination: ET.Element,
    source: Path,
    *,
    fill: str | None = None,
) -> None:
    """
    Append persistent registered SVG geometry to an output group.

    The producer's root SVG is a registered coordinate container.
    Its children are copied without recomputing geometry, placement,
    typography, or component identity.

    When an authoritative fill is supplied, normalize copied SVG
    geometry to that color. Source files remain unchanged.

    The resulting canonical SVG is self-contained.
    """
    source_root = ET.parse(source).getroot()

    if source_root.tag != f"{{{SVG_NAMESPACE}}}svg":
        raise ValueError(f"Registered SVG component requires an SVG root: {source}")

    if not len(source_root):
        raise ValueError(f"Registered SVG component contains no geometry: {source}")

    for element in source_root:
        copied = ET.fromstring(ET.tostring(element, encoding="unicode"))

        if fill is not None:
            for descendant in copied.iter():
                style = descendant.get("style")

                if style is not None:
                    declarations = [
                        declaration.strip()
                        for declaration in style.split(";")
                        if declaration.strip()
                    ]

                    declarations = [
                        declaration
                        for declaration in declarations
                        if declaration.partition(":")[0].strip().lower() != "fill"
                    ]

                    if declarations:
                        descendant.set("style", ";".join(declarations))
                    else:
                        descendant.attrib.pop("style", None)

                if "fill" in descendant.attrib:
                    descendant.set("fill", fill)

        destination.append(copied)


def _svg_boundary_path(element: ET.Element) -> str:
    """
    Convert a registered Shape boundary to a closed SVG path.

    Supports the circle, rectangle, and polygon geometry already
    produced by SHAPE Structure and Compose.

    Compound paths may combine two such boundaries with the
    even-odd fill rule to represent an annular region.
    """
    if element.tag == SVG_CIRCLE:
        cx = float(element.get("cx", "0"))
        cy = float(element.get("cy", "0"))
        radius = float(element.get("r", "0"))

        if radius <= 0.0:
            raise ValueError("Canonical Shape SVG requires positive circle radius.")

        left = cx - radius
        right = cx + radius

        return (
            f"M {left:g} {cy:g} "
            f"A {radius:g} {radius:g} 0 1 0 {right:g} {cy:g} "
            f"A {radius:g} {radius:g} 0 1 0 {left:g} {cy:g} "
            "Z"
        )

    if element.tag == SVG_RECT:
        x = float(element.get("x", "0"))
        y = float(element.get("y", "0"))
        width = float(element.get("width", "0"))
        height = float(element.get("height", "0"))

        if width <= 0.0 or height <= 0.0:
            raise ValueError("Canonical Shape SVG requires positive rectangle dimensions.")

        return (
            f"M {x:g} {y:g} "
            f"L {x + width:g} {y:g} "
            f"L {x + width:g} {y + height:g} "
            f"L {x:g} {y + height:g} "
            "Z"
        )

    if element.tag == SVG_POLYGON:
        points = _read_polygon_points(element)

        first_x, first_y = points[0]

        commands = [f"M {first_x:g} {first_y:g}"]

        commands.extend(f"L {x:g} {y:g}" for x, y in points[1:])

        commands.append("Z")

        return " ".join(commands)

    raise ValueError("Canonical Shape SVG requires a supported registered boundary.")


def _write_composition_manifest(
    path: Path,
    *,
    composition: Path,
    border_labels: dict[str, dict[str, object] | None] | None = None,
    artwork: RegisteredArtwork | None = None,
    artwork_transform: RegisteredArtworkTransform | None = None,
    artwork_fill: RegisteredArtworkFillRegion | None = None,
    qr: RegisteredQR | None = None,
    shape_size: float | None = None,
) -> None:
    """
    Write the persistent registered Shape composition manifest.

    Registered Artwork and QR retain independent component identities.

    When QR participates, its rounded footprint establishes the
    authoritative registered exclusion geometry. Artwork remains
    unmodified in its original registered coordinate system.

    Downstream dimensionalization applies the persisted exclusion
    after Artwork placement, before physical extrusion.
    """
    artwork_manifest: dict[str, Any] | None = None

    if artwork is not None:
        if artwork_transform is None:
            raise ValueError("Registered Artwork requires a composition transform.")

        for component in artwork.components:
            destination = path.parent / component.path.name

            if component.path != destination:
                shutil.copyfile(
                    component.path,
                    destination,
                )

        artwork_manifest = _registered_artwork_manifest(
            artwork,
            transform=artwork_transform,
        )

    if border_labels is None:
        border_labels = {
            "top": None,
            "bottom": None,
        }

    manifest: dict[str, Any] = {
        "composition": composition.name,
        "border_labels": border_labels,
        "artwork": artwork_manifest,
        "artwork_fill": (
            _registered_artwork_fill_manifest(artwork_fill) if artwork_fill is not None else None
        ),
    }

    if qr is not None:
        if shape_size is None:
            raise ValueError("Participating QR requires Shape size.")

        footprint = _registered_qr_footprint(
            qr,
            shape_size=shape_size,
        )

        manifest["qr"] = {
            "footprint": footprint,
            "quiet_zone_modules": qr.quiet_zone_modules,
            "components": {
                name: {"path": component_path.name}
                for name, component_path in qr.components.items()
            },
        }

        if artwork_manifest is not None:
            artwork_manifest["exclusions"] = [
                footprint.copy(),
            ]

    path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _registered_artwork_fill_manifest(
    fill: RegisteredArtworkFillRegion,
) -> dict[str, Any]:
    """
    Serialize registered Artwork-fill geometry.

    The resulting manifest contains the already-composed registered boundaries
    needed by downstream dimensionalization. Producer Artwork geometry does not
    need to be reopened to reconstruct the fill region.
    """

    return {
        "outer_boundary": _registered_element_manifest(
            fill.outer_boundary,
        ),
        "inner_boundary": _registered_element_manifest(
            fill.inner_boundary,
        ),
    }


def _registered_element_manifest(
    element: ET.Element,
) -> dict[str, Any]:
    """
    Serialize supported registered geometry for persistent composition.

    Geometry remains in registered Shape coordinates. No physical dimensions
    or semantic color are introduced by this representation.
    """

    if element.tag == SVG_CIRCLE:
        return {
            "type": "circle",
            "cx": float(
                element.get(
                    "cx",
                    "0.0",
                )
            ),
            "cy": float(
                element.get(
                    "cy",
                    "0.0",
                )
            ),
            "r": float(
                element.get(
                    "r",
                    "0.0",
                )
            ),
        }

    if element.tag == SVG_RECT:
        return {
            "type": "rect",
            "x": float(
                element.get(
                    "x",
                    "0.0",
                )
            ),
            "y": float(
                element.get(
                    "y",
                    "0.0",
                )
            ),
            "width": float(
                element.get(
                    "width",
                    "0.0",
                )
            ),
            "height": float(
                element.get(
                    "height",
                    "0.0",
                )
            ),
        }

    if element.tag == SVG_POLYGON:
        return {
            "type": "polygon",
            "points": [
                {
                    "x": x,
                    "y": y,
                }
                for x, y in _read_polygon_points(
                    element,
                )
            ],
        }

    if element.tag == SVG_PATH:
        return {
            "type": "path",
            "points": [
                {
                    "x": x,
                    "y": y,
                }
                for x, y in _registered_linear_path_points(
                    element,
                )
            ],
        }

    if element.tag == SVG_GROUP:
        return {
            "type": "group",
            "children": [
                _registered_element_manifest(
                    child,
                )
                for child in element
            ],
        }

    raise ValueError(
        "Registered Artwork fill contains unsupported geometry.",
    )


def _registered_artwork_manifest(
    artwork: RegisteredArtwork,
    *,
    transform: RegisteredArtworkTransform,
) -> dict[str, Any]:
    """
    Serialize incorporated registered Artwork for persistent composition.

    The common registered coordinate extent, component membership, Artifact
    color identity, and placement transformation are preserved so downstream
    stages can interpret the registered Artwork without rediscovering source
    geometry or color semantics.

    Physical printer-color assignment is deferred to packaging.
    """

    return {
        "registered_extent": {
            "width": artwork.registered_extent.width,
            "height": artwork.registered_extent.height,
        },
        "transform": {
            "scale": transform.scale,
            "translate_x": transform.translate_x,
            "translate_y": transform.translate_y,
        },
        "components": [
            {
                "index": component.index,
                "path": component.path.name,
                "artifact_color": {
                    "index": component.artifact_color_index,
                    "rgb": component.artifact_color,
                },
            }
            for component in artwork.components
        ],
    }


# =========================================================
# Structural composition
# =========================================================


def _compose_ridge(
    structure_input: Path,
    output: Path,
    *,
    shape_size: float,
    ridge_width: float,
    inner_ridge_width: float = 0.0,
    inner_to_outer_ridge_dist: float = 10.0,
    border_label_width: float = 1.0,
    border_label_max_glyph_height: float = 5.0,
    border_label_arc_degrees: float = 140.0,
    border_label_end_margin: float = 1.0,
    border_label_font_family: str = "DejaVu Sans",
    top_border_label_text: str = "",
    bottom_border_label_text: str = "",
    border_label_output_directory: Path | None = None,
    top_border_label_font_family: str | None = None,
    bottom_border_label_font_family: str | None = None,
    top_border_label_arc_degrees: float | None = None,
    bottom_border_label_arc_degrees: float | None = None,
) -> dict[str, dict[str, object] | None]:
    """
    Compose structural partition boundaries in registered Shape space.

    The complete Shape boundary remains unchanged. Physical widths,
    positioning distances, and Border Label fitting dimensions are converted
    into registered-space geometry.

    Structural features are composed from the Shape perimeter inward:

        Outer Ridge
        Border Labels
        Inner Ridge

    Outer-ridge existence is determined solely by outer-ridge width. Zero
    width preserves the registered Shape boundary without creating an outer
    ridge partition.

    Top and Bottom Border Labels participate independently according to
    whether their text contains non-whitespace content. When either
    participates, the Border Label reference boundary is the inside boundary
    of the Outer Ridge when it participates and the complete Shape boundary
    otherwise.

    Participating Border Labels are also materialized as persistent registered
    path geometry while the fitted typography and semantic baseline geometry
    are available. Downstream stages therefore consume ordinary registered
    geometry without rediscovering typography or fitting policy.

    Inner-ridge existence is determined solely by inner-ridge width. When
    Border Labels participate, their inside boundary establishes the Inner
    Ridge positioning reference. Otherwise, the Outer Ridge inside boundary
    establishes that reference when present, falling back to the complete
    Shape boundary.

    Integrated and separate outer-ridge styles share these registered
    boundaries. Their different physical component partitioning belongs
    downstream.

    Border Label composition currently supports circular registered Shape
    geometry. Existing square and polygon behavior remains unchanged when
    Border Labels do not participate.
    """

    if ridge_width < 0.0:
        raise ValueError("shape_outer_ridge_width must be nonnegative.")

    if inner_ridge_width < 0.0:
        raise ValueError("shape_inner_ridge_width must be nonnegative.")

    if inner_to_outer_ridge_dist < 0.0:
        raise ValueError("shape_inner_to_outer_ridge_dist must be nonnegative.")

    tree = ET.parse(
        structure_input,
    )

    root = tree.getroot()

    circle = root.find(
        SVG_CIRCLE,
    )

    square = root.find(
        SVG_RECT,
    )

    polygon = root.find(
        SVG_POLYGON,
    )

    outer_boundary = circle if circle is not None else square if square is not None else polygon

    if outer_boundary is None:
        raise ValueError("Ridge composition requires supported registered Shape structure.")

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    if ridge_width > 0.0:
        registered_inset = ridge_width / shape_size

        if circle is not None:
            _compose_circle_ridge(
                root,
                circle,
                registered_inset=registered_inset,
            )

        elif square is not None:
            _compose_square_ridge(
                root,
                square,
                registered_inset=registered_inset,
            )

        else:
            assert polygon is not None

            _compose_polygon_ridge(
                root,
                polygon,
                registered_inset=registered_inset,
            )

    top_participates = bool(top_border_label_text.strip())

    bottom_participates = bool(bottom_border_label_text.strip())

    border_labels_participate = top_participates or bottom_participates

    border_labels: dict[
        str,
        dict[str, object] | None,
    ] = {
        "top": None,
        "bottom": None,
    }

    inner_reference_boundary = next(
        (element for element in root if element.get("id") == "ridge-inner-boundary"),
        outer_boundary,
    )

    if border_labels_participate:
        if border_label_output_directory is None:
            raise ValueError("Participating Border Labels require a persistent output directory.")

        border_labels = _compose_circle_border_labels(
            root,
            inner_reference_boundary,
            shape_size=shape_size,
            border_width=border_label_width,
            max_glyph_height=border_label_max_glyph_height,
            arc_degrees=border_label_arc_degrees,
            end_margin=border_label_end_margin,
            font_family=border_label_font_family,
            top_text=(top_border_label_text if top_participates else None),
            bottom_text=(bottom_border_label_text if bottom_participates else None),
            output_directory=border_label_output_directory,
            top_font_family=top_border_label_font_family,
            bottom_font_family=bottom_border_label_font_family,
            top_arc_degrees=top_border_label_arc_degrees,
            bottom_arc_degrees=bottom_border_label_arc_degrees,
        )

        border_label_boundary = next(
            (element for element in root if element.get("id") == "border-label-inner-boundary"),
            None,
        )

        if border_label_boundary is None:
            raise ValueError("Participating Border Labels require a registered inner boundary.")

        inner_reference_boundary = border_label_boundary

    if inner_ridge_width > 0.0:
        registered_width = inner_ridge_width / shape_size

        if border_labels_participate:
            registered_distance = 0.0

        else:
            registered_distance = inner_to_outer_ridge_dist / shape_size

        _compose_inner_ridge(
            root,
            inner_reference_boundary,
            registered_distance=registered_distance,
            registered_width=registered_width,
        )

    #
    # ElementTree namespace registration is process-global. Establish the SVG
    # default namespace at the serialization boundary rather than relying on
    # namespace state established when this module was imported.
    #

    ET.register_namespace(
        "",
        SVG_NAMESPACE,
    )

    tree.write(
        output,
        encoding="unicode",
    )

    return border_labels


def _compose_circle_border_labels(
    root: ET.Element,
    reference_boundary: ET.Element,
    *,
    shape_size: float,
    border_width: float,
    max_glyph_height: float,
    arc_degrees: float,
    end_margin: float,
    font_family: str,
    top_text: str | None,
    bottom_text: str | None,
    output_directory: Path,
    top_font_family: str | None = None,
    bottom_font_family: str | None = None,
    top_arc_degrees: float | None = None,
    bottom_arc_degrees: float | None = None,
) -> dict[str, dict[str, object] | None]:
    """
    Compose independent circular Border Label geometry.

    Fitting determines a shared physical lettering band. Each label uses
    its effective font and arc span for persistent glyph geometry.
    """

    if reference_boundary.tag != SVG_CIRCLE:
        raise ValueError(
            "Border Label composition currently requires circular registered Shape geometry."
        )

    registered_reference_radius = float(reference_boundary.get("r", "0.0"))
    physical_reference_radius = registered_reference_radius * shape_size

    fit = fit_circular_border_labels(
        top_text=top_text,
        bottom_text=bottom_text,
        font_family=font_family,
        reference_radius=physical_reference_radius,
        border_width=border_width,
        max_glyph_height=max_glyph_height,
        arc_degrees=arc_degrees,
        end_margin=end_margin,
        top_font_family=top_font_family,
        bottom_font_family=bottom_font_family,
        top_arc_degrees=top_arc_degrees,
        bottom_arc_degrees=bottom_arc_degrees,
    )

    center_x = float(reference_boundary.get("cx", "0.0"))
    center_y = float(reference_boundary.get("cy", "0.0"))

    bottom_radius = fit.bottom_baseline_radius / shape_size
    top_radius = fit.top_baseline_radius / shape_size
    inner_radius = fit.inner_boundary_radius / shape_size

    for element_id, radius in (
        ("border-label-bottom-baseline", bottom_radius),
        ("border-label-top-baseline", top_radius),
        ("border-label-inner-boundary", inner_radius),
    ):
        ET.SubElement(
            root,
            SVG_CIRCLE,
            {
                "id": element_id,
                "cx": str(center_x),
                "cy": str(center_y),
                "r": str(radius),
            },
        )

    components: dict[str, dict[str, object] | None] = {
        "top": None,
        "bottom": None,
    }

    if fit.top is not None:
        effective_arc = top_arc_degrees if top_arc_degrees is not None else arc_degrees
        effective_font = top_font_family if top_font_family is not None else font_family

        path = top_label_path(
            center_x=center_x,
            center_y=center_y,
            radius=top_radius,
            arc_degrees=effective_arc,
        )

        ET.SubElement(
            root,
            SVG_PATH,
            {
                "id": "top-border-label-path",
                "d": path,
            },
        )

        component_name = "top-border-label.svg"

        write_registered_circular_label_svg(
            output_directory / component_name,
            text=fit.top.text,
            font_family=effective_font,
            font_size=fit.top.font_size,
            metrics=fit.top.metrics,
            rendered_height=fit.top.rendered_height,
            baseline_path=path,
            shape_size=shape_size,
            position="top",
        )

        components["top"] = {"path": component_name}

    if fit.bottom is not None:
        effective_arc = bottom_arc_degrees if bottom_arc_degrees is not None else arc_degrees
        effective_font = bottom_font_family if bottom_font_family is not None else font_family

        path = bottom_label_path(
            center_x=center_x,
            center_y=center_y,
            radius=bottom_radius,
            arc_degrees=effective_arc,
        )

        ET.SubElement(
            root,
            SVG_PATH,
            {
                "id": "bottom-border-label-path",
                "d": path,
            },
        )

        component_name = "bottom-border-label.svg"

        write_registered_circular_label_svg(
            output_directory / component_name,
            text=fit.bottom.text,
            font_family=effective_font,
            font_size=fit.bottom.font_size,
            metrics=fit.bottom.metrics,
            rendered_height=fit.bottom.rendered_height,
            baseline_path=path,
            shape_size=shape_size,
            position="bottom",
        )

        components["bottom"] = {"path": component_name}

    return components


def _compose_inner_ridge(
    root: ET.Element,
    reference_boundary: ET.Element,
    *,
    registered_distance: float,
    registered_width: float,
) -> None:
    """
    Establish registered outer and inner boundaries for the inner ridge.

    The outer boundary is inset from the current positioning reference by the
    configured ridge distance. The inner boundary is inset from that same
    reference by the positioning distance plus the inner-ridge width.

    The positioning reference is the outer ridge's inside boundary when the
    outer ridge participates and the complete Shape boundary otherwise.
    """

    outer_inset = registered_distance
    inner_inset = registered_distance + registered_width

    if reference_boundary.tag == SVG_CIRCLE:
        reference_radius = float(
            reference_boundary.get(
                "r",
                "0.0",
            )
        )

        ET.SubElement(
            root,
            SVG_CIRCLE,
            {
                "id": "inner-ridge-outer-boundary",
                "cx": reference_boundary.get("cx", "0.0"),
                "cy": reference_boundary.get("cy", "0.0"),
                "r": str(reference_radius - outer_inset),
            },
        )

        ET.SubElement(
            root,
            SVG_CIRCLE,
            {
                "id": "inner-ridge-inner-boundary",
                "cx": reference_boundary.get("cx", "0.0"),
                "cy": reference_boundary.get("cy", "0.0"),
                "r": str(reference_radius - inner_inset),
            },
        )

        return

    if reference_boundary.tag == SVG_RECT:
        reference_x = float(
            reference_boundary.get(
                "x",
                "0.0",
            )
        )
        reference_y = float(
            reference_boundary.get(
                "y",
                "0.0",
            )
        )
        reference_width = float(
            reference_boundary.get(
                "width",
                "0.0",
            )
        )
        reference_height = float(
            reference_boundary.get(
                "height",
                "0.0",
            )
        )

        ET.SubElement(
            root,
            SVG_RECT,
            {
                "id": "inner-ridge-outer-boundary",
                "x": str(reference_x + outer_inset),
                "y": str(reference_y + outer_inset),
                "width": str(reference_width - (2.0 * outer_inset)),
                "height": str(reference_height - (2.0 * outer_inset)),
            },
        )

        ET.SubElement(
            root,
            SVG_RECT,
            {
                "id": "inner-ridge-inner-boundary",
                "x": str(reference_x + inner_inset),
                "y": str(reference_y + inner_inset),
                "width": str(reference_width - (2.0 * inner_inset)),
                "height": str(reference_height - (2.0 * inner_inset)),
            },
        )

        return

    if reference_boundary.tag == SVG_POLYGON:
        reference_points = _read_polygon_points(
            reference_boundary,
        )

        outer_points = _inset_polygon(
            reference_points,
            inset=outer_inset,
        )

        inner_points = _inset_polygon(
            reference_points,
            inset=inner_inset,
        )

        ET.SubElement(
            root,
            SVG_POLYGON,
            {
                "id": "inner-ridge-outer-boundary",
                "points": _format_polygon_points(
                    outer_points,
                ),
            },
        )

        ET.SubElement(
            root,
            SVG_POLYGON,
            {
                "id": "inner-ridge-inner-boundary",
                "points": _format_polygon_points(
                    inner_points,
                ),
            },
        )

        return

    raise ValueError("Inner-ridge composition requires supported registered Shape geometry.")


def _compose_circle_ridge(
    root: ET.Element,
    outer_boundary: ET.Element,
    *,
    registered_inset: float,
) -> None:
    """
    Establish registered outer and inner boundaries for a circle ridge.
    """

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    outer_radius = float(
        outer_boundary.get(
            "r",
            "0.0",
        )
    )

    inner_radius = outer_radius - registered_inset

    ET.SubElement(
        root,
        SVG_CIRCLE,
        {
            "id": "ridge-inner-boundary",
            "cx": outer_boundary.get("cx", "0.0"),
            "cy": outer_boundary.get("cy", "0.0"),
            "r": str(inner_radius),
        },
    )


def _compose_square_ridge(
    root: ET.Element,
    outer_boundary: ET.Element,
    *,
    registered_inset: float,
) -> None:
    """
    Establish registered outer and inner boundaries for a square ridge.

    Ridge width is measured inward from every side, so the inner square loses
    twice the registered inset from both its width and height.
    """

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    outer_x = float(
        outer_boundary.get(
            "x",
            "0.0",
        )
    )
    outer_y = float(
        outer_boundary.get(
            "y",
            "0.0",
        )
    )
    outer_width = float(
        outer_boundary.get(
            "width",
            "0.0",
        )
    )
    outer_height = float(
        outer_boundary.get(
            "height",
            "0.0",
        )
    )

    ET.SubElement(
        root,
        SVG_RECT,
        {
            "id": "ridge-inner-boundary",
            "x": str(outer_x + registered_inset),
            "y": str(outer_y + registered_inset),
            "width": str(outer_width - (2.0 * registered_inset)),
            "height": str(outer_height - (2.0 * registered_inset)),
        },
    )


def _compose_polygon_ridge(
    root: ET.Element,
    outer_boundary: ET.Element,
    *,
    registered_inset: float,
) -> None:
    """
    Establish registered outer and inner boundaries for a polygon ridge.

    Each outer edge is translated inward by registered_inset along its
    perpendicular normal. Adjacent translated edge lines are intersected to
    establish the vertices of the inner polygon.

    This preserves parallel corresponding edges and gives ridge width its
    perpendicular edge-distance semantics rather than treating the ridge as
    a radial scale of the outer polygon.
    """

    outer_points = _read_polygon_points(
        outer_boundary,
    )

    inner_points = _inset_polygon(
        outer_points,
        inset=registered_inset,
    )

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    ET.SubElement(
        root,
        SVG_POLYGON,
        {
            "id": "ridge-inner-boundary",
            "points": _format_polygon_points(
                inner_points,
            ),
        },
    )


# =========================================================
# Polygon composition helpers
# =========================================================


def _read_polygon_points(
    polygon: ET.Element,
) -> tuple[tuple[float, float], ...]:
    """
    Read registered vertices from an SVG polygon element.
    """

    points = polygon.get(
        "points",
    )

    if points is None:
        raise ValueError("Registered polygon structure requires polygon points.")

    vertices = tuple(
        _parse_polygon_point(
            point,
        )
        for point in points.split()
    )

    if len(vertices) < 3:
        raise ValueError("Registered polygon structure requires at least 3 vertices.")

    return vertices


def _parse_polygon_point(
    point: str,
) -> tuple[float, float]:
    """
    Parse one SVG polygon point.
    """

    coordinates = point.split(
        ",",
    )

    if len(coordinates) != 2:
        raise ValueError("Registered polygon structure contains an invalid polygon point.")

    return (
        float(coordinates[0]),
        float(coordinates[1]),
    )


def _format_polygon_points(
    points: tuple[tuple[float, float], ...],
) -> str:
    """
    Format registered polygon vertices for SVG persistence.
    """

    return " ".join(f"{x},{y}" for x, y in points)


def _inset_polygon(
    points: tuple[tuple[float, float], ...],
    *,
    inset: float,
) -> tuple[tuple[float, float], ...]:
    """
    Construct an inward edge-offset polygon.

    Each edge is represented by an inward-translated parallel line. The
    intersection of each edge with its following edge produces one vertex of
    the inset polygon.
    """

    orientation = _polygon_orientation(
        points,
    )

    offset_lines = tuple(
        _offset_edge_line(
            points[index],
            points[(index + 1) % len(points)],
            inset=inset,
            orientation=orientation,
        )
        for index in range(len(points))
    )

    return tuple(
        _intersect_lines(
            offset_lines[(index - 1) % len(offset_lines)],
            offset_lines[index],
        )
        for index in range(len(offset_lines))
    )


def _polygon_orientation(
    points: tuple[tuple[float, float], ...],
) -> float:
    """
    Return the signed orientation of a polygon.

    Positive values indicate counterclockwise vertex order and negative
    values indicate clockwise vertex order.
    """

    signed_area_twice = sum(
        (start[0] * end[1] - end[0] * start[1])
        for start, end in (
            (
                points[index],
                points[(index + 1) % len(points)],
            )
            for index in range(len(points))
        )
    )

    if math.isclose(
        signed_area_twice,
        0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("Registered polygon structure has zero area.")

    return signed_area_twice


def _offset_edge_line(
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    inset: float,
    orientation: float,
) -> tuple[
    tuple[float, float],
    tuple[float, float],
]:
    """
    Translate one polygon edge inward by a perpendicular registered distance.

    The polygon orientation determines which perpendicular normal points
    toward the polygon interior.
    """

    dx = end[0] - start[0]
    dy = end[1] - start[1]

    length = math.hypot(
        dx,
        dy,
    )

    if math.isclose(
        length,
        0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("Registered polygon structure contains a zero-length edge.")

    if orientation > 0.0:
        normal_x = -dy / length
        normal_y = dx / length
    else:
        normal_x = dy / length
        normal_y = -dx / length

    offset_x = normal_x * inset
    offset_y = normal_y * inset

    return (
        (
            start[0] + offset_x,
            start[1] + offset_y,
        ),
        (
            end[0] + offset_x,
            end[1] + offset_y,
        ),
    )


def _intersect_lines(
    first: tuple[
        tuple[float, float],
        tuple[float, float],
    ],
    second: tuple[
        tuple[float, float],
        tuple[float, float],
    ],
) -> tuple[float, float]:
    """
    Return the intersection of two infinite lines.

    Adjacent edges of a valid regular polygon are nonparallel, so their inward
    offset lines must have one unique intersection.
    """

    first_start, first_end = first
    second_start, second_end = second

    first_dx = first_end[0] - first_start[0]
    first_dy = first_end[1] - first_start[1]

    second_dx = second_end[0] - second_start[0]
    second_dy = second_end[1] - second_start[1]

    denominator = first_dx * second_dy - first_dy * second_dx

    if math.isclose(
        denominator,
        0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("Registered polygon structure contains parallel adjacent edges.")

    delta_x = second_start[0] - first_start[0]
    delta_y = second_start[1] - first_start[1]

    first_parameter = (delta_x * second_dy - delta_y * second_dx) / denominator

    return (
        first_start[0] + first_parameter * first_dx,
        first_start[1] + first_parameter * first_dy,
    )


def registered_artwork_fill(
    interior: ET.Element,
    artwork: RegisteredArtwork,
    *,
    transform: RegisteredArtworkTransform,
    fill_color: str,
) -> RegisteredArtworkFillRegion | None:
    """
    Resolve optional registered Artwork-fill geometry.

    The Shape fill policy determines only whether fill geometry exists.
    Enabled fill colors do not participate in registered geometry; the fill
    region is always the Shape interior minus the transformed authoritative
    Artwork envelope.
    """

    if fill_color == "none":
        return None

    return registered_artwork_fill_region(
        interior,
        artwork,
        transform=transform,
    )


def registered_artwork_fill_region(
    interior: ET.Element,
    artwork: RegisteredArtwork,
    *,
    transform: RegisteredArtworkTransform,
) -> RegisteredArtworkFillRegion:
    """
    Return the registered Shape region available for Artwork fill.

    The registered Shape interior defines the outer boundary. The
    authoritative Artwork envelope defines the occupied inner boundary and
    is transformed using the same common placement transform as incorporated
    Artwork.

    Individual Artwork component geometry is not inspected. No physical
    dimensions are introduced at this boundary.
    """

    root = ET.parse(
        artwork.envelope,
    ).getroot()

    envelope = next(
        iter(root),
        None,
    )

    if envelope is None:
        raise ValueError("Registered Artwork envelope requires geometry.")

    inner_boundary = _transform_registered_element(
        envelope,
        transform=transform,
    )

    return RegisteredArtworkFillRegion(
        outer_boundary=interior,
        inner_boundary=inner_boundary,
    )


def _transform_registered_element(
    element: ET.Element,
    *,
    transform: RegisteredArtworkTransform,
) -> ET.Element:
    """
    Transform supported registered geometry into registered Shape space.

    The common Artwork placement transform uniformly scales source registered
    coordinates and then translates them into the Shape registered coordinate
    system.

    Producer-published group translations are composed into that common
    transform before recursively transforming group children.
    """

    if element.tag == SVG_RECT:
        x = float(
            element.get(
                "x",
                "0.0",
            )
        )
        y = float(
            element.get(
                "y",
                "0.0",
            )
        )
        width = float(
            element.get(
                "width",
                "0.0",
            )
        )
        height = float(
            element.get(
                "height",
                "0.0",
            )
        )

        return ET.Element(
            SVG_RECT,
            {
                "x": str(
                    x * transform.scale + transform.translate_x,
                ),
                "y": str(
                    y * transform.scale + transform.translate_y,
                ),
                "width": str(
                    width * transform.scale,
                ),
                "height": str(
                    height * transform.scale,
                ),
            },
        )

    if element.tag == SVG_CIRCLE:
        center_x = float(
            element.get(
                "cx",
                "0.0",
            )
        )
        center_y = float(
            element.get(
                "cy",
                "0.0",
            )
        )
        radius = float(
            element.get(
                "r",
                "0.0",
            )
        )

        return ET.Element(
            SVG_CIRCLE,
            {
                "cx": str(
                    center_x * transform.scale + transform.translate_x,
                ),
                "cy": str(
                    center_y * transform.scale + transform.translate_y,
                ),
                "r": str(
                    radius * transform.scale,
                ),
            },
        )

    if element.tag == SVG_POLYGON:
        points = _read_polygon_points(
            element,
        )

        transformed_points = tuple(
            (
                x * transform.scale + transform.translate_x,
                y * transform.scale + transform.translate_y,
            )
            for x, y in points
        )

        return ET.Element(
            SVG_POLYGON,
            {
                "points": _format_polygon_points(
                    transformed_points,
                ),
            },
        )

    if element.tag == SVG_PATH:
        points = _registered_linear_path_points(
            element,
        )

        transformed_points = tuple(
            (
                x * transform.scale + transform.translate_x,
                y * transform.scale + transform.translate_y,
            )
            for x, y in points
        )

        return ET.Element(
            SVG_PATH,
            {
                "d": _format_registered_linear_path(
                    transformed_points,
                ),
            },
        )

    if element.tag == SVG_GROUP:
        group_translate_x, group_translate_y = _registered_translation(
            element.get(
                "transform",
            ),
        )

        child_transform = RegisteredArtworkTransform(
            scale=transform.scale,
            width=transform.width,
            height=transform.height,
            translate_x=(transform.translate_x + group_translate_x * transform.scale),
            translate_y=(transform.translate_y + group_translate_y * transform.scale),
        )

        transformed_group = ET.Element(
            SVG_GROUP,
        )

        for child in element:
            transformed_group.append(
                _transform_registered_element(
                    child,
                    transform=child_transform,
                )
            )

        return transformed_group

    raise ValueError("Registered Artwork envelope contains unsupported geometry.")


def _format_registered_linear_path(
    points: tuple[tuple[float, float], ...],
) -> str:
    """
    Format registered vertices as a closed absolute linear SVG path.

    Registered Artwork envelopes use absolute move and line commands with
    optional path closure. Artwork-fill transformation preserves that supported
    geometric representation after applying the common placement transform.
    """

    if not points:
        raise ValueError("Registered Artwork envelope path requires geometry.")

    first_x, first_y = points[0]

    commands = [
        f"M {first_x} {first_y}",
    ]

    commands.extend(f"L {x} {y}" for x, y in points[1:])

    commands.append(
        "Z",
    )

    return " ".join(
        commands,
    )


# =========================================================
# Registered Artwork placement
# =========================================================


def registered_artwork_envelope_bounds(
    artwork: RegisteredArtwork,
) -> RegisteredBounds:
    """
    Return the occupied bounds declared by the registered Artwork envelope.

    The Artwork envelope is interpreted in the common registered coordinate
    system. Component geometry is not inspected independently.
    """

    root = ET.parse(
        artwork.envelope,
    ).getroot()

    envelope = next(
        iter(root),
        None,
    )

    if envelope is None:
        raise ValueError("Registered Artwork envelope requires geometry.")

    return _registered_element_bounds(
        envelope,
    )


def registered_artwork_envelope_radius(
    artwork: RegisteredArtwork,
) -> float:
    """
    Return the radial extent of the authoritative Artwork envelope.

    The envelope is measured from the center of its occupied bounds. Actual
    envelope geometry determines the maximum occupied radius; the corners of
    the envelope's rectangular bounds are not assumed to contain geometry.
    """

    root = ET.parse(
        artwork.envelope,
    ).getroot()

    envelope = next(
        iter(root),
        None,
    )

    if envelope is None:
        raise ValueError("Registered Artwork envelope requires geometry.")

    bounds = _registered_element_bounds(
        envelope,
    )

    center_x = bounds.x + (bounds.width / 2.0)
    center_y = bounds.y + (bounds.height / 2.0)

    return _registered_element_radius(
        envelope,
        center_x=center_x,
        center_y=center_y,
    )


def _registered_element_radius(
    element: ET.Element,
    *,
    center_x: float,
    center_y: float,
) -> float:
    """
    Return the maximum occupied distance from a registered point.

    Supported registered envelope geometry is measured directly rather than
    through its rectangular bounds.
    """

    if element.tag == SVG_CIRCLE:
        element_center_x = float(
            element.get(
                "cx",
                "0.0",
            )
        )
        element_center_y = float(
            element.get(
                "cy",
                "0.0",
            )
        )
        radius = float(
            element.get(
                "r",
                "0.0",
            )
        )

        return (
            math.hypot(
                element_center_x - center_x,
                element_center_y - center_y,
            )
            + radius
        )

    if element.tag == SVG_RECT:
        x = float(
            element.get(
                "x",
                "0.0",
            )
        )
        y = float(
            element.get(
                "y",
                "0.0",
            )
        )
        width = float(
            element.get(
                "width",
                "0.0",
            )
        )
        height = float(
            element.get(
                "height",
                "0.0",
            )
        )

        corners = (
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        )

        return max(
            math.hypot(
                x_coordinate - center_x,
                y_coordinate - center_y,
            )
            for x_coordinate, y_coordinate in corners
        )

    if element.tag == SVG_POLYGON:
        points = _read_polygon_points(
            element,
        )

        return max(
            math.hypot(
                x_coordinate - center_x,
                y_coordinate - center_y,
            )
            for x_coordinate, y_coordinate in points
        )

    if element.tag == SVG_PATH:
        points = _registered_linear_path_points(
            element,
        )

        return max(
            math.hypot(
                x_coordinate - center_x,
                y_coordinate - center_y,
            )
            for x_coordinate, y_coordinate in points
        )

    if element.tag == SVG_GROUP:
        translate_x, translate_y = _registered_translation(
            element.get(
                "transform",
            ),
        )

        return max(
            _registered_element_radius(
                child,
                center_x=center_x - translate_x,
                center_y=center_y - translate_y,
            )
            for child in element
        )

    raise ValueError("Registered Artwork envelope contains unsupported geometry.")


def _registered_element_bounds(
    element: ET.Element,
) -> RegisteredBounds:
    """
    Return registered bounds for supported envelope geometry.

    Primitive registered geometry is interpreted directly. SVG groups
    recursively combine the occupied bounds of their children and apply
    supported registration transforms to the combined bounds.
    """

    if element.tag == SVG_RECT:
        return RegisteredBounds(
            x=float(element.get("x", "0.0")),
            y=float(element.get("y", "0.0")),
            width=float(element.get("width", "0.0")),
            height=float(element.get("height", "0.0")),
        )

    if element.tag == SVG_CIRCLE:
        center_x = float(
            element.get(
                "cx",
                "0.0",
            )
        )
        center_y = float(
            element.get(
                "cy",
                "0.0",
            )
        )
        radius = float(
            element.get(
                "r",
                "0.0",
            )
        )

        return RegisteredBounds(
            x=center_x - radius,
            y=center_y - radius,
            width=2.0 * radius,
            height=2.0 * radius,
        )

    if element.tag == SVG_POLYGON:
        points = _read_polygon_points(
            element,
        )

        x_coordinates = tuple(point[0] for point in points)
        y_coordinates = tuple(point[1] for point in points)

        minimum_x = min(
            x_coordinates,
        )
        maximum_x = max(
            x_coordinates,
        )
        minimum_y = min(
            y_coordinates,
        )
        maximum_y = max(
            y_coordinates,
        )

        return RegisteredBounds(
            x=minimum_x,
            y=minimum_y,
            width=maximum_x - minimum_x,
            height=maximum_y - minimum_y,
        )

    if element.tag == SVG_PATH:
        return _registered_linear_path_bounds(
            element,
        )

    if element.tag == SVG_GROUP:
        child_bounds = tuple(
            _registered_element_bounds(
                child,
            )
            for child in element
        )

        if not child_bounds:
            raise ValueError("Registered Artwork envelope group requires geometry.")

        minimum_x = min(bounds.x for bounds in child_bounds)
        minimum_y = min(bounds.y for bounds in child_bounds)
        maximum_x = max(bounds.x + bounds.width for bounds in child_bounds)
        maximum_y = max(bounds.y + bounds.height for bounds in child_bounds)

        bounds = RegisteredBounds(
            x=minimum_x,
            y=minimum_y,
            width=maximum_x - minimum_x,
            height=maximum_y - minimum_y,
        )

        return _apply_registered_element_transform(
            bounds,
            transform=element.get(
                "transform",
            ),
        )

    raise ValueError("Registered Artwork envelope contains unsupported geometry.")


def _registered_linear_path_points(
    path: ET.Element,
) -> tuple[tuple[float, float], ...]:
    """
    Return vertices from a registered linear SVG path.

    Registered Artwork envelopes produced by Artwork use absolute move and
    line commands with optional path closure.
    """

    data = path.get(
        "d",
    )

    if data is None:
        raise ValueError("Registered Artwork envelope path requires path data.")

    tokens = data.replace(
        ",",
        " ",
    ).split()

    points: list[tuple[float, float]] = []

    index = 0

    while index < len(tokens):
        command = tokens[index]
        index += 1

        if command == "Z":
            continue

        if command not in {
            "M",
            "L",
        }:
            raise ValueError("Registered Artwork envelope path contains an unsupported command.")

        if index + 1 >= len(tokens):
            raise ValueError("Registered Artwork envelope path contains incomplete coordinates.")

        points.append(
            (
                float(tokens[index]),
                float(tokens[index + 1]),
            )
        )

        index += 2

    if not points:
        raise ValueError("Registered Artwork envelope path requires geometry.")

    return tuple(
        points,
    )


def _registered_linear_path_bounds(
    path: ET.Element,
) -> RegisteredBounds:
    """
    Return occupied bounds for a registered linear SVG path.
    """

    points = _registered_linear_path_points(
        path,
    )

    minimum_x = min(point[0] for point in points)
    maximum_x = max(point[0] for point in points)
    minimum_y = min(point[1] for point in points)
    maximum_y = max(point[1] for point in points)

    return RegisteredBounds(
        x=minimum_x,
        y=minimum_y,
        width=maximum_x - minimum_x,
        height=maximum_y - minimum_y,
    )


def _registered_translation(
    transform: str | None,
) -> tuple[float, float]:
    """
    Return the translation declared by a supported SVG transform.
    """

    if transform is None:
        return (
            0.0,
            0.0,
        )

    transform = transform.strip()

    if not transform.startswith(
        "translate(",
    ) or not transform.endswith(
        ")",
    ):
        raise ValueError("Registered Artwork envelope contains an unsupported transform.")

    arguments = (
        transform[len("translate(") : -1]
        .replace(
            ",",
            " ",
        )
        .split()
    )

    if len(arguments) == 1:
        return (
            float(arguments[0]),
            0.0,
        )

    if len(arguments) == 2:
        return (
            float(arguments[0]),
            float(arguments[1]),
        )

    raise ValueError("Registered Artwork envelope contains an invalid translation.")


def _apply_registered_element_transform(
    bounds: RegisteredBounds,
    *,
    transform: str | None,
) -> RegisteredBounds:
    """
    Apply a supported SVG registration transform to occupied bounds.
    """

    translate_x, translate_y = _registered_translation(
        transform,
    )

    return RegisteredBounds(
        x=bounds.x + translate_x,
        y=bounds.y + translate_y,
        width=bounds.width,
        height=bounds.height,
    )


def fit_registered_artwork(
    artwork: RegisteredArtwork,
    *,
    available_width: float,
    available_height: float,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork uniformly within an available region.

    The Artwork envelope defines occupied geometry while registered_extent
    defines the common coordinate system. One uniform transformation fits
    and centers the occupied envelope within the available region.

    Individual component payloads are not inspected or independently fitted.
    """

    bounds = registered_artwork_envelope_bounds(
        artwork,
    )

    scale = min(
        available_width / bounds.width,
        available_height / bounds.height,
    )

    width = bounds.width * scale
    height = bounds.height * scale

    target_x = (available_width - width) / 2.0
    target_y = (available_height - height) / 2.0

    translate_x = target_x - (bounds.x * scale)
    translate_y = target_y - (bounds.y * scale)

    return RegisteredArtworkTransform(
        scale=scale,
        width=width,
        height=height,
        translate_x=translate_x,
        translate_y=translate_y,
    )


def _fit_registered_artwork_to_rect(
    artwork: RegisteredArtwork,
    *,
    interior: ET.Element,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork within a rectangular Shape interior.
    """

    interior_x = float(
        interior.get(
            "x",
            "0.0",
        )
    )
    interior_y = float(
        interior.get(
            "y",
            "0.0",
        )
    )
    interior_width = float(
        interior.get(
            "width",
            "0.0",
        )
    )
    interior_height = float(
        interior.get(
            "height",
            "0.0",
        )
    )

    transform = fit_registered_artwork(
        artwork,
        available_width=interior_width,
        available_height=interior_height,
    )

    return RegisteredArtworkTransform(
        scale=transform.scale,
        width=transform.width,
        height=transform.height,
        translate_x=transform.translate_x + interior_x,
        translate_y=transform.translate_y + interior_y,
    )


def _fit_registered_artwork_to_circle(
    artwork: RegisteredArtwork,
    *,
    interior: ET.Element,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork within a circular placement region.

    The authoritative Artwork envelope is uniformly scaled to the largest
    size whose occupied geometry remains within the placement circle, then
    centered while preserving the Artwork's common registered coordinate
    system.
    """

    bounds = registered_artwork_envelope_bounds(
        artwork,
    )

    center_x = float(
        interior.get(
            "cx",
            "0.0",
        )
    )
    center_y = float(
        interior.get(
            "cy",
            "0.0",
        )
    )
    radius = float(
        interior.get(
            "r",
            "0.0",
        )
    )

    envelope_radius = registered_artwork_envelope_radius(
        artwork,
    )

    if envelope_radius <= 0.0:
        raise ValueError("Registered Artwork envelope requires positive radial extent.")

    scale = radius / envelope_radius

    width = bounds.width * scale
    height = bounds.height * scale

    source_center_x = bounds.x + (bounds.width / 2.0)
    source_center_y = bounds.y + (bounds.height / 2.0)

    return RegisteredArtworkTransform(
        scale=scale,
        width=width,
        height=height,
        translate_x=center_x - (source_center_x * scale),
        translate_y=center_y - (source_center_y * scale),
    )


def _fit_registered_artwork_to_polygon(
    artwork: RegisteredArtwork,
    *,
    interior: ET.Element,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork within a convex polygon Shape interior.

    The occupied Artwork envelope is centered on the registered Shape origin
    and uniformly scaled until one of its corners reaches a polygon edge.

    Registered Shape geometry is centered at (0, 0). Polygon vertex or
    bounding-box asymmetry therefore does not shift incorporated Artwork away
    from the Shape origin.
    """

    bounds = registered_artwork_envelope_bounds(
        artwork,
    )

    polygon = _read_polygon_points(
        interior,
    )

    target_center_x = 0.0
    target_center_y = 0.0

    half_width = bounds.width / 2.0
    half_height = bounds.height / 2.0

    corners = (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    )

    orientation = _polygon_orientation(
        polygon,
    )

    scale = math.inf

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]

        edge_x = end[0] - start[0]
        edge_y = end[1] - start[1]

        if orientation > 0.0:
            normal_x = -edge_y
            normal_y = edge_x
        else:
            normal_x = edge_y
            normal_y = -edge_x

        center_distance = normal_x * (target_center_x - start[0]) + normal_y * (
            target_center_y - start[1]
        )

        corner_distance = max(-(normal_x * corner[0] + normal_y * corner[1]) for corner in corners)

        if corner_distance <= 0.0:
            continue

        scale = min(
            scale,
            center_distance / corner_distance,
        )

    if not math.isfinite(
        scale,
    ):
        raise ValueError("Registered Artwork cannot be fitted within polygon Shape interior.")

    width = bounds.width * scale
    height = bounds.height * scale

    source_center_x = bounds.x + (bounds.width / 2.0)
    source_center_y = bounds.y + (bounds.height / 2.0)

    return RegisteredArtworkTransform(
        scale=scale,
        width=width,
        height=height,
        translate_x=target_center_x - (source_center_x * scale),
        translate_y=target_center_y - (source_center_y * scale),
    )


def fit_registered_artwork_to_shape(
    artwork: RegisteredArtwork,
    *,
    composition: Path,
    shape_size: float = 100.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    scale: float = 1.0,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork and apply optional placement adjustments.

    Automatic fitting establishes the baseline placement within the
    origin-centered Shape placement circle.

    Uniform scaling is applied about the fitted Artwork center, followed
    by physical X/Y offsets. Positive Y moves upward.

    The final common transform is validated against the placement circle.
    """
    if not math.isfinite(shape_size) or shape_size <= 0.0:
        raise ValueError("Artwork placement requires positive finite Shape size.")

    if not math.isfinite(offset_x) or not math.isfinite(offset_y):
        raise ValueError("Artwork placement offsets must be finite.")

    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("Artwork placement scale must be positive and finite.")

    interior = registered_interior_region(composition)
    placement = artwork_placement_circle(interior)

    if not math.isfinite(placement.radius) or placement.radius <= 0.0:
        raise ValueError("Artwork placement requires a positive interior radius.")

    placement_element = ET.Element(
        SVG_CIRCLE,
        {
            "cx": str(placement.center_x),
            "cy": str(placement.center_y),
            "r": str(placement.radius),
        },
    )

    fitted = _fit_registered_artwork_to_circle(
        artwork,
        interior=placement_element,
    )

    bounds = registered_artwork_envelope_bounds(artwork)

    source_center_x = bounds.x + bounds.width / 2.0
    source_center_y = bounds.y + bounds.height / 2.0

    fitted_center_x = source_center_x * fitted.scale + fitted.translate_x
    fitted_center_y = source_center_y * fitted.scale + fitted.translate_y

    adjusted_scale = fitted.scale * scale

    adjusted_center_x = fitted_center_x + offset_x / shape_size
    adjusted_center_y = fitted_center_y - offset_y / shape_size

    adjusted = RegisteredArtworkTransform(
        scale=adjusted_scale,
        width=bounds.width * adjusted_scale,
        height=bounds.height * adjusted_scale,
        translate_x=adjusted_center_x - source_center_x * adjusted_scale,
        translate_y=adjusted_center_y - source_center_y * adjusted_scale,
    )

    _validate_registered_artwork_placement(
        artwork,
        transform=adjusted,
        placement=placement,
    )

    return adjusted


def place_registered_artwork(
    artwork: RegisteredArtwork,
    *,
    available_width: float,
    available_height: float,
) -> PlacedRegisteredArtwork:
    """
    Place every registered Artwork component using one common transform.

    The common transform is calculated once from the registered collection
    extent and associated unchanged with every component. This preserves the
    registration established by the Artwork producer.
    """

    transform = fit_registered_artwork(
        artwork,
        available_width=available_width,
        available_height=available_height,
    )

    components = tuple(
        PlacedRegisteredArtworkComponent(
            component=component,
            transform=transform,
        )
        for component in artwork.components
    )

    return PlacedRegisteredArtwork(
        transform=transform,
        components=components,
    )


# =========================================================
# Manifest loading
# =========================================================


def load_registered_artwork(
    manifest_path: Path,
) -> RegisteredArtwork:
    """
    Load registered Artwork from its declared vector manifest.

    The envelope and component membership are determined exclusively by the
    manifest. Their paths are resolved relative to the manifest location.

    This boundary does not inspect registered geometry or independently
    calculate component bounds.
    """

    manifest = _load_manifest(
        manifest_path,
    )

    registered_extent = _load_registered_extent(
        manifest,
    )

    envelope = _load_envelope(
        manifest,
        manifest_path=manifest_path,
    )

    components = _load_components(
        manifest,
        manifest_path=manifest_path,
    )

    return RegisteredArtwork(
        registered_extent=registered_extent,
        envelope=envelope,
        components=components,
    )


def _load_manifest(
    manifest_path: Path,
) -> dict[str, Any]:
    """
    Load the vector manifest document.
    """

    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as stream:
        manifest = json.load(
            stream,
        )

    if not isinstance(
        manifest,
        dict,
    ):
        raise ValueError("Registered Artwork manifest must contain an object.")

    return manifest


def _load_registered_extent(
    manifest: dict[str, Any],
) -> RegisteredExtent:
    """
    Read the common registered extent declared by the Artwork manifest.

    Artwork publishes one scalar extent describing its square common
    registered coordinate system.
    """

    extent = manifest["registered_extent"]

    if not isinstance(
        extent,
        int | float,
    ):
        raise ValueError("Registered Artwork extent must be numeric.")

    registered_extent = float(
        extent,
    )

    return RegisteredExtent(
        width=registered_extent,
        height=registered_extent,
    )


def _load_envelope(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
) -> Path:
    """
    Read the registered Artwork envelope declared by the manifest.

    The envelope path is resolved relative to the manifest location.
    """

    relative_path = manifest.get(
        "envelope",
    )

    if not isinstance(
        relative_path,
        str,
    ):
        raise ValueError("Registered Artwork manifest requires an envelope.")

    return manifest_path.parent / relative_path


def _load_components(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
) -> tuple[RegisteredArtworkComponent, ...]:
    """
    Read registered components declared by the manifest.
    """

    products = manifest["products"]

    if not isinstance(
        products,
        list,
    ):
        raise ValueError("Registered Artwork products must contain a list.")

    return tuple(
        _load_component(
            product,
            manifest_path=manifest_path,
        )
        for product in products
    )


def _load_component(
    product: Any,
    *,
    manifest_path: Path,
) -> RegisteredArtworkComponent:
    """
    Read one registered Artwork component declaration.

    Shape composition consumes registered geometry and Artifact-color identity.
    Physical printer-color assignment is not part of the persistent Artwork
    vector contract.
    """

    if not isinstance(
        product,
        dict,
    ):
        raise ValueError("Registered Artwork product must contain an object.")

    index = product.get(
        "index",
    )
    relative_path = product.get(
        "path",
    )
    artifact_color = product.get(
        "artifact_color",
    )

    if (
        not isinstance(
            index,
            int,
        )
        or isinstance(
            index,
            bool,
        )
        or index <= 0
    ):
        raise ValueError("Registered Artwork product index must be a positive integer.")

    if not isinstance(
        relative_path,
        str,
    ):
        raise ValueError("Registered Artwork product path must be a string.")

    if not isinstance(
        artifact_color,
        dict,
    ):
        raise ValueError(f"Registered Artwork product {index} requires Artifact color metadata.")

    artifact_color_index = artifact_color.get(
        "index",
    )
    artifact_rgb = artifact_color.get(
        "rgb",
    )

    if (
        not isinstance(
            artifact_color_index,
            int,
        )
        or isinstance(
            artifact_color_index,
            bool,
        )
        or artifact_color_index <= 0
    ):
        raise ValueError(
            f"Registered Artwork product {index} requires a positive Artifact color index."
        )

    if not isinstance(
        artifact_rgb,
        dict,
    ):
        raise ValueError(f"Registered Artwork product {index} requires Artifact RGB metadata.")

    artifact_red = artifact_rgb.get(
        "red",
    )
    artifact_green = artifact_rgb.get(
        "green",
    )
    artifact_blue = artifact_rgb.get(
        "blue",
    )

    if (
        not isinstance(
            artifact_red,
            int,
        )
        or isinstance(
            artifact_red,
            bool,
        )
        or not 0 <= artifact_red <= 255
        or not isinstance(
            artifact_green,
            int,
        )
        or isinstance(
            artifact_green,
            bool,
        )
        or not 0 <= artifact_green <= 255
        or not isinstance(
            artifact_blue,
            int,
        )
        or isinstance(
            artifact_blue,
            bool,
        )
        or not 0 <= artifact_blue <= 255
    ):
        raise ValueError(
            f"Registered Artwork product {index} requires valid Artifact RGB metadata."
        )

    return RegisteredArtworkComponent(
        index=index,
        path=manifest_path.parent / relative_path,
        artifact_color_index=artifact_color_index,
        artifact_color={
            "red": artifact_red,
            "green": artifact_green,
            "blue": artifact_blue,
        },
    )


def artwork_placement_circle(
    interior: ET.Element,
) -> ArtworkPlacementCircle:
    """
    Return the largest origin-centered circle contained by a Shape interior.

    Circle, rectangle, and regular-polygon interiors use the same semantic
    operation. The registered Shape origin is the fixed center of the
    placement circle; the interior boundary determines only its maximum
    radius.
    """

    if interior.tag == SVG_CIRCLE:
        center_x = float(
            interior.get(
                "cx",
                "0.0",
            )
        )
        center_y = float(
            interior.get(
                "cy",
                "0.0",
            )
        )
        radius = float(
            interior.get(
                "r",
                "0.0",
            )
        )

        center_distance = math.hypot(
            center_x,
            center_y,
        )

        return ArtworkPlacementCircle(
            center_x=0.0,
            center_y=0.0,
            radius=radius - center_distance,
        )

    if interior.tag == SVG_RECT:
        x = float(
            interior.get(
                "x",
                "0.0",
            )
        )
        y = float(
            interior.get(
                "y",
                "0.0",
            )
        )
        width = float(
            interior.get(
                "width",
                "0.0",
            )
        )
        height = float(
            interior.get(
                "height",
                "0.0",
            )
        )

        radius = min(
            -x,
            x + width,
            -y,
            y + height,
        )

        return ArtworkPlacementCircle(
            center_x=0.0,
            center_y=0.0,
            radius=radius,
        )

    if interior.tag == SVG_POLYGON:
        points = _read_polygon_points(
            interior,
        )

        radius = min(
            abs(start[0] * end[1] - start[1] * end[0])
            / math.hypot(
                end[0] - start[0],
                end[1] - start[1],
            )
            for start, end in zip(
                points,
                points[1:] + points[:1],
                strict=True,
            )
        )

        return ArtworkPlacementCircle(
            center_x=0.0,
            center_y=0.0,
            radius=radius,
        )

    raise ValueError("Artwork placement requires a supported registered Shape interior.")
