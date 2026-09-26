"""
Module for lowkey_artifact_builder.cli._main.
"""
# File: src/lowkey_artifact_builder/cli/_main.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import click

from ..logging_config import configure_logging, get_logger
from .cmd_build import cli as cmd_build
from .cmd_clean import cli as cmd_clean
from .cmd_color import cli as cmd_color
from .cmd_config import cli as cmd_config
from .cmd_create import cli as cmd_create
from .cmd_list import cli as cmd_list
from .cmd_show import cli as cmd_show

logger = get_logger(__name__)


def alias_command(
    base_cmd: click.Command,
    name: str,
    *,
    help: str | None = None,
) -> click.Command:
    """Creates a new independent Command instance sharing the same core logic."""

    if help is None:
        help = base_cmd.help

    return click.Command(
        name=name,
        callback=base_cmd.callback,
        params=base_cmd.params,
        help=help,
        epilog=base_cmd.epilog,
        short_help=base_cmd.short_help,
        options_metavar=base_cmd.options_metavar,
    )


@click.group(invoke_without_command=True)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show manufacturing progress.",
)
@click.option(
    "-vv",
    "--very-verbose",
    is_flag=True,
    help="Show semantic execution diagnostics.",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress semantic messaging.",
)
@click.option(
    "--log-level",
    type=click.Choice(
        [
            "TRACE",
            "DEBUG",
            "INFO",
            "PROGRESS",
            "SUCCESS",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ],
        case_sensitive=False,
    ),
    default=None,
    help="Set diagnostic logging level.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    very_verbose: bool,
    quiet: bool,
    log_level: str | None,
) -> None:
    """
    Artifact builder.

    See main project README.md
    """

    #
    # Semantic messaging and diagnostic logging are independent.
    #
    # Exactly one semantic messaging mode may be selected explicitly.
    #
    semantic_modes = sum(
        (
            quiet,
            verbose,
            very_verbose,
        )
    )

    if semantic_modes > 1:
        raise click.UsageError("--quiet, --verbose, and --very-verbose are mutually exclusive.")

    #
    # Diagnostic logging is controlled only by --log-level.
    #
    # Passing None preserves normal logging configuration, including the
    # LOG_LEVEL environment variable and configured default.
    #
    configure_logging(
        log_level,
    )

    #
    # Preserve semantic verbosity as application context for commands that
    # present structured execution events.
    #
    # The numeric representation is intentionally internal and remains
    # extensible beyond the currently exposed CLI modes.
    #
    if quiet:
        verbosity = -1
    elif very_verbose:
        verbosity = 2
    elif verbose:
        verbosity = 1
    else:
        verbosity = 0

    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbosity

    #
    # No subcommand?
    #
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ================================================
# Add commands
# ================================================

cli.add_command(cmd_config, name="config")
cli.add_command(cmd_build, name="build")
cli.add_command(cmd_color, name="colors")
cli.add_command(cmd_create, name="create")

cli.add_command(cmd_show, name="show")
cli.add_command(cmd_clean, name="clean")
cli.add_command(cmd_list, name="list")

# cli.add_command(alias_command(cmd_vals, name="vals", help="Display values from workspace"))
