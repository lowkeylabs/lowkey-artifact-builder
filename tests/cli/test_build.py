"""
Tests for the artifact build command.
"""
# File: tests/cli/test_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import pytest
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


def test_build_without_variant_selects_default(
    monkeypatch,
) -> None:
    """
    A normal build with no Variant option builds only the Artifact's
    ordinary default Variant.
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
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "default",
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


def test_build_dry_run_without_variant_selects_default(
    monkeypatch,
) -> None:
    """
    A normal dry run plans only the Artifact's ordinary default Variant.
    """

    plan = object()

    selections: list[str | None] = []
    prepared: list[object] = []
    displayed: list[object] = []

    def create_plans(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ):
        selections.append(realization)
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
    assert selections == ["default"]
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
    An explicit default Variant selects the Artifact's default Variant.
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
        "--variant",
        "default",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "default",
        ),
    ]


def test_build_dry_run_explicit_default_variant_selects_default(
    monkeypatch,
) -> None:
    """
    An explicit default Variant dry-run plans the Artifact's default Variant.
    """

    plan = object()

    selections: list[str | None] = []

    def create_plans(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ):
        selections.append(realization)
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
    assert selections == ["default"]


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


def test_parse_variant_reference_accepts_bare_variant() -> None:
    """
    A bare Variant reference contains only its local Variant name.
    """

    assert cmd_build._parse_variant_reference("default") == (
        None,
        "default",
    )


def test_parse_variant_reference_accepts_qualified_variant() -> None:
    """
    A qualified Variant reference identifies its Model and local name.
    """

    assert cmd_build._parse_variant_reference("shape.ornament") == (
        "shape",
        "ornament",
    )


def test_parse_variant_reference_rejects_malformed_variant() -> None:
    """
    A Variant reference must be either a local name or model.local-name.
    """

    for reference in (
        "",
        ".ornament",
        "shape.",
        "shape.ornament.extra",
    ):
        with pytest.raises(
            click.UsageError,
            match="Invalid Variant",
        ):
            cmd_build._parse_variant_reference(reference)


def test_build_parses_bare_variant_before_execution(
    monkeypatch,
) -> None:
    """
    Normal build selection parses a bare Variant reference before
    forwarding its local name to the engine.
    """

    parsed: list[str] = []
    executed: list[tuple[str, str | None]] = []

    def parse_variant(reference: str) -> tuple[str | None, str]:
        parsed.append(reference)
        return (
            None,
            "parsed-variant",
        )

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
        "_parse_variant_reference",
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
            "parsed-variant",
        )
    ]


def test_build_dry_run_parses_bare_variant_before_planning(
    monkeypatch,
) -> None:
    """
    Dry-run uses the same bare Variant normalization as execution.
    """

    parsed: list[str] = []
    planned: list[tuple[str, str | None]] = []

    def parse_variant(reference: str) -> tuple[str | None, str]:
        parsed.append(reference)
        return (
            None,
            "parsed-variant",
        )

    def create_plans(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> tuple:
        planned.append(
            (
                artifact_id,
                realization,
            )
        )
        return ()

    monkeypatch.setattr(
        cmd_build,
        "_parse_variant_reference",
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
            "parsed-variant",
        )
    ]
