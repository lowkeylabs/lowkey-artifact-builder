"""
Incremental execution of selected Artwork dependencies.

Exercise the ordinary dependency-aware engine using real Artwork and Shape
plans, while replacing external manufacturing operations with deterministic
test products.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import lowkey_artifact_builder.engine.incremental as incremental_module
from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plan,
    execute_dependency_build,
)
from lowkey_artifact_builder.model import ProductRef

ARTIFACT_ID = "example"


def _configure(root: Path) -> None:
    (root / "source.png").write_bytes(b"stable source contents")

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
        project_root=root,
    )


def _plan(root: Path, realization: str):
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
        project_root=root,
    )


def test_selected_producer_is_built_and_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Initial build produces the selected Artwork and Shape products.

    A repeated build with unchanged inputs reuses persistent products
    without executing either producer or consumer stages.
    """
    _configure(tmp_path)

    executed: list[tuple[str, str]] = []

    def execute_stage(context) -> None:
        executed.append(
            (
                context.resolver("realization"),
                context.stage_name,
            )
        )

        for path in context.outputs.values():
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                "deterministic test product",
                encoding="utf-8",
            )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        execute_stage,
    )

    execute_dependency_build(
        _plan(tmp_path, "coaster_print"),
    )

    assert ("artwork_color", "vector") in executed
    assert ("coaster_print", "compose") in executed
    assert not any(realization == "artwork_vector" for realization, _ in executed)
    assert not any(realization == "coaster_engrave" for realization, _ in executed)

    executed.clear()

    execute_dependency_build(
        _plan(tmp_path, "coaster_print"),
    )

    assert executed == []


def test_changed_selected_producer_rebuilds_only_its_consumer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changing the selected producer's source invalidates its consumer.

    The other Shape Realization and its Artwork dependency remain
    reusable when their own required build contexts are unchanged.
    """
    _configure(tmp_path)

    executed: list[tuple[str, str]] = []

    def execute_stage(context) -> None:
        executed.append(
            (
                context.resolver("realization"),
                context.stage_name,
            )
        )

        for path in context.outputs.values():
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                "deterministic test product",
                encoding="utf-8",
            )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        execute_stage,
    )

    execute_dependency_build(
        _plan(tmp_path, "coaster_print"),
    )
    execute_dependency_build(
        _plan(tmp_path, "coaster_engrave"),
    )

    executed.clear()

    # Change only the first Artwork Realization's effective configuration.
    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": "source.png",
            "realizations": {
                "artwork_color": {
                    "variant": "artwork.default",
                    "parameters": {
                        "artifact_color_count": 2,
                    },
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
        project_root=tmp_path,
    )

    execute_dependency_build(
        _plan(tmp_path, "coaster_print"),
    )

    assert ("artwork_color", "vector") in executed
    assert ("coaster_print", "compose") in executed

    executed.clear()

    execute_dependency_build(
        _plan(tmp_path, "coaster_engrave"),
    )

    assert executed == []
