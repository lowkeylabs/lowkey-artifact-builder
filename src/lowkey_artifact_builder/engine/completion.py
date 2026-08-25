"""
Persistent stage completion metadata.

Completion metadata records that one stage execution successfully produced
and validated its declared persistent products.

Schema version 1 records stage identity and produced products.

Schema version 2 additionally records the fingerprint of the build context
under which those products were produced. Version 1 records remain readable
and are interpreted conservatively as having no fingerprint provenance.

Product-state evaluation, dependency invalidation, execution planning, and
execution integration are handled separately.
"""
# File: src/lowkey_artifact_builder/engine/completion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .freshness import (
    ProductFingerprint,
)

# =========================================================
# Constants
# =========================================================


_COMPLETION_FILENAME = ".completion.json"
_COMPLETION_SCHEMA_VERSION = 2
_SUPPORTED_COMPLETION_SCHEMA_VERSIONS = {
    1,
    2,
}


# =========================================================
# Completion metadata
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class StageCompletion:
    """
    Durable record of one successfully completed stage realization.

    products contains the logical product identities successfully produced
    and validated by the stage.

    fingerprint records the build context under which the stage products
    were produced. None represents completion metadata without sufficient
    provenance to prove freshness.
    """

    artifact_id: str
    model_name: str
    realization: str
    stage_name: str
    products: tuple[str, ...]
    fingerprint: ProductFingerprint | None = None


# =========================================================
# Completion location
# =========================================================


def completion_path(
    working_dir: Path,
) -> Path:
    """
    Return the persistent completion-record path for one stage.

    Resolving the path is side-effect free and does not create the stage
    working directory.
    """

    return working_dir / _COMPLETION_FILENAME


# =========================================================
# Persistence
# =========================================================


def write_stage_completion(
    working_dir: Path,
    completion: StageCompletion,
) -> None:
    """
    Persist one successful stage completion record.

    The stage working directory must already exist. Workspace creation is
    owned by execution rather than completion persistence.

    New completion records are always written using the current completion
    schema.
    """

    if not working_dir.is_dir():
        raise FileNotFoundError(f"Stage working directory does not exist: {working_dir}")

    fingerprint: dict[str, str] | None

    if completion.fingerprint is None:
        fingerprint = None
    else:
        fingerprint = {
            "algorithm": completion.fingerprint.algorithm,
            "value": completion.fingerprint.value,
        }

    data = {
        "schema_version": _COMPLETION_SCHEMA_VERSION,
        "artifact_id": completion.artifact_id,
        "model_name": completion.model_name,
        "realization": completion.realization,
        "stage_name": completion.stage_name,
        "products": list(
            completion.products,
        ),
        "fingerprint": fingerprint,
    }

    completion_path(
        working_dir,
    ).write_text(
        json.dumps(
            data,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_stage_completion(
    working_dir: Path,
) -> StageCompletion | None:
    """
    Read persistent completion metadata for one stage.

    Return None when no completion record exists.

    Schema version 1 records are accepted with fingerprint=None.

    Schema version 2 records restore their persisted fingerprint provenance.

    Raise ValueError when a record exists but cannot be interpreted as a
    supported completion schema.
    """

    path = completion_path(
        working_dir,
    )

    if not path.exists():
        return None

    try:
        raw = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError(f"Invalid stage completion metadata: {path}") from exc

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(f"Invalid stage completion metadata: {path}")

    data = cast(
        dict[str, object],
        raw,
    )

    schema_version = data.get(
        "schema_version",
    )

    if schema_version not in _SUPPORTED_COMPLETION_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported stage completion schema {schema_version!r} in {path}")

    artifact_id = _required_string(
        data,
        "artifact_id",
        path,
    )

    model_name = _required_string(
        data,
        "model_name",
        path,
    )

    realization = _required_string(
        data,
        "realization",
        path,
    )

    stage_name = _required_string(
        data,
        "stage_name",
        path,
    )

    products = _required_products(
        data,
        path,
    )

    if schema_version == 1:
        fingerprint = None
    else:
        fingerprint = _optional_fingerprint(
            data,
            path,
        )

    return StageCompletion(
        artifact_id=artifact_id,
        model_name=model_name,
        realization=realization,
        stage_name=stage_name,
        products=products,
        fingerprint=fingerprint,
    )


# =========================================================
# Validation
# =========================================================


def _required_string(
    data: dict[str, object],
    field: str,
    path: Path,
) -> str:
    """
    Read one required non-empty string field.
    """

    value = data.get(
        field,
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(f"Invalid {field!r} in stage completion metadata: {path}")

    return value


def _required_products(
    data: dict[str, object],
    path: Path,
) -> tuple[str, ...]:
    """
    Read the required logical product identity collection.
    """

    value = data.get(
        "products",
    )

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(f"Invalid 'products' in stage completion metadata: {path}")

    products: list[str] = []

    for product in value:
        if (
            not isinstance(
                product,
                str,
            )
            or not product
        ):
            raise ValueError(f"Invalid 'products' in stage completion metadata: {path}")

        products.append(
            product,
        )

    return tuple(
        products,
    )


def _optional_fingerprint(
    data: dict[str, object],
    path: Path,
) -> ProductFingerprint | None:
    """
    Read optional schema-version-2 fingerprint provenance.

    None explicitly represents missing provenance. Any non-None value must
    contain non-empty algorithm and value strings.
    """

    value = data.get(
        "fingerprint",
    )

    if value is None:
        return None

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(f"Invalid 'fingerprint' in stage completion metadata: {path}")

    fingerprint_data = cast(
        dict[str, object],
        value,
    )

    algorithm = fingerprint_data.get(
        "algorithm",
    )

    fingerprint_value = fingerprint_data.get(
        "value",
    )

    if (
        not isinstance(
            algorithm,
            str,
        )
        or not algorithm
        or not isinstance(
            fingerprint_value,
            str,
        )
        or not fingerprint_value
    ):
        raise ValueError(f"Invalid 'fingerprint' in stage completion metadata: {path}")

    return ProductFingerprint(
        algorithm=algorithm,
        value=fingerprint_value,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "StageCompletion",
    "completion_path",
    "read_stage_completion",
    "write_stage_completion",
]
