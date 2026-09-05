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
# Build execution
# =========================================================


def test_build_without_variant_leaves_variant_selection_implicit(
    monkeypatch,
) -> None:
    """
    A normal build with no Variant option leaves Variant selection
    implicit so configuration resolution may select the default Variant.
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
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            None,
            None,
        ),
    ]


def test_build_does_not_create_build_plans(
    monkeypatch,
) -> None:
    """
    Normal execution leaves build-plan creation to the engine boundary.
    """

    def unexpected_planning(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ):
        raise AssertionError("normal CLI execution created build plans")

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        unexpected_planning,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        lambda artifact_id, *, realization=None, project_root, event_sink=None: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0


def test_build_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact execution receives the current project root.
    """

    roots: list[Path] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
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
    )

    assert result.exit_code == 0
    assert roots == [tmp_path]


# =========================================================
# Dry run
# =========================================================


def test_build_dry_run_without_variant_leaves_variant_selection_implicit(
    monkeypatch,
) -> None:
    """
    A normal dry run with no Variant option leaves Variant selection
    implicit so configuration resolution may select the default Variant.
    """

    plan = object()

    selections: list[
        tuple[
            str | None,
            str | None,
        ]
    ] = []
    prepared: list[object] = []
    displayed: list[object] = []

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
        "create_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda candidate: prepared.append(candidate),
        raising=False,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert selections == [
        (
            None,
            None,
        )
    ]
    assert prepared == [plan]
    assert displayed == [plan]


def test_build_dry_run_prepares_plan_before_display(
    monkeypatch,
) -> None:
    """
    A dry run validates persistent execution state before displaying a plan.
    """

    plan = object()

    operations: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, realization=None, project_root: (plan,),
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
    A dry run performs validated preparation and display but no execution.
    """

    plans = (
        object(),
        object(),
    )

    executed: list[str] = []

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, realization=None, project_root: plans,
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
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
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
    Multiple artifact IDs are delegated to the engine in argument order.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
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
    Dry-run plans are prepared and displayed artifact-by-artifact in order.
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
        "create_build_plans",
        lambda artifact_id, *, realization=None, project_root: plans_by_artifact[artifact_id],
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
    Dry-run build-plan errors are presented as Click command errors.
    """

    def create_plans(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ):
        raise cmd_build.BuildPlanError("cannot create build plan")

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        create_plans,
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "cannot create build plan" in result.output


def test_build_dry_run_configuration_error_is_reported_before_display(
    monkeypatch,
) -> None:
    """
    Dry-run configuration validation failures are presented as Click command
    errors before the invalid plan is displayed.
    """

    plan = object()

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, realization=None, project_root: (plan,),
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
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "required configuration is invalid" in result.output
    assert displayed == []


def test_build_execution_error_is_reported(
    monkeypatch,
) -> None:
    """
    Artifact build errors are presented as Click command errors.
    """

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
    ) -> None:
        raise cmd_build.BuildError("cannot execute build")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "cannot execute build" in result.output


def test_build_passes_selected_realization_to_engine(
    monkeypatch,
) -> None:
    """
    Normal artifact builds may select one public realization.
    """

    executed: list[tuple[str, str | None]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
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
        "--realization",
        "default",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "default",
        ),
    ]


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
        "create_build_plans",
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


def test_build_rejects_variant_with_realization(
    monkeypatch,
) -> None:
    """
    Variant and historical realization selection cannot independently
    select the same normal artifact build.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
        event_sink=None,
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
        "default",
        "--realization",
        "default",
    )

    assert result.exit_code != 0
    assert "--variant and --realization cannot be used together" in result.output
    assert executed == []


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
        "create_build_plans",
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
    A qualified Variant selects its Model and local Variant name for execution
    without selecting an Artifact Realization.
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
        "create_build_plans",
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
    Model, Variant, or Artifact Realization selection.
    """

    selected: list[
        tuple[
            tuple[str, ...],
            str | None,
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
        realization: str | None,
        all_variants: bool,
        dry_run: bool,
    ) -> None:
        selected.append(
            (
                artifact_ids,
                model_name,
                variant_name,
                realization,
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
        realization: str | None,
        all_variants: bool,
        dry_run: bool,
    ) -> None:
        selected.append(
            (
                artifact_ids,
                model_name,
                variant_name,
                realization,
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
    artifact-build engine boundary.
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


def test_build_without_all_variants_preserves_existing_execution_call_shape(
    monkeypatch,
) -> None:
    """
    Ordinary execution does not add an all-Variant selection argument.

    The existing artifact-build call shape remains unchanged when
    all-Variant selection was not requested.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            artifact_id,
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert executed == [
        "skippy",
    ]
