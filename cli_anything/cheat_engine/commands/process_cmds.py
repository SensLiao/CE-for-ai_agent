"""Process management commands: list, attach, detach, info."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx


@click.group()
def process() -> None:
    """Process management: list, attach, detach, info."""


@process.command("list")
@click.option("-n", "--name", default=None, help="Filter by process name substring.")
@click.option("--limit", default=50, help="Max results to show.")
@pass_ctx
def process_list(ctx: CLIContext, name: Optional[str], limit: int) -> None:
    """List running processes."""
    from ..core.process import list_processes

    try:
        procs = list_processes(name_filter=name)[:limit]
        data = [p.to_dict() for p in procs]
        if ctx.json_mode:
            output({"success": True, "count": len(data), "processes": data}, ctx)
        else:
            for p in procs:
                mem = f"  {p.memory_mb:.1f}MB" if p.memory_mb else ""
                click.echo(f"  {p.pid:>8}  {p.name:<40}{mem}")
    except ImportError as e:
        error_output(str(e), ctx)


@process.command("attach")
@click.argument("pid", type=int)
@pass_ctx
def process_attach(ctx: CLIContext, pid: int) -> None:
    """Attach to a process by PID."""
    from ..core.process import attach

    try:
        proc = attach(pid)
        ctx.session.set_attached(proc.pid, proc.name)
        data = {"success": True, **proc.to_dict()}
        output(data, ctx, f"Attached to {proc.name} (PID {proc.pid})")
    except (OSError, PermissionError) as e:
        error_output(str(e), ctx)


@process.command("detach")
@pass_ctx
def process_detach(ctx: CLIContext) -> None:
    """Detach from the current process."""
    state = ctx.session.state
    if state.attached_pid is None:
        error_output("Not attached to any process", ctx)
        return
    ctx.session.set_detached()
    output({"success": True}, ctx, "Detached.")


@process.command("info")
@click.argument("pid", type=int)
@pass_ctx
def process_info(ctx: CLIContext, pid: int) -> None:
    """Get detailed info about a process."""
    from ..core.process import get_process_info

    try:
        info = get_process_info(pid)
        data = {"success": True, **info.to_dict()}
        output(
            data, ctx,
            f"{info.name} (PID {info.pid})\n"
            f"  Exe: {info.exe}\n  User: {info.username}\n"
            f"  Memory: {info.memory_mb}MB\n  Status: {info.status}",
        )
    except (ValueError, ImportError) as e:
        error_output(str(e), ctx)
