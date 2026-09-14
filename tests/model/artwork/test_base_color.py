"""
Tests for Artwork Base semantic color resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lowkey_artifact_builder.config.config import Resolver
from lowkey_artifact_builder.model.models.artwork.base_color import (
    resolve_base_color,
)
from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorLayer,
    VectorManifest,
)


def _resolver(
    values: dict[str, object],
    *,
    configured: set[str] | None = None,
) -> Resolver:
    """
    Construct an actual configuration Resolver for Base color tests.

    Values identified as explicitly configured receive realization
    provenance. Other values represent ordinary resolved defaults.
    """

    configured = configured or set()

    return Resolver(
        values=values,
        provenance={name: ("realization" if name in configured else "model") for name in values},
        colors={},
    )


def _layer(
    tmp_path: Path,
    *,
    index: int,
    printer_color_name: str,
    printer_color: tuple[
        int,
        int,
        int,
    ],
) -> VectorLayer:
    """
    Construct one registered Artwork layer.
    """

    path = tmp_path / f"color-{index}.svg"

    path.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    return VectorLayer(
        index=index,
        path=path,
        artifact_color_index=index,
        artifact_color=printer_color,
        printer_color_name=printer_color_name,
        printer_color=printer_color,
        distance=0.0,
    )


def _manifest(
    tmp_path: Path,
) -> VectorManifest:
    """
    Construct registered Artwork whose attachment color at position 0 is
    deterministically selected by the existing attachment-color operation.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    return VectorManifest(
        registered_extent=100,
        envelope=envelope,
        layers=(
            _layer(
                tmp_path,
                index=1,
                printer_color_name="red",
                printer_color=(
                    255,
                    0,
                    0,
                ),
            ),
            _layer(
                tmp_path,
                index=2,
                printer_color_name="blue",
                printer_color=(
                    0,
                    0,
                    255,
                ),
            ),
        ),
    )


def test_explicit_base_color_is_authoritative(
    tmp_path: Path,
) -> None:
    """
    Explicit artwork_base_color is authoritative regardless of Loop state or
    registered Artwork attachment color.
    """

    artwork = _manifest(
        tmp_path,
    )

    resolver = _resolver(
        {
            "artwork_base_color": "gold",
            "loop_inner_diameter": 5.0,
            "loop_color": "red",
            "loop_position": 0,
        },
        configured={
            "artwork_base_color",
            "loop_color",
        },
    )

    assert (
        resolve_base_color(
            artwork,
            resolver=resolver,
        )
        == "gold"
    )


def test_base_inherits_resolved_loop_color_when_loop_participates(
    tmp_path: Path,
) -> None:
    """
    Without explicit Base color, a participating Loop determines Base color.

    Base inherits the Loop's resolved semantic physical color rather than
    independently deriving another attachment color.
    """

    artwork = _manifest(
        tmp_path,
    )

    resolver = _resolver(
        {
            "loop_inner_diameter": 5.0,
            "loop_color": "gold",
            "loop_position": 0,
        },
        configured={
            "loop_color",
        },
    )

    assert (
        resolve_base_color(
            artwork,
            resolver=resolver,
        )
        == "gold"
    )


def test_base_inherits_derived_loop_color_when_loop_color_is_not_explicit(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """
    Base inherits the resolved Loop color even when that Loop color itself is
    derived from registered Artwork.
    """

    artwork = _manifest(
        tmp_path,
    )

    resolver = _resolver(
        {
            "loop_inner_diameter": 5.0,
            "loop_position": 90,
        },
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.model.models.artwork.base_color.resolve_loop_color",
        lambda artwork, *, resolver: "derived-loop-color",
    )

    assert (
        resolve_base_color(
            artwork,
            resolver=resolver,
        )
        == "derived-loop-color"
    )


def test_base_without_loop_uses_hypothetical_loop_at_position_zero(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """
    Without a participating Loop, Base color is derived using the same
    attachment-color operation as a hypothetical Loop at position 0.
    """

    artwork = _manifest(
        tmp_path,
    )

    resolver = _resolver(
        {
            "loop_inner_diameter": 0.0,
        },
    )

    positions: list[int] = []

    def select_color(
        artwork: VectorManifest,
        *,
        position: int,
    ) -> str:
        positions.append(
            position,
        )

        return "attachment-color"

    monkeypatch.setattr(
        "lowkey_artifact_builder.model.models.artwork.base_color.select_attachment_color",
        select_color,
    )

    assert (
        resolve_base_color(
            artwork,
            resolver=resolver,
        )
        == "attachment-color"
    )

    assert positions == [
        0,
    ]


def test_base_without_loop_does_not_resolve_loop_color(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """
    A nonparticipating Loop does not supply Base color.

    The Base instead follows the hypothetical-position-zero attachment rule.
    """

    artwork = _manifest(
        tmp_path,
    )

    resolver = _resolver(
        {
            "loop_inner_diameter": 0.0,
        },
    )

    def unexpected_loop_resolution(
        *args: object,
        **kwargs: object,
    ) -> str:
        raise AssertionError("nonparticipating Loop must not determine Base color")

    monkeypatch.setattr(
        "lowkey_artifact_builder.model.models.artwork.base_color.resolve_loop_color",
        unexpected_loop_resolution,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.model.models.artwork.base_color.select_attachment_color",
        lambda artwork, *, position: "attachment-color",
    )

    assert (
        resolve_base_color(
            artwork,
            resolver=resolver,
        )
        == "attachment-color"
    )
