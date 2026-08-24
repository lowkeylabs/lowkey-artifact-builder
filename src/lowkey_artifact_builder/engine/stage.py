"""
Independent stage execution.

This module provides the common execution boundary for model-specific
stage implementations.

Both graph-driven artifact builds and explicit independent stage
execution converge on execute_stage(). The caller supplies a fully
resolved StageContext. This module does not perform build planning,
dependency traversal, configuration resolution, filesystem input
materialization, or StageContext construction.

A stage executes exactly once using the model and stage identity carried
by its StageContext.
"""
# File: src/lowkey_artifact_builder/engine/stage.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from lowkey_artifact_builder.engine.bootstrap import (
    build_stage_registry,
)
from lowkey_artifact_builder.engine.registry import (
    StageImplementationNotFoundError,
    StageRegistry,
)
from lowkey_artifact_builder.engine.specs import (
    StageContext,
)

# =========================================================
# Errors
# =========================================================


class StageExecutionError(RuntimeError):
    """
    Raised when an independently resolved stage cannot be executed.
    """


# =========================================================
# Public interface
# =========================================================


def execute_stage(
    context: StageContext,
) -> None:
    """
    Execute one fully resolved model-specific stage.

    The implementation is selected using the model and stage identity
    carried by StageContext.

    Execution occurs from context.working_dir. The caller's previous
    working directory is restored after execution, including when the
    stage fails.

    After successful implementation execution, every declared output in
    context.outputs must exist.

    This function executes exactly the supplied stage. It does not
    inspect model dependencies, execute prerequisite stages, perform
    build planning, materialize external inputs, or construct another
    StageContext.
    """

    registry = build_stage_registry()

    _execute_stage(
        context,
        registry,
    )

    _verify_products(
        context,
    )


# =========================================================
# Stage implementation execution
# =========================================================


def _execute_stage(
    context: StageContext,
    registry: StageRegistry,
) -> None:
    """
    Execute one model-specific stage implementation.

    The executable implementation is obtained from the completed stage
    registry using the model and stage names carried by StageContext.
    """

    try:
        implementation = registry.get(
            context.model_name,
            context.stage_name,
        )

    except StageImplementationNotFoundError as exc:
        raise StageExecutionError(
            f"No implementation is registered "
            f"for model "
            f"{context.model_name!r}, "
            f"stage "
            f"{context.stage_name!r}."
        ) from exc

    try:
        with _working_directory(
            context.working_dir,
        ):
            implementation(
                context,
            )

    except StageExecutionError:
        raise

    except Exception as exc:
        raise StageExecutionError(
            f"Stage "
            f"{context.stage_name!r} "
            f"failed for artifact "
            f"{context.artifact_id!r} "
            f"using model "
            f"{context.model_name!r}: "
            f"{exc}"
        ) from exc


# =========================================================
# Working directory
# =========================================================


@contextmanager
def _working_directory(
    path: Path,
) -> Iterator[None]:
    """
    Temporarily change the process working directory.

    The previous working directory is restored regardless of whether
    stage execution succeeds or raises an exception.
    """

    previous = Path.cwd()

    try:
        os.chdir(
            path,
        )

        yield

    finally:
        os.chdir(
            previous,
        )


# =========================================================
# Product verification
# =========================================================


def _verify_products(
    context: StageContext,
) -> None:
    """
    Verify that every declared stage product exists.

    Product contents and semantics remain model-specific and are not
    interpreted by the generic stage execution boundary.
    """

    missing = [
        (
            name,
            path,
        )
        for name, path in context.outputs.items()
        if not path.exists()
    ]

    if not missing:
        return

    details = ", ".join(f"{name!r} ({path})" for name, path in missing)

    raise StageExecutionError(
        f"Stage "
        f"{context.stage_name!r} "
        f"for artifact "
        f"{context.artifact_id!r} "
        f"did not produce declared product(s): "
        f"{details}."
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "StageExecutionError",
    "execute_stage",
]
