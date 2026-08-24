"""Tests for lowkey-artifact-builder logging."""
# File: tests/test_logging.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import logging

import pytest

from lowkey_artifact_builder.logging_config import (
    DEFAULT_LEVEL,
    PROGRESS,
    SUCCESS,
    TRACE,
    ArtifactLogger,
    configure_logging,
    get_logger,
    resolve_log_level,
)

# =========================================================
# Custom levels
# =========================================================


def test_custom_level_names() -> None:
    """Custom logging levels have the expected names."""

    assert logging.getLevelName(TRACE) == "TRACE"
    assert logging.getLevelName(PROGRESS) == "PROGRESS"
    assert logging.getLevelName(SUCCESS) == "SUCCESS"


def test_custom_level_ordering() -> None:
    """Custom logging levels have the intended ordering."""

    assert TRACE < logging.DEBUG
    assert logging.INFO < PROGRESS
    assert PROGRESS < SUCCESS
    assert SUCCESS < logging.WARNING


# =========================================================
# Logger
# =========================================================


def test_get_logger_returns_artifact_logger() -> None:
    """get_logger returns the custom ArtifactLogger type."""

    logger = get_logger(
        "lowkey_artifact_builder.tests.logger",
    )

    assert isinstance(
        logger,
        ArtifactLogger,
    )


def test_logger_has_custom_methods() -> None:
    """Artifact loggers expose the custom logging methods."""

    logger = get_logger(
        "lowkey_artifact_builder.tests.methods",
    )

    assert callable(logger.trace)
    assert callable(logger.progress)
    assert callable(logger.success)


# =========================================================
# Level resolution
# =========================================================


def test_default_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default level is used when no override exists."""

    monkeypatch.delenv(
        "LOG_LEVEL",
        raising=False,
    )

    assert resolve_log_level() == DEFAULT_LEVEL


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("TRACE", TRACE),
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("PROGRESS", PROGRESS),
        ("SUCCESS", SUCCESS),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
    ],
)
def test_named_log_levels(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    expected: int,
) -> None:
    """Named logging levels resolve correctly."""

    monkeypatch.delenv(
        "LOG_LEVEL",
        raising=False,
    )

    assert resolve_log_level(name) == expected


def test_log_level_names_are_case_insensitive() -> None:
    """Logging level names are case-insensitive."""

    assert resolve_log_level("debug") == logging.DEBUG
    assert resolve_log_level("Progress") == PROGRESS
    assert resolve_log_level("success") == SUCCESS


def test_integer_log_level() -> None:
    """Numeric logging levels may be supplied directly."""

    assert resolve_log_level(17) == 17


def test_environment_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LOG_LEVEL overrides the default logging level."""

    monkeypatch.setenv(
        "LOG_LEVEL",
        "DEBUG",
    )

    assert resolve_log_level() == logging.DEBUG


def test_explicit_level_overrides_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit logging level takes precedence over LOG_LEVEL."""

    monkeypatch.setenv(
        "LOG_LEVEL",
        "DEBUG",
    )

    assert resolve_log_level("TRACE") == TRACE


def test_invalid_log_level() -> None:
    """An invalid logging level raises ValueError."""

    with pytest.raises(
        ValueError,
        match="Invalid log level",
    ):
        resolve_log_level("BOGUS")


# =========================================================
# Output routing
# =========================================================


def test_progress_writes_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """PROGRESS messages are written to stdout."""

    configure_logging(PROGRESS)

    logger = get_logger(
        "lowkey_artifact_builder.tests.progress",
    )

    logger.progress("Building artwork")

    captured = capsys.readouterr()

    assert captured.out == "Building artwork\n"
    assert captured.err == ""


def test_success_writes_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SUCCESS messages are written to stdout."""

    configure_logging(PROGRESS)

    logger = get_logger(
        "lowkey_artifact_builder.tests.success",
    )

    logger.success("Artifact created")

    captured = capsys.readouterr()

    assert captured.out == "Artifact created\n"
    assert captured.err == ""


def test_warning_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """WARNING messages are written to stderr."""

    configure_logging(PROGRESS)

    logger = get_logger(
        "lowkey_artifact_builder.tests.warning",
    )

    logger.warning("Existing file will be replaced")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == "Existing file will be replaced\n"


def test_info_writes_to_stderr_when_enabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """INFO messages are written to stderr when enabled."""

    configure_logging(logging.INFO)

    logger = get_logger(
        "lowkey_artifact_builder.tests.info",
    )

    logger.info("Using circular model")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == "Using circular model\n"


def test_debug_writes_to_stderr_when_enabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """DEBUG messages are written to stderr when enabled."""

    configure_logging(logging.DEBUG)

    logger = get_logger(
        "lowkey_artifact_builder.tests.debug",
    )

    logger.debug("Resolved parameter")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == "Resolved parameter\n"


def test_trace_writes_to_stderr_when_enabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """TRACE messages are written to stderr when enabled."""

    configure_logging(TRACE)

    logger = get_logger(
        "lowkey_artifact_builder.tests.trace",
    )

    logger.trace("Entering resolver")

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == "Entering resolver\n"


# =========================================================
# Filtering
# =========================================================


def test_default_suppresses_info(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """INFO messages are suppressed at the default logging level."""

    monkeypatch.delenv(
        "LOG_LEVEL",
        raising=False,
    )

    configure_logging()

    logger = get_logger(
        "lowkey_artifact_builder.tests.default",
    )

    logger.info("Hidden information")
    logger.progress("Visible progress")

    captured = capsys.readouterr()

    assert captured.out == "Visible progress\n"
    assert captured.err == ""


def test_debug_level_includes_normal_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """DEBUG enables diagnostics without suppressing result output."""

    configure_logging(logging.DEBUG)

    logger = get_logger(
        "lowkey_artifact_builder.tests.debug_output",
    )

    logger.debug("Diagnostic")
    logger.progress("Working")
    logger.success("Complete")

    captured = capsys.readouterr()

    assert captured.out == "Working\nComplete\n"
    assert captured.err == "Diagnostic\n"
