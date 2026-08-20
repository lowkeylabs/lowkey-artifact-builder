"""
Artifact build execution.

This module executes concrete artifact build plans.

Build planning is performed separately by the planning subsystem.
Execution consumes an already-resolved BuildPlan and performs the
declared workflow stages.

Stage execution is not yet implemented.
"""

from __future__ import annotations

from .plan import (
    BuildPlan,
)

# =========================================================
# Errors
# =========================================================


class BuildError(RuntimeError):
    """
    Raised when an artifact build cannot be completed.
    """


# =========================================================
# Public interface
# =========================================================


def execute_build(
    plan: BuildPlan,
) -> None:
    """
    Execute an artifact build plan.

    Stage execution is not yet implemented.
    """

    raise BuildError(f"Build execution for artifact {plan.artifact_id!r} is not yet implemented.")


__all__ = [
    "BuildError",
    "execute_build",
]
