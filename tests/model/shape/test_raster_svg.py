"""Phase 4: raster-preserving SHAPE SVG composition tests."""

from __future__ import annotations

import base64
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape import MODEL
from lowkey_artifact_builder.model.models.shape.stages import compose
from tests.support.model_parameters import model_test_resolver

SVG = "http://www.w3.org/2000/svg"


def _raster_source(directory: Path) -> tuple[Path, Path]:
    """Provide a registered raster Product and its producer metadata."""
    directory.mkdir(parents=True, exist_ok=True)

    png = directory / "artifact.png"
    metadata = directory / "metadata.json"

    image = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    image.putpixel((0, 0), (20, 80, 210, 255))
    image.putpixel((31, 15), (220, 40, 90, 128))
    image.save(png, format="PNG")
    image.close()

    metadata.write_text(
        json.dumps(
            {
                "representation": "raster",
                "processing": "none",
                "format": "png",
                "width": 32,
                "height": 16,
                "mode": "RGBA",
                "source_name": "artifact.png",
            }
        ),
        encoding="utf-8",
    )
    return png, metadata


def _compose_raster(directory: Path) -> tuple[Path, Path]:
    """Execute the declared SHAPE Compose boundary without vector input."""
    directory.mkdir(parents=True, exist_ok=True)
    png, metadata = _raster_source(directory / "source")

    structure = directory / "structure.svg"
    structure.write_text(
        f'<svg xmlns="{SVG}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
        "</svg>",
        encoding="utf-8",
    )

    outputs = {
        "composition": directory / "composition.svg",
        "manifest": directory / "products.json",
        "artifact": directory / "artifact.svg",
    }
    inputs = {
        "structure.structure": structure,
        "artwork.raster_source.artifact": png,
        "artwork.raster_source.metadata": metadata,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = outputs.__getitem__

    resolver = model_test_resolver(
        "shape",
        overrides={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 2.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_border_label_width": 0.0,
            "shape_top_border_label_text": "",
            "shape_bottom_border_label_text": "",
            "shape_qr_payload": "",
            "shape_artwork_offset_x": 0.0,
            "shape_artwork_offset_y": 0.0,
            "shape_artwork_scale": 1.0,
        },
        project_root=directory,
    )
    context.resolver.side_effect = resolver
    context.resolver.color.side_effect = resolver.color

    compose.execute(context)
    return outputs["artifact"], png


def test_shape_declares_raster_artwork_dependency() -> None:
    """Raster SVG builds need a declared, independently bindable Product."""
    stage = next(stage for stage in MODEL.stages if stage.name == "compose")

    assert any(
        dependency.name == "raster_artwork"
        and dependency.model == "artwork"
        and dependency.stage == "raster_source"
        and dependency.product == "artifact"
        for dependency in stage.product_dependencies
    )


def test_raster_compose_embeds_original_png(
    tmp_path: Path,
) -> None:
    artifact, source = _compose_raster(tmp_path)

    root = ET.parse(artifact).getroot()
    images = list(root.iter(f"{{{SVG}}}image"))

    assert len(images) == 1

    href = images[0].get("href") or images[0].get("{http://www.w3.org/1999/xlink}href")
    assert href is not None
    assert href.startswith("data:image/png;base64,")

    decoded = base64.b64decode(href.split(",", 1)[1])
    assert decoded == source.read_bytes()

    with Image.open(io.BytesIO(decoded)) as image:
        assert image.mode == "RGBA"
        assert image.size == (32, 16)
        assert image.getpixel((31, 15)) == (220, 40, 90, 128)


def test_raster_svg_retains_shape_manufacturing_geometry(
    tmp_path: Path,
) -> None:
    artifact, _ = _compose_raster(tmp_path)

    root = ET.parse(artifact).getroot()
    ids = {element.get("id") for element in root.iter() if element.get("id") is not None}

    assert root.get("width") == "100mm"
    assert root.get("height") == "100mm"

    assert "cut-contour" in ids
    assert "outer-ridge" in ids
    assert "artwork" in ids

    contour = next(element for element in root.iter() if element.get("id") == "cut-contour")
    assert contour.get("fill") == "none"

    assert "base" not in ids


def test_raster_svg_preserves_aspect_ratio_and_placement(
    tmp_path: Path,
) -> None:
    """Raster Artwork preserves aspect ratio and fits inside Shape."""
    import math

    artifact, _ = _compose_raster(tmp_path)

    root = ET.parse(artifact).getroot()
    image = next(root.iter(f"{{{SVG}}}image"))

    x = float(image.get("x", "0"))
    y = float(image.get("y", "0"))
    width = float(image.get("width", "0"))
    height = float(image.get("height", "0"))

    # Raster placement must have positive dimensions.
    assert width > 0.0
    assert height > 0.0

    # The registered PNG is 32 x 16 pixels.
    # Its effective rendered dimensions must preserve 2:1.
    assert width / height == pytest.approx(2.0)

    # With zero offsets, the raster must be centered
    # on the registered Shape origin.

    assert x + width / 2.0 == pytest.approx(0.0, abs=1.0e-6)
    assert y + height / 2.0 == pytest.approx(0.0, abs=1.0e-6)

    # The authoritative placement region is the Shape
    # interior, not the complete 100 mm outer boundary.
    #
    # Resolve the actual registered interior from the
    # composition Product generated by COMPOSE.
    composition = artifact.parent / "composition.svg"

    interior = compose.registered_interior_region(composition)
    placement = compose.artwork_placement_circle(interior)

    assert placement.radius > 0.0

    # Every corner of the complete rectangular raster
    # must remain inside the available placement circle.
    # Checking only width or height is insufficient.
    corners = (
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    )

    for corner_x, corner_y in corners:
        distance = math.hypot(
            corner_x - placement.center_x,
            corner_y - placement.center_y,
        )

        assert distance <= placement.radius + 1.0e-6

    # Raster source dimensions do not determine the
    # manufactured Shape's physical dimensions.
    assert root.get("width") == "100mm"
    assert root.get("height") == "100mm"
