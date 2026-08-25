"""
Artifact build subsystem.

The build subsystem materializes configured artifact models into
concrete build plans and executes those plans.

Planning is intentionally separate from execution so build workflows
may be inspected and validated without modifying filesystem products.

Execution owns artifact workspace creation, external input
materialization, stage dispatch, execution contexts, and verification
of declared products.

Independent stage execution uses the same resolved StageContext and
model-specific stage implementation boundary as graph-driven builds.
Stage input readiness may be validated independently before execution.

Structured execution events provide an optional, presentation-independent
observation boundary for build and stage execution.

Persistent completion metadata records successfully completed stage
realizations, their declared products, and optional build-context
fingerprint provenance.

Product evidence gathering combines filesystem materialization, completion
metadata, and fingerprint provenance into normalized persistent-product
evidence.

Product-state evaluation converts normalized persistent-product evidence
into semantic state independently of evidence gathering.

Persistent product freshness is proven by matching explicit fingerprint
evidence rather than inferred from filesystem presence or timestamps.
Build-context fingerprints are generated deterministically from operation
identity, relevant parameters, and upstream input fingerprints.

Build-plan fingerprint resolution derives required stage provenance from
resolved stage parameters and dependency fingerprints.

Execution product-state resolution adapts realized build-plan stages and
products to persistent product-state evaluation.

Execution planning combines realized build plans with resolved persistent
product states while remaining independent of direct filesystem inspection,
evidence gathering, and execution.

Persistent-state-aware execution planning composes execution product-state
resolution with execution-plan construction.

Execution plans preserve the complete realized workflow while identifying
the subset of stages that must execute for the current build context.
"""
# File: src/lowkey_artifact_builder/engine/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from .build import (
    BuildError,
    execute_artifact_stage,
    execute_build,
    execute_builds,
)
from .completion import (
    StageCompletion,
    completion_path,
    read_stage_completion,
    write_stage_completion,
)
from .context import (
    create_stage_context,
)
from .events import (
    EventSink,
    ExecutionEvent,
    ProductStateEvent,
    emit_event,
)
from .evidence import (
    PersistentProductStateResolver,
    create_product_state_resolver,
    gather_product_evidence,
)
from .execution import (
    ExecutionPlan,
    PlannedStageExecution,
    ProductStateResolver,
    create_execution_plan,
    plan_execution,
    stage_requires_execution,
)
from .execution_state import (
    ExecutionProductStateResolver,
    RequiredFingerprintResolver,
    create_execution_state_resolver,
)
from .fingerprint_plan import (
    create_required_fingerprints,
)
from .freshness import (
    ProductFingerprint,
    create_product_fingerprint,
    product_is_fresh,
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
from .stage import (
    StageExecutionError,
    StageInputError,
    execute_stage,
    validate_stage_inputs,
)
from .state import (
    ProductEvidence,
    ProductState,
    evaluate_product_state,
)

__all__ = [
    "BuildError",
    "BuildPlan",
    "BuildPlanError",
    "EventSink",
    "ExecutionEvent",
    "ExecutionPlan",
    "ExecutionProductStateResolver",
    "PersistentProductStateResolver",
    "PlannedInput",
    "PlannedProduct",
    "PlannedStage",
    "PlannedStageExecution",
    "ProductEvidence",
    "ProductFingerprint",
    "ProductState",
    "ProductStateEvent",
    "ProductStateResolver",
    "RequiredFingerprintResolver",
    "StageCompletion",
    "StageContext",
    "StageContextError",
    "StageExecutionError",
    "StageInputError",
    "completion_path",
    "create_build_plan",
    "create_build_plans",
    "create_execution_plan",
    "create_execution_state_resolver",
    "create_product_fingerprint",
    "create_product_state_resolver",
    "create_required_fingerprints",
    "create_stage_context",
    "emit_event",
    "evaluate_product_state",
    "execute_artifact_stage",
    "execute_build",
    "execute_builds",
    "execute_stage",
    "gather_product_evidence",
    "plan_execution",
    "product_is_fresh",
    "read_stage_completion",
    "stage_requires_execution",
    "validate_stage_inputs",
    "write_stage_completion",
]
