"""Symbol resolution and module listing commands."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx


@click.group()
def symbol() -> None:
    """Symbol resolution and module listing."""


@symbol.command("lookup")
@click.argument("name")
@click.option("--pid", type=int, default=None)
@pass_ctx
def symbol_lookup(ctx: CLIContext, name: str, pid: Optional[int]) -> None:
    """Look up a symbol by name (module.dll+offset, export name)."""
    from ..core.process import attach, detach
    from ..core.symbols import lookup_symbol

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    try:
        proc = attach(pid)
        try:
            sym = lookup_symbol(proc.handle, pid, name)
            if sym:
                data = {"success": True, **sym.to_dict()}
                output(data, ctx, f"{sym.name} = 0x{sym.address:X} ({sym.module})")
            else:
                error_output(f"Symbol not found: {name}", ctx)
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@symbol.command("list-modules")
@click.option("--pid", type=int, default=None)
@pass_ctx
def symbol_list_modules(ctx: CLIContext, pid: Optional[int]) -> None:
    """List loaded modules for the attached process."""
    from ..core.symbols import list_modules

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    try:
        modules = list_modules(pid)
        if ctx.json_mode:
            output(
                {"success": True, "count": len(modules),
                 "modules": [m.to_dict() for m in modules]},
                ctx,
            )
        else:
            for m in modules:
                click.echo(f"  {m.base_address:#018x}  {m.size:>10}  {m.name}")
    except Exception as e:
        error_output(str(e), ctx)
