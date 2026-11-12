"""Phase 3 Slice E: ARTWORK Realization isolation and Product freshness."""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine.dependency_build import (
    execute_dependency_build,
    plan_dependency_build,
)
from lowkey_artifact_builder.engine.events import ExecutionEvent
from lowkey_artifact_builder.engine.plan import create_build_plans
from lowkey_artifact_builder.model.specs import ProductRef

ARTIFACT_ID = "mixed-representations"


def _configure(
    tmp_path: Path,
    *,
    vector_envelope_mode: str = "alpha",
) -> Path:
    """
    Configure three independent Artwork Realizations using one
    PNG source supported by all three representations.
    """
    source = tmp_path / "customer.png"

    if not source.exists():
        image = Image.new(
            "RGBA",
            (64, 64),
            (0, 0, 0, 0),
        )

        try:
            pixels = image.load()
            assert pixels is not None

            for y in range(8, 56):
                for x in range(8, 56):
                    pixels[x, y] = (32, 48, 128, 255)

            image.save(source, format="PNG")
        finally:
            image.close()

    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": str(source),
            "realizations": {
                "original": {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "source",
                        "artwork_processing": "none",
                    },
                },
                "preview": {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "raster",
                        "artwork_processing": "none",
                    },
                },
                "engraving": {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "vector",
                        "artwork_processing": "auto",
                        "artwork_envelope_mode": vector_envelope_mode,
                        "artifact_color_count": 1,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    return source


def _target(realization: str) -> ProductRef:
    stage, product = {
        "original": ("source", "artifact"),
        "preview": ("raster_source", "artifact"),
        "engraving": ("vector", "manifest"),
    }[realization]

    return ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization=realization,
        stage=stage,
        product=product,
    )


def _plan(tmp_path: Path, realization: str):
    target = _target(realization)
    plans = create_build_plans(
        ARTIFACT_ID,
        realization=realization,
        targets=(target,),
        project_root=tmp_path,
    )
    assert len(plans) == 1
    return plans[0]


def _product_path(plan, target: ProductRef) -> Path:
    for stage in plan.stages:
        if stage.name == target.stage:
            for product in stage.products:
                if product.spec.name == target.product:
                    return product.path
    pytest.fail(f"Missing declared Product: {target}")


def _build(tmp_path: Path, realization: str) -> Path:
    plan = _plan(tmp_path, realization)
    target = _target(realization)
    output = _product_path(plan, target)
    execute_dependency_build(plan)
    assert output.is_file()
    return output


def test_three_representations_have_independent_product_ownership(
    tmp_path: Path,
) -> None:
    """One Artifact supports three independently named Realizations."""
    _configure(tmp_path)

    products = {name: _build(tmp_path, name) for name in ("original", "preview", "engraving")}

    assert len(set(products.values())) == 3

    for name, path in products.items():
        assert path.is_file(), name
        assert name in path.parts


def test_each_realization_plans_only_compatible_stages(
    tmp_path: Path,
) -> None:
    """Source and raster requests avoid vector manufacturing."""
    _configure(tmp_path)

    source_stages = {stage.name for stage in _plan(tmp_path, "original").stages}
    raster_stages = {stage.name for stage in _plan(tmp_path, "preview").stages}
    vector_stages = {stage.name for stage in _plan(tmp_path, "engraving").stages}

    assert source_stages == {"source"}
    assert raster_stages == {"raster_source"}

    assert "vector" in vector_stages
    assert "prepare" in vector_stages

    assert not {"extrude", "package"} & vector_stages


def test_rebuilding_one_realization_preserves_unrelated_products(
    tmp_path: Path,
) -> None:
    """An unchanged build does not rewrite other Realizations."""
    _configure(tmp_path)

    products = {name: _build(tmp_path, name) for name in ("original", "preview", "engraving")}

    before = {name: (path.read_bytes(), path.stat().st_mtime_ns) for name, path in products.items()}

    _build(tmp_path, "engraving")

    for name, path in products.items():
        assert (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        ) == before[name]


def test_vector_configuration_change_preserves_other_realizations(
    tmp_path: Path,
) -> None:
    """
    Changing only vector configuration must not rewrite
    source-preserving or raster-preserving Products.
    """
    _configure(tmp_path, vector_envelope_mode="alpha")

    products = {name: _build(tmp_path, name) for name in ("original", "preview", "engraving")}

    before = {name: (path.read_bytes(), path.stat().st_mtime_ns) for name, path in products.items()}

    _configure(tmp_path, vector_envelope_mode="shrink-wrap")

    _build(tmp_path, "engraving")

    for name in ("original", "preview"):
        path = products[name]
        assert (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        ) == before[name]


def test_unchanged_realizations_have_no_required_stage_work(
    tmp_path: Path,
) -> None:
    """All three completed Realizations are reusable."""
    _configure(tmp_path)

    for name in ("original", "preview", "engraving"):
        _build(tmp_path, name)

    for name in ("original", "preview", "engraving"):
        execution = plan_dependency_build(_plan(tmp_path, name))

        assert not execution.required_product_dependencies
        assert not [stage for stage in execution.stages if stage.requires_execution], name


def test_vector_configuration_change_invalidates_vector_only(
    tmp_path: Path,
) -> None:
    """Changing vector envelope policy must not invalidate other Products."""
    _configure(tmp_path, vector_envelope_mode="alpha")

    for name in ("original", "preview", "engraving"):
        _build(tmp_path, name)

    _configure(tmp_path, vector_envelope_mode="shrink-wrap")

    vector = plan_dependency_build(_plan(tmp_path, "engraving"))

    required = {stage.stage_name for stage in vector.stages if stage.requires_execution}

    assert "prepare" in required
    assert "vector" in required

    for name in ("original", "preview"):
        execution = plan_dependency_build(_plan(tmp_path, name))
        assert not any(stage.requires_execution for stage in execution.stages), name


def test_source_change_invalidates_all_three_realizations(
    tmp_path: Path,
) -> None:
    """Changing the common source invalidates every representation."""
    source = _configure(tmp_path)

    for name in ("original", "preview", "engraving"):
        _build(tmp_path, name)

    with Image.open(source) as image:
        modified = image.copy()

    try:
        modified.putpixel((20, 20), (200, 40, 60, 255))
        modified.save(source, format="PNG")
    finally:
        modified.close()

    for name in ("original", "preview", "engraving"):
        execution = plan_dependency_build(_plan(tmp_path, name))

        assert any(stage.requires_execution for stage in execution.stages), name


def test_vector_rebuild_emits_no_other_realization_stage_events(
    tmp_path: Path,
) -> None:
    """Rebuilding vector work never executes source/raster Realizations."""
    _configure(tmp_path, vector_envelope_mode="alpha")

    for name in ("original", "preview", "engraving"):
        _build(tmp_path, name)

    _configure(tmp_path, vector_envelope_mode="shrink-wrap")

    events: list[ExecutionEvent] = []

    execute_dependency_build(
        _plan(tmp_path, "engraving"),
        event_sink=events.append,
    )

    started = [event for event in events if event.kind == "stage.started"]

    assert started
    assert all(event.realization == "engraving" for event in started)

    assert any(event.stage_name == "prepare" for event in started)
    assert any(event.stage_name == "vector" for event in started)


def test_vector_rebuild_restores_product_freshness(
    tmp_path: Path,
) -> None:
    """
    Changing vector-specific configuration invalidates its pipeline.

    After rebuilding, every required vector stage is reusable.
    """
    _configure(tmp_path, vector_envelope_mode="alpha")
    _build(tmp_path, "engraving")

    _configure(tmp_path, vector_envelope_mode="shrink-wrap")

    stale = plan_dependency_build(_plan(tmp_path, "engraving"))

    stale_stages = {stage.stage_name for stage in stale.stages if stage.requires_execution}

    assert "prepare" in stale_stages
    assert "vector" in stale_stages

    events: list[ExecutionEvent] = []

    execute_dependency_build(
        _plan(tmp_path, "engraving"),
        event_sink=events.append,
    )

    started_stages = {event.stage_name for event in events if event.kind == "stage.started"}

    assert stale_stages <= started_stages

    fresh = plan_dependency_build(_plan(tmp_path, "engraving"))

    assert not fresh.required_product_dependencies
    assert not any(stage.requires_execution for stage in fresh.stages)


def test_shared_source_rebuild_restores_freshness_independently(
    tmp_path: Path,
) -> None:
    """
    Changing the shared source invalidates all three Realizations.

    Rebuilding one Realization must not implicitly rebuild or
    mark the other two as fresh.
    """
    source = _configure(tmp_path)

    names = ("original", "preview", "engraving")

    for name in names:
        _build(tmp_path, name)

    with Image.open(source) as image:
        modified = image.copy()

    try:
        modified.putpixel((20, 20), (200, 40, 60, 255))
        modified.save(source, format="PNG")
    finally:
        modified.close()

    def requires_work(name: str) -> bool:
        execution = plan_dependency_build(_plan(tmp_path, name))

        return bool(execution.required_product_dependencies) or any(
            stage.requires_execution for stage in execution.stages
        )

    assert all(requires_work(name) for name in names)

    _build(tmp_path, "original")

    assert not requires_work("original")
    assert requires_work("preview")
    assert requires_work("engraving")

    _build(tmp_path, "preview")

    assert not requires_work("original")
    assert not requires_work("preview")
    assert requires_work("engraving")

    _build(tmp_path, "engraving")

    assert all(not requires_work(name) for name in names)


def test_repeated_builds_execute_no_stages_after_freshness_restored(
    tmp_path: Path,
) -> None:
    """
    Once all three Realizations are fresh, repeated targeted
    builds must reuse their registered Products without executing
    any Stage.
    """
    _configure(tmp_path)

    names = ("original", "preview", "engraving")

    products = {name: _build(tmp_path, name) for name in names}

    before = {
        name: (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for name, path in products.items()
    }

    events: list[ExecutionEvent] = []

    for name in names:
        execute_dependency_build(
            _plan(tmp_path, name),
            event_sink=events.append,
        )

    started = [event for event in events if event.kind == "stage.started"]

    completed = [event for event in events if event.kind == "stage.completed"]

    assert started == []
    assert completed == []

    for name, path in products.items():
        assert (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        ) == before[name]

        execution = plan_dependency_build(_plan(tmp_path, name))

        assert not execution.required_product_dependencies
        assert not any(stage.requires_execution for stage in execution.stages)
