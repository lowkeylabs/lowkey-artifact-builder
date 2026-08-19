from __future__ import annotations

import click

# =========================================================
# CLI
# =========================================================


@click.command("config")
@click.pass_context
@click.argument(
    "args",
    nargs=-1,
)
def cli(
    ctx,
    args,
):
    """
    Manage configuration
    """

    _invoked_as = ctx.info_name

    click.echo(f"Invoked as {_invoked_as}")
    click.echo(f"Args: {args}")


if __name__ == "__main__":
    cli()
