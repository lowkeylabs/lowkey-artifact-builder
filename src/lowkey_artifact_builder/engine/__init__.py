"""
Artifact build subsystem.

The build subsystem materializes configured artifact models into
concrete build plans and executes those plans.

Planning is intentionally separate from execution so build workflows
may be inspected and validated without modifying filesystem products.
"""

from .build import (
    BuildError,
    execute_build,
)
from .plan import (
    BuildPlan,
    BuildPlanError,
    PlannedProduct,
    PlannedStage,
    ResolvedParameter,
    create_build_plan,
)

__all__ = [
    "BuildError",
    "BuildPlan",
    "BuildPlanError",
    "PlannedProduct",
    "PlannedStage",
    "ResolvedParameter",
    "create_build_plan",
    "execute_build",
]
