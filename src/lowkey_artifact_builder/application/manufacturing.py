"""
Reusable manufacturing inspection.

Manufacturing inspection answers operator-oriented questions about an
Artifact without executing manufacturing work:

    What Realizations can be manufactured?
    Which are built-in versus Artifact-authored?
    Is each manufacturing Product current, stale, or not built?
    Is an operator-accessible published 3MF available?

This module composes existing configuration, planning, and persistent
Product-state capabilities. It does not reconstruct those semantics.

Inspection is read-only. It may construct BuildPlans and inspect persistent
Product state, but it does not execute stages, publish Products, repair
workspace state, or otherwise mutate the Artifact.
"""

# File: src/lowkey_artifact_builder/application/manufacturing.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.config import (
    ConfigError,
    get_realization_names,
    load_artifact_config,
    realization_3mf_filename,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    ProductState,
    create_build_plans,
    plan_dependency_build,
)

# =========================================================
# Operator-facing manufacturing state
# =========================================================


class ManufacturingState(StrEnum):
    """
    Operator-facing state of one Realization's manufacturing Product.

    NOT_BUILT
        No valid completed manufacturing Product is available.

    STALE
        A valid completed manufacturing Product exists but does not
        represent the current build context.

    CURRENT
        A valid completed manufacturing Product represents the current
        build context.
    """

    NOT_BUILT = "not built"
    STALE = "stale"
    CURRENT = "current"


class RealizationType(StrEnum):
    """
    Origin of one effective Artifact Realization.

    BUILT_IN
        A canonical Realization synthesized from a registered Model Variant.

    CUSTOM
        An additional Realization explicitly authored by the Artifact.
    """

    BUILT_IN = "built-in"
    CUSTOM = "custom"


# =========================================================
# Structured application results
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class RealizationManufacturingStatus:
    """
    Manufacturing status for one effective Artifact Realization.

    realization
        Artifact Realization identity.

    realization_type
        Whether the Realization is canonical/built-in or additionally
        authored by the Artifact.

    state
        Operator-facing manufacturing currency.

    product
        Operator-accessible published 3MF when one currently exists.
        Product availability is independent of manufacturing currency.
    """

    realization: str
    realization_type: RealizationType
    state: ManufacturingState
    product: Path | None


@dataclass(
    frozen=True,
    slots=True,
)
class ArtifactManufacturingStatus:
    """
    Manufacturing status for one Artifact.

    Realizations are returned in authoritative configuration discovery
    order.
    """

    artifact_id: str
    realizations: tuple[
        RealizationManufacturingStatus,
        ...,
    ]


# =========================================================
# Realization classification
# =========================================================


def _authored_realization_names(
    configuration: dict[str, Any],
) -> frozenset[str]:
    """
    Return Realization names explicitly authored by the Artifact.

    Canonical Realizations may appear in artifact.toml when customized.
    Their presence in authored configuration therefore does not by itself
    make them custom.

    This helper returns authored names only. Canonical identity is resolved
    separately from registered Variant identity.
    """

    authored = configuration.get(
        "realizations",
        {},
    )

    if not isinstance(
        authored,
        dict,
    ):
        raise ConfigError("The [realizations] section in artifact.toml must be a TOML table.")

    return frozenset(
        authored,
    )


def _canonical_realization_names(
    artifact_id: str,
    realization_names: tuple[str, ...],
    *,
    project_root: Path,
) -> frozenset[str]:
    """
    Return effective Realizations that are canonical Variant applications.

    A canonical Realization uses the established ``model_variant`` identity.
    Planning remains authoritative for resolving each effective Realization
    to its Model and Variant.

    An Artifact-authored customization of a canonical Realization therefore
    remains built-in, while an additional named application of a Variant is
    custom.
    """

    canonical: set[str] = set()

    for realization_name in realization_names:
        plans = create_build_plans(
            artifact_id,
            realization=realization_name,
            project_root=project_root,
        )

        if len(plans) != 1:
            raise ConfigError(
                f"Realization {realization_name!r} for Artifact "
                f"{artifact_id!r} resolved to {len(plans)} build plans."
            )

        plan = plans[0]

        variant = plan.resolver(
            "variant",
        )

        if not isinstance(
            variant,
            str,
        ):
            raise ConfigError(
                f"Variant for Realization {realization_name!r} "
                f"of Artifact {artifact_id!r} must resolve to a string."
            )

        canonical_name = f"{plan.model_name}_{variant}"

        if realization_name == canonical_name:
            canonical.add(
                realization_name,
            )

    return frozenset(
        canonical,
    )


# =========================================================
# Manufacturing Product state
# =========================================================


def _package_stage_state(
    execution_plan: ExecutionPlan,
) -> tuple[ProductState, ...] | None:
    """
    Return persistent Product states for the package Stage.

    A Realization without a package Stage has no normal manufacturing 3MF
    represented by this inspection surface.
    """

    for stage in execution_plan.stages:
        if stage.stage_name == "package":
            return stage.product_states

    return None


def _manufacturing_state(
    execution_plan: ExecutionPlan,
) -> ManufacturingState:
    """
    Summarize package Product state for operator presentation.

    CURRENT requires every declared package Product to be CURRENT.

    STALE means at least one valid completed package Product exists but is
    no longer current.

    All other engine states are summarized as NOT_BUILT because no valid
    current-or-stale manufacturing Product is available for operator use.
    """

    states = _package_stage_state(
        execution_plan,
    )

    if not states:
        return ManufacturingState.NOT_BUILT

    if all(state is ProductState.CURRENT for state in states):
        return ManufacturingState.CURRENT

    if any(state is ProductState.STALE for state in states):
        return ManufacturingState.STALE

    return ManufacturingState.NOT_BUILT


def _published_product(
    *,
    artifact_dir: Path,
    realization: str,
) -> Path | None:
    """
    Return the accessible published 3MF when it exists.

    Publication existence is deliberately independent of canonical Product
    state. A stale publication remains visible, while a missing publication
    does not make a current canonical Product stale.

    Inspection never restores a missing publication.
    """

    published = artifact_dir / realization_3mf_filename(
        realization,
    )

    if not published.is_file():
        return None

    return published


# =========================================================
# Realization inspection
# =========================================================


def _inspect_realization(
    artifact_id: str,
    realization: str,
    *,
    realization_type: RealizationType,
    project_root: Path,
) -> RealizationManufacturingStatus:
    """
    Inspect one effective Artifact Realization without executing it.
    """

    plans = create_build_plans(
        artifact_id,
        realization=realization,
        project_root=project_root,
    )

    if len(plans) != 1:
        raise ConfigError(
            f"Realization {realization!r} for Artifact "
            f"{artifact_id!r} resolved to {len(plans)} build plans."
        )

    plan: BuildPlan = plans[0]

    execution_plan = plan_dependency_build(
        plan,
    )

    return RealizationManufacturingStatus(
        realization=realization,
        realization_type=realization_type,
        state=_manufacturing_state(
            execution_plan,
        ),
        product=_published_product(
            artifact_dir=plan.artifact_dir,
            realization=realization,
        ),
    )


# =========================================================
# Public inspection operation
# =========================================================


def inspect_artifact_manufacturing(
    artifact_id: str,
    *,
    realization: str | None = None,
    project_root: Path | None = None,
) -> ArtifactManufacturingStatus:
    """
    Inspect manufacturing state for one Artifact.

    Without an explicit Realization, every effective canonical and custom
    Realization is inspected.

    With an explicit Realization, exactly that Realization is inspected.
    Explicit selection asserts that the Realization exists.

    Discovery is delegated to Artifact configuration. Persistent Product
    currency is delegated to incremental planning. This operation does not
    execute manufacturing work or repair publication state.
    """

    root = project_root if project_root is not None else Path.cwd()

    configuration = load_artifact_config(
        artifact_id,
        project_root=root,
    )

    if not configuration:
        raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

    realization_names = tuple(
        get_realization_names(
            artifact_id,
            project_root=root,
        )
    )

    if realization is not None:
        if realization not in realization_names:
            raise ConfigError(
                f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
            )

        selected_names = (realization,)

    else:
        selected_names = realization_names

    authored_names = _authored_realization_names(
        configuration,
    )

    canonical_names = _canonical_realization_names(
        artifact_id,
        realization_names,
        project_root=root,
    )

    statuses: list[RealizationManufacturingStatus] = []

    for realization_name in selected_names:
        # Canonical identity wins over authored presence. An operator may
        # customize shape_ornament in artifact.toml without converting that
        # canonical Realization into a custom Realization.
        if realization_name in canonical_names:
            realization_type = RealizationType.BUILT_IN

        elif realization_name in authored_names:
            realization_type = RealizationType.CUSTOM

        else:
            # Effective non-canonical Realizations should normally originate
            # from Artifact-authored configuration. Treat anything else as
            # inconsistent persistent/configuration state rather than guessing
            # its operator-facing type.
            raise ConfigError(
                f"Realization {realization_name!r} for Artifact "
                f"{artifact_id!r} is neither canonical nor explicitly authored."
            )

        statuses.append(
            _inspect_realization(
                artifact_id,
                realization_name,
                realization_type=realization_type,
                project_root=root,
            )
        )

    return ArtifactManufacturingStatus(
        artifact_id=artifact_id,
        realizations=tuple(
            statuses,
        ),
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ArtifactManufacturingStatus",
    "ManufacturingState",
    "RealizationManufacturingStatus",
    "RealizationType",
    "inspect_artifact_manufacturing",
]
