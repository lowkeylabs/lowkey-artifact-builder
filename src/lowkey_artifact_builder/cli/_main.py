from __future__ import annotations

import click

from ..logging_config import configure_logging, get_logger
from .cmd_build import cli as cmd_build
from .cmd_config import cli as cmd_config

logger = get_logger(__name__)


def alias_command(base_cmd: click.Command, name: str, *, help: str | None = None) -> click.Command:
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
@click.pass_context
def cli(
    ctx,
):
    """
    Artifact builder.

    See main project README.md
    """
    configure_logging()
    ctx.ensure_object(dict)

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

# cli.add_command(alias_command(cmd_vals, name="vals", help="Display values from workspace"))
