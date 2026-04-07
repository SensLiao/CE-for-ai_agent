"""Main CLI entry point for cli-anything-cheatengine.

Registers all command groups and provides the root Click group.
All commands support --json for machine-readable output.
"""

from __future__ import annotations

import click

from .commands.helpers import CLIContext
from .commands import asm, bridge, memory, process, scan, session, symbol, table


@click.group()
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format.")
@click.version_option(version="0.2.0", prog_name="cli-anything-cheatengine")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool) -> None:
    """CLI-Anything Cheat Engine harness.

    Standalone memory inspection, scanning, and cheat table management.
    Uses native Windows API -- no Cheat Engine installation required.
    """
    ctx.ensure_object(CLIContext)
    ctx.obj.json_mode = json_mode


# Register command groups
cli.add_command(process)
cli.add_command(memory)
cli.add_command(scan)
cli.add_command(table)
cli.add_command(asm)
cli.add_command(symbol)
cli.add_command(session)
cli.add_command(bridge)


def main() -> None:
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
