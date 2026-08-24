"""
Artifact build subsystem.

The build subsystem materializes configured artifact models into
concrete build plans and executes those plans.

Planning is intentionally separate from execution so build workflows
may be inspected and validated without modifying filesystem products.

Execution owns artifact workspace creation, external input
materialization, stage dispatch, execution contexts, and verification
of declared products.
"""

from .build import (
    BuildError,
    execute_build,
    execute_builds,
)
from .plan import (
    BuildPlanError,
    create_build_plan,
    create_build_plans,
)
from .specs import (
    BuildPlan,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
    StageContext,
    StageContextError,
)

__all__ = [
    "BuildError",
    "BuildPlan",
    "BuildPlanError",
    "PlannedInput",
    "PlannedProduct",
    "PlannedStage",
    "StageContext",
    "StageContextError",
    "create_build_plan",
    "create_build_plans",
    "execute_build",
    "execute_builds",
]
