"""
Shape QR physical dimensionalization tests.

QR geometry is already registered by Compose. Extrude consumes that
persistent geometry and produces independently printable dark and light
components, without resolving physical printer colors.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import extrude

SVG_NS = "http://www.w3.org/2000/svg"


def _write_registered_geometry(
    path: Path,
    *,
    rectangle: tuple[float, float, float, float] | None = None,
) -> None:
    """Write minimal registered Shape-space SVG geometry."""

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"viewBox": "-0.5 -0.5 1 1"},
    )

    if rectangle is None:
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}circle",
            {
                "id": "shape-boundary",
                "cx": "0",
                "cy": "0",
                "r": "0.5",
            },
        )
    else:
        x, y, width, height = rectangle
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}rect",
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
            },
        )

    ET.ElementTree(root).write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )


def _registered_qr_fixture(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """
    Create a minimal Compose Product containing two complementary
    registered QR regions.

    The small rectangular regions stand in for the registered
    module geometry. QR encoding itself is not under test.
    """

    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "composition-products.json"

    _write_registered_geometry(composition)

    _write_registered_geometry(
        tmp_path / "qr-dark.svg",
        rectangle=(-0.15, -0.15, 0.15, 0.30),
    )
    _write_registered_geometry(
        tmp_path / "qr-light.svg",
        rectangle=(0.0, -0.15, 0.15, 0.30),
    )

    manifest.write_text(
        json.dumps(
            {
                "composition": composition.name,
                "border_labels": {
                    "top": None,
                    "bottom": None,
                },
                "artwork": None,
                "artwork_fill": None,
                "qr": {
                    "footprint": {
                        "type": "rounded_rect",
                        "x": 0.0,
                        "y": 0.0,
                        "width": 0.30,
                        "height": 0.30,
                        "corner_radius": 0.01,
                    },
                    "quiet_zone_modules": 4,
                    "components": {
                        "qr-dark": {"path": "qr-dark.svg"},
                        "qr-light": {"path": "qr-light.svg"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    return composition, manifest


def _extrude_qr(
    tmp_path: Path,
    *,
    raise_style: str,
    qr_raise: float = 0.8,
) -> tuple[dict, dict[str, str]]:
    """
    Execute the real Shape Extrude stage against registered QR geometry.

    Capture the OpenSCAD passed to the manufacturing renderer without
    requiring OpenSCAD to run.
    """

    composition, composition_manifest = _registered_qr_fixture(
        tmp_path,
    )
    manifest = tmp_path / "extrude" / "products.json"

    values: dict[str, object] = {
        "shape_size": 100.0,
        "shape_base_raise": 2.0,
        "shape_raise_style": raise_style,
        "shape_outer_ridge_raise": 0.0,
        "shape_outer_ridge_style": "integrated",
        "shape_hole_diameter": 0.0,
        "shape_loop_inner_diameter": 0.0,
        "shape_qr_raise": qr_raise,
    }

    context = Mock(spec=StageContext)

    context.input.side_effect = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }.__getitem__

    context.output.side_effect = {
        "manifest": manifest,
    }.__getitem__

    context.resolver.side_effect = values.__getitem__

    rendered: dict[str, str] = {}

    def capture_render(
        source: str,
        output_path: Path,
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        rendered[output_path.name] = source
        output_path.write_text(
            source,
            encoding="utf-8",
        )

    with patch.object(
        extrude,
        "render_stl_source",
        side_effect=capture_render,
    ):
        extrude.execute(context)

    data = json.loads(manifest.read_text(encoding="utf-8"))

    return data, rendered


@pytest.mark.parametrize(
    ("raise_style", "expected_bottom", "expected_top"),
    [
        ("raised", 2.0, 2.8),
        ("inlaid", 0.0, 2.0),
    ],
)
def test_qr_dark_and_light_share_physical_z_interval(
    tmp_path: Path,
    raise_style: str,
    expected_bottom: float,
    expected_top: float,
) -> None:
    """
    Both QR regions share one physical Z interval.

    Raised QR sits on the Base. Inlaid QR occupies the complete
    Base thickness, independently of the configured raised height.

    Inspect the generated manufacturing geometry rather than relying
    on a particular numeric string representation.
    """

    import re

    data, rendered = _extrude_qr(
        tmp_path,
        raise_style=raise_style,
    )

    components = {component["name"]: component for component in data["components"]}

    assert "qr-dark" in components
    assert "qr-light" in components

    intervals: list[tuple[float, float]] = []

    for name, registered_name in (
        ("qr-dark", "qr-dark.svg"),
        ("qr-light", "qr-light.svg"),
    ):
        component_path = components[name]["path"]

        assert component_path in rendered

        source = rendered[component_path]

        assert registered_name in source

        placement = re.search(
            r"translate\(\[\s*0\s*,\s*0\s*,\s*"
            r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
            r"\s*\]\)",
            source,
        )

        extrusion = re.search(
            r"linear_extrude\(\s*height\s*=\s*"
            r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
            source,
        )

        assert placement is not None
        assert extrusion is not None

        bottom = float(placement.group(1))
        height = float(extrusion.group(1))
        top = bottom + height

        assert bottom == pytest.approx(expected_bottom)
        assert top == pytest.approx(expected_top)

        intervals.append((bottom, top))

    assert intervals[0] == pytest.approx(intervals[1])


def test_inlaid_qr_partitions_base_without_physical_overlap(
    tmp_path: Path,
) -> None:
    """
    The inlaid Base must subtract the union of both QR regions.

    Merely adding QR solids on top of an intact Base would create
    overlapping physical material and violate the inlaid contract.
    """

    data, rendered = _extrude_qr(
        tmp_path,
        raise_style="inlaid",
    )

    components = {component["name"]: component for component in data["components"]}

    assert {"base", "qr-dark", "qr-light"} <= set(components)

    base_source = rendered[components["base"]["path"]]

    assert "difference()" in base_source

    # The Base subtraction must consume the registered QR regions,
    # rather than simply leaving the full Base beneath them.
    assert "qr-dark.svg" in base_source
    assert "qr-light.svg" in base_source


def test_qr_extrusion_preserves_semantic_identity_without_colors(
    tmp_path: Path,
) -> None:
    """
    Extrude identifies QR components but does not resolve their
    physical printing colors. That responsibility belongs to Package.
    """

    data, _ = _extrude_qr(
        tmp_path,
        raise_style="raised",
    )

    components = {component["name"]: component for component in data["components"]}

    assert "qr-dark" in components
    assert "qr-light" in components

    for name in ("qr-dark", "qr-light"):
        component = components[name]

        assert component["path"].endswith(".stl")
        assert "printer_color" not in component
        assert "color" not in component
