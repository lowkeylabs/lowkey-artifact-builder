"""
Logging configuration for lowkey-artifact-builder.

Application modules should obtain loggers using:

    from lowkey_artifact_builder.logging_config import get_logger

    logger = get_logger(__name__)

Logging is configured once by the application entry point using
configure_logging(). Library modules should never configure logging
themselves.

User-facing result messages are written to stdout:

    PROGRESS
    SUCCESS

Diagnostic and error messages are written to stderr:

    TRACE
    DEBUG
    INFO
    WARNING
    ERROR
    CRITICAL
"""
# File: src/lowkey_artifact_builder/logging_config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys
from typing import Final

# =========================================================
# Custom logging levels
# =========================================================
#
# Numeric values are intentionally centralized here.
#
# Calling code should use the semantic logging methods:
#
#     logger.trace(...)
#     logger.progress(...)
#     logger.success(...)
#
# rather than depending on these numeric values.
#

TRACE: Final = 5

PROGRESS: Final = 25
SUCCESS: Final = 26

DEFAULT_LEVEL: Final = PROGRESS

LOG_LEVEL_ENV: Final = "LOG_LEVEL"


# =========================================================
# Custom logger
# =========================================================


class ArtifactLogger(logging.Logger):
    """
    Logger with lowkey-artifact-builder custom logging levels.
    """

    def trace(
        self,
        msg: object,
        *args: object,
    ) -> None:
        """
        Log a TRACE message.
        """

        self.log(
            TRACE,
            msg,
            *args,
        )

    def progress(
        self,
        msg: object,
        *args: object,
    ) -> None:
        """
        Log a PROGRESS message.

        PROGRESS messages are user-facing and are routed to stdout.
        """

        self.log(
            PROGRESS,
            msg,
            *args,
        )

    def success(
        self,
        msg: object,
        *args: object,
    ) -> None:
        """
        Log a SUCCESS message.

        SUCCESS messages are user-facing and are routed to stdout.
        """

        self.log(
            SUCCESS,
            msg,
            *args,
        )


#
# Install the custom logger class before application loggers are created.
#

logging.setLoggerClass(
    ArtifactLogger,
)


#
# Register human-readable names for the custom levels.
#

logging.addLevelName(
    TRACE,
    "TRACE",
)

logging.addLevelName(
    PROGRESS,
    "PROGRESS",
)

logging.addLevelName(
    SUCCESS,
    "SUCCESS",
)


# =========================================================
# Logger access
# =========================================================


def get_logger(
    name: str,
) -> ArtifactLogger:
    """
    Return an Artifact Builder logger.

    Using this helper rather than logging.getLogger() gives static type
    checkers knowledge of the custom trace(), progress(), and success()
    methods.
    """

    logger = logging.getLogger(name)

    if not isinstance(logger, ArtifactLogger):
        raise TypeError(f"Logger {name!r} is not an ArtifactLogger.")

    return logger


# =========================================================
# Level resolution
# =========================================================


def resolve_log_level(
    level: str | int | None = None,
) -> int:
    """
    Resolve the effective logging level.

    Resolution precedence is:

        explicit argument
        LOG_LEVEL environment variable
        DEFAULT_LEVEL

    String values are case-insensitive and may specify either standard
    Python logging levels or Artifact Builder custom levels.
    """

    if level is None:
        level = os.getenv(LOG_LEVEL_ENV)

    if level is None:
        return DEFAULT_LEVEL

    if isinstance(level, int):
        return level

    name = level.strip().upper()

    levels = {
        "TRACE": TRACE,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "PROGRESS": PROGRESS,
        "SUCCESS": SUCCESS,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    try:
        return levels[name]

    except KeyError as exc:
        valid = ", ".join(levels)

        raise ValueError(f"Invalid log level {level!r}. Expected one of: {valid}.") from exc


# =========================================================
# Logging filters
# =========================================================


class ResultFilter(logging.Filter):
    """
    Allow user-facing result messages.

    PROGRESS and SUCCESS messages are routed to stdout.
    """

    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        """
        Return True for result-oriented logging levels.
        """

        return record.levelno in {
            PROGRESS,
            SUCCESS,
        }


class DiagnosticFilter(logging.Filter):
    """
    Allow diagnostic and error messages.

    PROGRESS and SUCCESS are excluded because they are handled by the
    stdout result handler.
    """

    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        """
        Return True for non-result logging levels.
        """

        return record.levelno not in {
            PROGRESS,
            SUCCESS,
        }


# =========================================================
# Application configuration
# =========================================================


def configure_logging(
    level: str | int | None = None,
) -> int:
    """
    Configure application logging.

    User-facing result messages are written to stdout:

        PROGRESS
        SUCCESS

    Diagnostic and error messages are written to stderr:

        TRACE
        DEBUG
        INFO
        WARNING
        ERROR
        CRITICAL

    Both streams intentionally use a minimal formatter containing only
    the message.

    Logging should normally be configured once by the application entry
    point before handing control to application code.

    Returns the resolved numeric logging level.
    """

    resolved_level = resolve_log_level(
        level,
    )

    formatter = logging.Formatter(
        "%(message)s",
    )

    #
    # User-facing result output.
    #

    result_handler = logging.StreamHandler(
        sys.stdout,
    )

    result_handler.setFormatter(
        formatter,
    )

    result_handler.addFilter(
        ResultFilter(),
    )

    #
    # Diagnostics, warnings, and errors.
    #

    diagnostic_handler = logging.StreamHandler(
        sys.stderr,
    )

    diagnostic_handler.setFormatter(
        formatter,
    )

    diagnostic_handler.addFilter(
        DiagnosticFilter(),
    )

    #
    # Configure the root logger.
    #

    root_logger = logging.getLogger()

    root_logger.handlers.clear()

    root_logger.addHandler(
        result_handler,
    )

    root_logger.addHandler(
        diagnostic_handler,
    )

    root_logger.setLevel(
        resolved_level,
    )

    return resolved_level
