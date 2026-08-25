"""
Tests for persistent stage completion metadata.

Completion metadata records that one stage execution successfully produced
and validated its declared persistent products.

These tests establish the durable completion-record contract independently
of product-state evaluation, freshness evaluation, resumability, and stage
execution integration.
"""
# File: tests/engine/test_completion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    StageCompletion,
    completion_path,
    read_stage_completion,
    write_stage_completion,
)

# =========================================================
# Helpers
# =========================================================


def _completion() -> StageCompletion:
    """
    Create representative stage completion metadata.
    """

    return StageCompletion(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="vector",
        products=(
            "colors",
            "manifest",
        ),
    )


# =========================================================
# Completion metadata
# =========================================================


def test_stage_completion_carries_execution_identity() -> None:
    """
    Completion metadata identifies the completed stage realization.
    """

    completion = _completion()

    assert completion.artifact_id == "example"
    assert completion.model_name == "artwork"
    assert completion.realization == "default"
    assert completion.stage_name == "vector"


def test_stage_completion_carries_declared_products() -> None:
    """
    Completion metadata records the logical products successfully produced.
    """

    completion = _completion()

    assert completion.products == (
        "colors",
        "manifest",
    )


def test_stage_completion_allows_no_products() -> None:
    """
    The completion contract does not require a stage to declare products.
    """

    completion = StageCompletion(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="prepare",
        products=(),
    )

    assert completion.products == ()


def test_stage_completion_is_immutable() -> None:
    """
    Completion metadata is an immutable record of completed work.
    """

    completion = _completion()

    with pytest.raises(
        FrozenInstanceError,
    ):
        completion.stage_name = "raster"  # type: ignore[misc]


def test_stage_completions_compare_by_value() -> None:
    """
    Completion records support deterministic value comparison.
    """

    assert _completion() == _completion()


# =========================================================
# Completion location
# =========================================================


def test_completion_path_is_inside_stage_working_directory(
    tmp_path: Path,
) -> None:
    """
    Completion metadata has one deterministic stage-local location.
    """

    working_dir = tmp_path / "artifacts" / "example" / "artwork" / "default" / "30-vector"

    assert completion_path(
        working_dir,
    ) == (working_dir / ".completion.json")


def test_completion_path_does_not_create_workspace(
    tmp_path: Path,
) -> None:
    """
    Resolving the completion path is side-effect free.
    """

    working_dir = tmp_path / "missing" / "30-vector"

    path = completion_path(
        working_dir,
    )

    assert path == (working_dir / ".completion.json")

    assert not working_dir.exists()


# =========================================================
# Persistence
# =========================================================


def test_write_stage_completion_persists_record(
    tmp_path: Path,
) -> None:
    """
    Completion metadata can be persisted after successful validation.
    """

    working_dir = tmp_path / "30-vector"

    working_dir.mkdir(
        parents=True,
    )

    completion = _completion()

    write_stage_completion(
        working_dir,
        completion,
    )

    assert completion_path(
        working_dir,
    ).is_file()


def test_write_stage_completion_does_not_create_working_directory(
    tmp_path: Path,
) -> None:
    """
    Completion persistence does not acquire workspace-creation responsibility.
    """

    working_dir = tmp_path / "missing" / "30-vector"

    with pytest.raises(
        FileNotFoundError,
    ):
        write_stage_completion(
            working_dir,
            _completion(),
        )

    assert not working_dir.exists()


def test_read_stage_completion_round_trips_record(
    tmp_path: Path,
) -> None:
    """
    Persisted completion metadata reconstructs the semantic record.
    """

    working_dir = tmp_path / "30-vector"

    working_dir.mkdir(
        parents=True,
    )

    expected = _completion()

    write_stage_completion(
        working_dir,
        expected,
    )

    actual = read_stage_completion(
        working_dir,
    )

    assert actual == expected


def test_read_stage_completion_returns_none_when_absent(
    tmp_path: Path,
) -> None:
    """
    Missing completion metadata is represented without an exception.
    """

    working_dir = tmp_path / "30-vector"

    assert (
        read_stage_completion(
            working_dir,
        )
        is None
    )


# =========================================================
# Persistent representation
# =========================================================


def test_completion_record_uses_versioned_json(
    tmp_path: Path,
) -> None:
    """
    Durable completion metadata has an explicit schema version.
    """

    import json

    working_dir = tmp_path / "30-vector"

    working_dir.mkdir(
        parents=True,
    )

    write_stage_completion(
        working_dir,
        _completion(),
    )

    data = json.loads(
        completion_path(
            working_dir,
        ).read_text(
            encoding="utf-8",
        )
    )

    assert data == {
        "schema_version": 1,
        "artifact_id": "example",
        "model_name": "artwork",
        "realization": "default",
        "stage_name": "vector",
        "products": [
            "colors",
            "manifest",
        ],
    }


def test_read_stage_completion_rejects_unknown_schema_version(
    tmp_path: Path,
) -> None:
    """
    Unsupported completion schemas are not silently interpreted.
    """

    path = tmp_path / "30-vector" / ".completion.json"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        """
{
    "schema_version": 999,
    "artifact_id": "example",
    "model_name": "artwork",
    "realization": "default",
    "stage_name": "vector",
    "products": ["manifest"]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="schema",
    ):
        read_stage_completion(
            path.parent,
        )


def test_read_stage_completion_rejects_malformed_json(
    tmp_path: Path,
) -> None:
    """
    Corrupt completion metadata is distinguishable from absent metadata.
    """

    path = tmp_path / "30-vector" / ".completion.json"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        read_stage_completion(
            path.parent,
        )


def test_read_stage_completion_rejects_missing_required_field(
    tmp_path: Path,
) -> None:
    """
    Structurally incomplete completion metadata is invalid.
    """

    path = tmp_path / "30-vector" / ".completion.json"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        """
{
    "schema_version": 1,
    "artifact_id": "example",
    "model_name": "artwork",
    "realization": "default",
    "products": ["manifest"]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        read_stage_completion(
            path.parent,
        )


def test_read_stage_completion_rejects_invalid_products(
    tmp_path: Path,
) -> None:
    """
    Product identities in completion metadata must have the expected shape.
    """

    path = tmp_path / "30-vector" / ".completion.json"

    path.parent.mkdir(
        parents=True,
    )

    path.write_text(
        """
{
    "schema_version": 1,
    "artifact_id": "example",
    "model_name": "artwork",
    "realization": "default",
    "stage_name": "vector",
    "products": "manifest"
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        read_stage_completion(
            path.parent,
        )
