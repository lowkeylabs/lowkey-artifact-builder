"""
Tests for persistent stage completion metadata.

Completion metadata records successful stage realization and the
persistent products produced by that realization.

Schema version 1 records stage identity and produced products.

Schema version 2 additionally records the fingerprint of the build
context under which those products were produced. Version 1 records
remain readable and are interpreted conservatively as having no
fingerprint provenance.
"""
# File: tests/engine/test_completion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    ProductFingerprint,
    StageCompletion,
    completion_path,
    read_stage_completion,
    write_stage_completion,
)

# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    value: str = "abc123",
) -> ProductFingerprint:
    """
    Create representative completion provenance.
    """

    return ProductFingerprint(
        algorithm="sha256",
        value=value,
    )


def _completion(
    *,
    fingerprint: ProductFingerprint | None = None,
) -> StageCompletion:
    """
    Create representative stage completion metadata.
    """

    return StageCompletion(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="vector",
        products=(
            "layers",
            "manifest",
        ),
        fingerprint=fingerprint,
    )


def _write_payload(
    working_dir: Path,
    payload: dict[str, object],
) -> None:
    """
    Write raw completion metadata for reader tests.
    """

    completion_path(
        working_dir,
    ).write_text(
        json.dumps(
            payload,
        ),
        encoding="utf-8",
    )


# =========================================================
# Completion representation
# =========================================================


def test_stage_completion_carries_execution_identity() -> None:
    """
    Completion metadata identifies the completed stage realization.
    """

    completion = _completion(
        fingerprint=_fingerprint(),
    )

    assert completion.artifact_id == "example"
    assert completion.model_name == "artwork"
    assert completion.realization == "default"
    assert completion.stage_name == "vector"


def test_stage_completion_carries_products() -> None:
    """
    Completion metadata records the products produced by the stage.
    """

    completion = _completion(
        fingerprint=_fingerprint(),
    )

    assert completion.products == (
        "layers",
        "manifest",
    )


def test_stage_completion_carries_fingerprint() -> None:
    """
    Completion metadata records the producing build-context fingerprint.
    """

    fingerprint = _fingerprint(
        "deadbeef",
    )

    completion = _completion(
        fingerprint=fingerprint,
    )

    assert completion.fingerprint == fingerprint


def test_stage_completion_allows_missing_fingerprint() -> None:
    """
    Completion metadata may represent legacy provenance absence.
    """

    completion = _completion()

    assert completion.fingerprint is None


def test_stage_completion_is_immutable() -> None:
    """
    Persistent completion records are immutable value objects.
    """

    completion = _completion(
        fingerprint=_fingerprint(),
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        completion.stage_name = "raster"  # type: ignore[misc]


def test_stage_completions_compare_by_value() -> None:
    """
    Equivalent completion records compare deterministically.
    """

    assert _completion(
        fingerprint=_fingerprint(),
    ) == _completion(
        fingerprint=_fingerprint(),
    )


def test_different_completion_fingerprints_compare_differently() -> None:
    """
    Provenance participates in completion-record identity.
    """

    assert _completion(
        fingerprint=_fingerprint(
            "old",
        ),
    ) != _completion(
        fingerprint=_fingerprint(
            "new",
        ),
    )


# =========================================================
# Completion path
# =========================================================


def test_completion_path_is_inside_stage_working_directory(
    tmp_path: Path,
) -> None:
    """
    Completion metadata belongs to the producing stage workspace.
    """

    assert (
        completion_path(
            tmp_path,
        ).parent
        == tmp_path
    )


def test_completion_path_is_hidden_metadata_file(
    tmp_path: Path,
) -> None:
    """
    Completion metadata does not collide with declared stage products.
    """

    assert (
        completion_path(
            tmp_path,
        ).name
        == ".completion.json"
    )


# =========================================================
# Persistence
# =========================================================


def test_write_stage_completion_creates_metadata_file(
    tmp_path: Path,
) -> None:
    """
    Writing completion metadata creates its persistent representation.
    """

    write_stage_completion(
        tmp_path,
        _completion(
            fingerprint=_fingerprint(),
        ),
    )

    assert completion_path(
        tmp_path,
    ).is_file()


def test_write_stage_completion_requires_working_directory(
    tmp_path: Path,
) -> None:
    """
    Completion persistence does not own stage workspace creation.
    """

    working_dir = tmp_path / "missing" / "stage"

    with pytest.raises(
        FileNotFoundError,
        match="Stage working directory does not exist",
    ):
        write_stage_completion(
            working_dir,
            _completion(
                fingerprint=_fingerprint(),
            ),
        )


def test_written_completion_uses_schema_version_two(
    tmp_path: Path,
) -> None:
    """
    Fingerprint-aware completion metadata uses schema version 2.
    """

    write_stage_completion(
        tmp_path,
        _completion(
            fingerprint=_fingerprint(),
        ),
    )

    payload = json.loads(
        completion_path(
            tmp_path,
        ).read_text(
            encoding="utf-8",
        )
    )

    assert payload["schema_version"] == 2


def test_written_completion_contains_stage_identity(
    tmp_path: Path,
) -> None:
    """
    Persistent completion data contains the completed realization identity.
    """

    write_stage_completion(
        tmp_path,
        _completion(
            fingerprint=_fingerprint(),
        ),
    )

    payload = json.loads(
        completion_path(
            tmp_path,
        ).read_text(
            encoding="utf-8",
        )
    )

    assert payload["artifact_id"] == "example"
    assert payload["model_name"] == "artwork"
    assert payload["realization"] == "default"
    assert payload["stage_name"] == "vector"


def test_written_completion_contains_products(
    tmp_path: Path,
) -> None:
    """
    Persistent completion data records produced logical products.
    """

    write_stage_completion(
        tmp_path,
        _completion(
            fingerprint=_fingerprint(),
        ),
    )

    payload = json.loads(
        completion_path(
            tmp_path,
        ).read_text(
            encoding="utf-8",
        )
    )

    assert payload["products"] == [
        "layers",
        "manifest",
    ]


def test_written_completion_contains_fingerprint(
    tmp_path: Path,
) -> None:
    """
    Persistent completion data records build-context provenance.
    """

    write_stage_completion(
        tmp_path,
        _completion(
            fingerprint=ProductFingerprint(
                algorithm="sha256",
                value="deadbeef",
            ),
        ),
    )

    payload = json.loads(
        completion_path(
            tmp_path,
        ).read_text(
            encoding="utf-8",
        )
    )

    assert payload["fingerprint"] == {
        "algorithm": "sha256",
        "value": "deadbeef",
    }


def test_written_completion_preserves_missing_fingerprint(
    tmp_path: Path,
) -> None:
    """
    Missing provenance is represented explicitly in schema version 2.
    """

    write_stage_completion(
        tmp_path,
        _completion(),
    )

    payload = json.loads(
        completion_path(
            tmp_path,
        ).read_text(
            encoding="utf-8",
        )
    )

    assert payload["fingerprint"] is None


# =========================================================
# Reading completion metadata
# =========================================================


def test_read_stage_completion_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    """
    Missing completion metadata means no successful completion is recorded.
    """

    assert (
        read_stage_completion(
            tmp_path,
        )
        is None
    )


def test_stage_completion_round_trips_with_fingerprint(
    tmp_path: Path,
) -> None:
    """
    Completion metadata including provenance survives persistence.
    """

    expected = _completion(
        fingerprint=_fingerprint(
            "deadbeef",
        ),
    )

    write_stage_completion(
        tmp_path,
        expected,
    )

    assert (
        read_stage_completion(
            tmp_path,
        )
        == expected
    )


def test_stage_completion_round_trips_without_fingerprint(
    tmp_path: Path,
) -> None:
    """
    Missing provenance survives persistence without becoming freshness.
    """

    expected = _completion()

    write_stage_completion(
        tmp_path,
        expected,
    )

    assert (
        read_stage_completion(
            tmp_path,
        )
        == expected
    )


# =========================================================
# Schema compatibility
# =========================================================


def test_read_stage_completion_supports_schema_version_one(
    tmp_path: Path,
) -> None:
    """
    Existing version-1 completion metadata remains readable.

    Version 1 predates fingerprint provenance and therefore produces a
    completion record whose fingerprint is None.
    """

    _write_payload(
        tmp_path,
        {
            "schema_version": 1,
            "artifact_id": "example",
            "model_name": "artwork",
            "realization": "default",
            "stage_name": "vector",
            "products": [
                "layers",
                "manifest",
            ],
        },
    )

    completion = read_stage_completion(
        tmp_path,
    )

    assert completion is not None
    assert completion.artifact_id == "example"
    assert completion.model_name == "artwork"
    assert completion.realization == "default"
    assert completion.stage_name == "vector"
    assert completion.products == (
        "layers",
        "manifest",
    )
    assert completion.fingerprint is None


def test_read_stage_completion_reconstructs_version_two_fingerprint(
    tmp_path: Path,
) -> None:
    """
    Version-2 fingerprint provenance is restored as a typed value.
    """

    _write_payload(
        tmp_path,
        {
            "schema_version": 2,
            "artifact_id": "example",
            "model_name": "artwork",
            "realization": "default",
            "stage_name": "vector",
            "products": [
                "layers",
            ],
            "fingerprint": {
                "algorithm": "sha256",
                "value": "deadbeef",
            },
        },
    )

    completion = read_stage_completion(
        tmp_path,
    )

    assert completion is not None
    assert completion.fingerprint == ProductFingerprint(
        algorithm="sha256",
        value="deadbeef",
    )


def test_read_stage_completion_supports_version_two_without_fingerprint(
    tmp_path: Path,
) -> None:
    """
    Version-2 metadata may explicitly record missing provenance.
    """

    _write_payload(
        tmp_path,
        {
            "schema_version": 2,
            "artifact_id": "example",
            "model_name": "artwork",
            "realization": "default",
            "stage_name": "vector",
            "products": [
                "layers",
            ],
            "fingerprint": None,
        },
    )

    completion = read_stage_completion(
        tmp_path,
    )

    assert completion is not None
    assert completion.fingerprint is None


def test_read_stage_completion_rejects_unknown_schema_version(
    tmp_path: Path,
) -> None:
    """
    Unknown completion schemas are not silently interpreted.
    """

    _write_payload(
        tmp_path,
        {
            "schema_version": 999,
            "artifact_id": "example",
            "model_name": "artwork",
            "realization": "default",
            "stage_name": "vector",
            "products": [
                "layers",
            ],
        },
    )

    with pytest.raises(
        ValueError,
        match="Unsupported stage completion schema",
    ):
        read_stage_completion(
            tmp_path,
        )


# =========================================================
# Invalid metadata
# =========================================================


def test_read_stage_completion_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    """
    Corrupt completion metadata is distinguishable from missing metadata.
    """

    completion_path(
        tmp_path,
    ).write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        read_stage_completion(
            tmp_path,
        )


@pytest.mark.parametrize(
    "fingerprint",
    [
        {},
        {
            "algorithm": "sha256",
        },
        {
            "value": "deadbeef",
        },
        {
            "algorithm": "",
            "value": "deadbeef",
        },
        {
            "algorithm": "sha256",
            "value": "",
        },
        "sha256:deadbeef",
        123,
    ],
)
def test_read_stage_completion_rejects_invalid_version_two_fingerprint(
    tmp_path: Path,
    fingerprint: object,
) -> None:
    """
    Malformed version-2 provenance is not treated as missing provenance.
    """

    _write_payload(
        tmp_path,
        {
            "schema_version": 2,
            "artifact_id": "example",
            "model_name": "artwork",
            "realization": "default",
            "stage_name": "vector",
            "products": [
                "layers",
            ],
            "fingerprint": fingerprint,
        },
    )

    with pytest.raises(
        ValueError,
    ):
        read_stage_completion(
            tmp_path,
        )
