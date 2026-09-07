"""
Tests for the artifact build command.
"""

# File: tests/cli/test_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import ConfigError

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact build command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "build",
            *args,
        ],
    )


# =========================================================
# Build discovery
# =========================================================


def test_build_without_variant_discovers_available_variants(
    monkeypatch,
) -> None:
    """
    An unqualified Artifact build displays every available qualified Variant.

    Discovery does not imply execution.
    """

    discovered: list[str] = []
    displayed: list[
        tuple[
            str,
            tuple[str, ...],
        ]
    ] = []
    executed: list[str] = []

    variants = (
        "artwork.default",
        "shape.default",
        "shape.ornament",
    )

    def get_available_variants(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[str, ...]:
        discovered.append(artifact_id)
        return variants

    def display_available_variants(
        artifact_id: str,
        available_variants: tuple[str, ...],
    ) -> None:
        displayed.append(
            (
                artifact_id,
                available_variants,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "get_available_variant_names",
        get_available_variants,
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_available_variants",
        display_available_variants,
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        lambda artifact_id, **kwargs: executed.append(artifact_id),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert discovered == ["skippy"]
    assert displayed == [
        (
            "skippy",
            variants,
        )
    ]
    assert executed == []


def test_build_without_variant_discovers_each_artifact_in_argument_order(
    monkeypatch,
) -> None:
    """
    Unqualified multi-Artifact builds perform discovery in argument order.
    """

    variants_by_artifact = {
        "skippy": (
            "artwork.default",
            "shape.default",
            "shape.ornament",
        ),
        "scooby": (
            "artwork.default",
            "shape.default",
            "shape.ornament",
        ),
    }

    displayed: list[
        tuple[
            str,
            tuple[str, ...],
        ]
    ] = []
    executed: list[str] = []

    monkeypatch.setattr(
        cmd_build,
        "get_available_variant_names",
        lambda artifact_id, *, project_root: variants_by_artifact[artifact_id],
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_available_variants",
        lambda artifact_id, variants: displayed.append(
            (
                artifact_id,
                variants,
            )
        ),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        lambda artifact_id, **kwargs: executed.append(artifact_id),
    )

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code == 0
    assert displayed == [
        (
            "skippy",
            variants_by_artifact["skippy"],
        ),
        (
            "scooby",
            variants_by_artifact["scooby"],
        ),
    ]
    assert executed == []


def test_build_dry_run_without_variant_is_discovery_only(
    monkeypatch,
) -> None:
    """
    An unqualified dry-run remains discovery-only.

    Discovery does not manufacture BuildPlans or prepare execution state.
    """

    variants = (
        "artwork.default",
        "shape.default",
        "shape.ornament",
    )

    displayed_variants: list[
        tuple[
            str,
            tuple[str, ...],
        ]
    ] = []
    planned: list[str] = []
    prepared: list[object] = []
    displayed_plans: list[object] = []

    monkeypatch.setattr(
        cmd_build,
        "get_available_variant_names",
        lambda artifact_id, *, project_root: variants,
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_available_variants",
        lambda artifact_id, available_variants: displayed_variants.append(
            (
                artifact_id,
                available_variants,
            )
        ),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, **kwargs: planned.append(artifact_id) or (),
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: prepared.append(plan),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed_plans.append,
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert displayed_variants == [
        (
            "skippy",
            variants,
        )
    ]
    assert planned == []
    assert prepared == []
    assert displayed_plans == []


# =========================================================
# Build execution
# =========================================================


def test_build_does_not_create_artifact_build_plans(
    monkeypatch,
) -> None:
    """
    Explicit normal execution leaves artifact BuildPlan creation to the
    engine execution boundary.
    """

    executed: list[
        tuple[
            str,
            str | None,
            str | None,
        ]
    ] = []

    def unexpected_planning(
        artifact_id: str,
        *,
        project_root: Path,
        **kwargs,
    ):
        raise AssertionError("normal CLI execution created artifact build plans")

    def execute_artifact(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        executed.append(
            (
                artifact_id,
                model_name,
                variant_name,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        unexpected_planning,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 0
    assert executed == [
        (
            "skippy",
            "shape",
            "ornament",
        )
    ]


def test_build_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit Artifact execution receives the current project root.
    """

    roots: list[Path] = []

    def execute_artifact(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        roots.append(project_root)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 0
    assert roots == [tmp_path]


# =========================================================
# Dry run
# =========================================================


def test_build_dry_run_prepares_plan_before_display(
    monkeypatch,
) -> None:
    """
    An explicitly selected dry run validates persistent execution state
    before displaying a plan.
    """

    plan = object()

    operations: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, model_name=None, variant_name=None, project_root: (plan,),
    )

    def prepare(
        candidate: object,
    ) -> object:
        operations.append(
            (
                "prepare",
                candidate,
            )
        )

        return object()

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        prepare,
        raising=False,
    )

    def display(
        candidate: object,
    ) -> None:
        operations.append(
            (
                "display",
                candidate,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        display,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert operations == [
        (
            "prepare",
            plan,
        ),
        (
            "display",
            plan,
        ),
    ]


def test_build_dry_run_does_not_execute(
    monkeypatch,
) -> None:
    """
    An explicitly selected dry run performs validated preparation and
    display but no execution.
    """

    plans = (
        object(),
        object(),
    )

    executed: list[str] = []

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, model_name=None, variant_name=None, project_root: plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: object(),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        lambda plan: None,
    )

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert executed == []


# =========================================================
# Multiple artifacts
# =========================================================


def test_build_multiple_artifacts_in_argument_order(
    monkeypatch,
) -> None:
    """
    Explicit multi-Artifact execution is delegated to the engine in
    argument order.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "scooby",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 0

    assert executed == [
        "skippy",
        "scooby",
    ]


def test_build_multiple_artifacts_dry_run_in_argument_order(
    monkeypatch,
) -> None:
    """
    Explicit multi-Artifact dry-run plans are prepared and displayed
    artifact-by-artifact in order.
    """

    skippy_first = object()
    skippy_second = object()
    scooby = object()

    plans_by_artifact = {
        "skippy": (
            skippy_first,
            skippy_second,
        ),
        "scooby": (scooby,),
    }

    operations: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, model_name=None, variant_name=None, project_root: plans_by_artifact[
            artifact_id
        ],
    )

    def prepare(
        plan: object,
    ) -> object:
        operations.append(
            (
                "prepare",
                plan,
            )
        )

        return object()

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        prepare,
        raising=False,
    )

    def display(
        plan: object,
    ) -> None:
        operations.append(
            (
                "display",
                plan,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        display,
    )

    result = _invoke(
        "skippy",
        "scooby",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert operations == [
        (
            "prepare",
            skippy_first,
        ),
        (
            "display",
            skippy_first,
        ),
        (
            "prepare",
            skippy_second,
        ),
        (
            "display",
            skippy_second,
        ),
        (
            "prepare",
            scooby,
        ),
        (
            "display",
            scooby,
        ),
    ]


# =========================================================
# Errors
# =========================================================


def test_build_plan_error_is_reported(
    monkeypatch,
) -> None:
    """
    Explicit dry-run BuildPlan errors are presented as Click command errors.
    """

    def create_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        project_root: Path,
    ):
        raise cmd_build.BuildPlanError("cannot create build plan")

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "cannot create build plan" in result.output


def test_build_dry_run_configuration_error_is_reported_before_display(
    monkeypatch,
) -> None:
    """
    Explicit dry-run configuration validation failures are presented as
    Click command errors before the invalid plan is displayed.
    """

    plan = object()

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, model_name=None, variant_name=None, project_root: (plan,),
    )

    def prepare(
        candidate: object,
    ) -> object:
        assert candidate is plan

        raise ConfigError(
            "required configuration is invalid",
        )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        prepare,
        raising=False,
    )

    displayed: list[object] = []

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "required configuration is invalid" in result.output
    assert displayed == []


def test_build_execution_error_is_reported(
    monkeypatch,
) -> None:
    """
    Explicit Artifact build errors are presented as Click command errors.
    """

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        raise cmd_build.BuildError("cannot execute build")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code != 0
    assert "cannot execute build" in result.output


def test_build_rejects_realization_for_normal_build(
    monkeypatch,
) -> None:
    """
    Artifact Realization is not an independent selector for normal builds.

    Normal reusable build selection is expressed through Variant.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "alternate",
    )

    assert result.exit_code != 0
    assert "--realization requires --stage" in result.output
    assert executed == []


# =========================================================
# Independent stage execution
# =========================================================


def test_build_stage_accepts_selected_realization(
    monkeypatch,
) -> None:
    """
    Independent Stage execution may select an Artifact Realization.
    """

    executed: list[tuple[str, str, str | None]] = []

    def execute_stage(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                stage_name,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute_stage,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "structure",
        "--realization",
        "alternate",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "structure",
            "alternate",
        )
    ]


# =========================================================
# Explicit Variant selection
# =========================================================


def test_build_explicit_default_variant_selects_default(
    monkeypatch,
) -> None:
    """
    An explicit default Variant selects the Model's default Variant
    without selecting an Artifact Realization.
    """

    executed: list[
        tuple[
            str,
            str | None,
            str | None,
        ]
    ] = []

    def execute_artifact(
        artifact_id: str,
        *,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                variant_name,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "default",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "default",
            None,
        )
    ]


def test_build_dry_run_explicit_default_variant_selects_default(
    monkeypatch,
) -> None:
    """
    An explicit default Variant dry-run selects the Model's default
    Variant without selecting an Artifact Realization.
    """

    plan = object()

    selections: list[
        tuple[
            str | None,
            str | None,
        ]
    ] = []

    def create_plans(
        artifact_id: str,
        *,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path,
    ):
        selections.append(
            (
                variant_name,
                realization,
            )
        )

        return (plan,)

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda candidate: object(),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        lambda candidate: None,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "default",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert selections == [
        (
            "default",
            None,
        )
    ]


def test_build_parses_bare_variant_before_execution(
    monkeypatch,
) -> None:
    """
    Normal build selection parses a bare Variant reference before
    forwarding its local name to the engine as Variant selection.
    """

    parsed: list[str] = []
    executed: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
        ]
    ] = []

    def parse_variant(reference: str) -> tuple[str | None, str]:
        parsed.append(reference)
        return (
            None,
            "parsed-variant",
        )

    def execute_artifact(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "parse_variant_reference",
        parse_variant,
    )
    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "default",
    )

    assert result.exit_code == 0
    assert parsed == ["default"]
    assert executed == [
        (
            "skippy",
            None,
            "parsed-variant",
            None,
        )
    ]


def test_build_dry_run_parses_bare_variant_before_planning(
    monkeypatch,
) -> None:
    """
    Dry-run uses the same bare Variant normalization as execution.
    """

    parsed: list[str] = []
    planned: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
        ]
    ] = []

    def parse_variant(reference: str) -> tuple[str | None, str]:
        parsed.append(reference)
        return (
            None,
            "parsed-variant",
        )

    def create_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path,
    ) -> tuple:
        planned.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
            )
        )
        return ()

    monkeypatch.setattr(
        cmd_build,
        "parse_variant_reference",
        parse_variant,
    )
    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "default",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert parsed == ["default"]
    assert planned == [
        (
            "skippy",
            None,
            "parsed-variant",
            None,
        )
    ]


def test_build_qualified_variant_selects_model_and_local_variant(
    monkeypatch,
) -> None:
    """
    A qualified Variant selects its Model and local Variant name for
    execution without selecting an Artifact Realization.
    """

    executed: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
        ]
    ] = []

    def execute_artifact(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "shape",
            "ornament",
            None,
        )
    ]


def test_build_dry_run_qualified_variant_selects_model_and_local_variant(
    monkeypatch,
) -> None:
    """
    A qualified Variant selects the same Model and local Variant name
    during dry-run planning without selecting an Artifact Realization.
    """

    planned: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
        ]
    ] = []

    def create_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path,
    ) -> tuple:
        planned.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
            )
        )

        return ()

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert planned == [
        (
            "skippy",
            "shape",
            "ornament",
            None,
        )
    ]


# =========================================================
# All-Variant selection
# =========================================================


def test_build_rejects_variant_with_all_variants(
    monkeypatch,
) -> None:
    """
    One Variant and all Variants are mutually exclusive selections.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
        **kwargs,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
        "--all-variants",
    )

    assert result.exit_code != 0
    assert "--variant and --all-variants cannot be used together" in result.output
    assert executed == []


def test_build_all_variants_selects_all_variants_before_execution(
    monkeypatch,
) -> None:
    """
    Normal build forwards all-Variant selection without manufacturing
    Model or Variant selection.
    """

    selected: list[
        tuple[
            tuple[str, ...],
            str | None,
            str | None,
            bool,
            bool,
        ]
    ] = []

    def execute_build(
        artifact_ids: tuple[str, ...],
        *,
        model_name: str | None,
        variant_name: str | None,
        all_variants: bool,
        dry_run: bool,
    ) -> None:
        selected.append(
            (
                artifact_ids,
                model_name,
                variant_name,
                all_variants,
                dry_run,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "_execute_build",
        execute_build,
    )

    result = _invoke(
        "skippy",
        "--all-variants",
    )

    assert result.exit_code == 0
    assert selected == [
        (
            ("skippy",),
            None,
            None,
            True,
            False,
        )
    ]


def test_build_all_variants_selects_all_variants_for_dry_run(
    monkeypatch,
) -> None:
    """
    Dry-run preserves all-Variant selection at the normal build boundary.
    """

    selected: list[
        tuple[
            tuple[str, ...],
            str | None,
            str | None,
            bool,
            bool,
        ]
    ] = []

    def execute_build(
        artifact_ids: tuple[str, ...],
        *,
        model_name: str | None,
        variant_name: str | None,
        all_variants: bool,
        dry_run: bool,
    ) -> None:
        selected.append(
            (
                artifact_ids,
                model_name,
                variant_name,
                all_variants,
                dry_run,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "_execute_build",
        execute_build,
    )

    result = _invoke(
        "skippy",
        "--all-variants",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert selected == [
        (
            ("skippy",),
            None,
            None,
            True,
            True,
        )
    ]


def test_build_all_variants_delegates_all_variants_to_artifact_build(
    monkeypatch,
) -> None:
    """
    Normal all-Variant execution delegates Variant enumeration to the
    Artifact-build engine boundary.
    """

    requested: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            bool,
        ]
    ] = []

    def execute_artifact(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        all_variants: bool = False,
        project_root: Path,
        event_sink=None,
    ) -> None:
        requested.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
                all_variants,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--all-variants",
    )

    assert result.exit_code == 0
    assert requested == [
        (
            "skippy",
            None,
            None,
            None,
            True,
        )
    ]


def test_build_all_variants_dry_run_delegates_selection_to_artifact_planning(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    All-Variant dry-run delegates Variant enumeration to the Artifact-level
    engine planning boundary.

    The CLI does not enumerate Model Variants itself.
    """

    first_plan = object()
    second_plan = object()

    requested: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            bool,
            Path,
        ]
    ] = []
    prepared: list[object] = []
    displayed: list[object] = []

    def create_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        all_variants: bool = False,
        project_root: Path,
    ) -> tuple[object, ...]:
        requested.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
                all_variants,
                project_root,
            )
        )

        return (
            first_plan,
            second_plan,
        )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: prepared.append(plan),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    result = _invoke(
        "example",
        "--all-variants",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert requested == [
        (
            "example",
            None,
            None,
            None,
            True,
            tmp_path,
        )
    ]

    assert prepared == [
        first_plan,
        second_plan,
    ]

    assert displayed == [
        first_plan,
        second_plan,
    ]


# =========================================================
# Planning integration
# =========================================================


def test_build_dry_run_qualified_variant_uses_effective_variant_configuration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Qualified Variant dry-run uses the selected Model and Variant's
    effective configuration through the real planning boundary.
    """

    from lowkey_artifact_builder.config import write_artifact_config

    write_artifact_config(
        "example",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    plans = []

    def display(plan) -> None:
        plans.append(plan)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        display,
    )

    result = _invoke(
        "example",
        "--variant",
        "shape.ornament",
        "--dry-run",
    )

    assert result.exit_code == 0, result.output
    assert plans

    for plan in plans:
        assert plan.model_name == "shape"
        assert plan.realization_name == "ornament"
        assert plan.resolver("variant") == "ornament"
        assert plan.resolver("shape_outer_ridge_width") == 2.0
        assert plan.resolver.source("shape_outer_ridge_width") == "variant 'ornament'"


def test_build_all_variants_dry_run_selects_all_default_realizations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    All-Variant dry-run plans every Variant owned by the Artifact's Model
    through the real Artifact-planning boundary.
    """

    from lowkey_artifact_builder.config import write_artifact_config

    write_artifact_config(
        "example",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    displayed = []

    def display(plan) -> None:
        displayed.append(
            (
                plan.model_name,
                plan.realization_name,
                plan.resolver("variant"),
                plan.resolver("shape_outer_ridge_width"),
                plan.resolver.source("shape_outer_ridge_width"),
            )
        )

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        display,
    )

    result = _invoke(
        "example",
        "--all-variants",
        "--dry-run",
    )

    assert result.exit_code == 0, result.output

    assert displayed == [
        (
            "shape",
            "shape_default",
            "default",
            0.0,
            "model",
        ),
        (
            "shape",
            "shape_ornament",
            "ornament",
            2.0,
            "variant 'ornament'",
        ),
    ]
