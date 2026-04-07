"""Session state management commands."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx


@click.group()
def session() -> None:
    """Session state management."""


@session.command("status")
@pass_ctx
def session_status(ctx: CLIContext) -> None:
    """Show current session status."""
    data = ctx.session.status()
    if ctx.json_mode:
        output({"success": True, **data}, ctx)
    else:
        click.echo(f"Session: {data['session_id']}")
        if data["attached_pid"]:
            click.echo(f"  Attached: {data['attached_name']} (PID {data['attached_pid']})")
        else:
            click.echo("  Not attached to any process")
        if data["loaded_table"]:
            click.echo(f"  Table: {data['loaded_table']}")
        click.echo(f"  Scan active: {data['scan_active']} ({data['scan_result_count']} results)")
        click.echo(f"  Undo/Redo: {data['undo_count']}/{data['redo_count']}")
        click.echo(f"  Commands: {data['command_count']}")


@session.command("history")
@click.option("-n", "--count", default=20, help="Number of history entries.")
@pass_ctx
def session_history(ctx: CLIContext, count: int) -> None:
    """Show command history."""
    history = ctx.session.get_history(count)
    if ctx.json_mode:
        output({"success": True, "history": history}, ctx)
    else:
        for h in history:
            click.echo(f"  {h['command']} {h.get('args', {})}")


@session.command("undo")
@click.option("--pid", type=int, default=None)
@pass_ctx
def session_undo(ctx: CLIContext, pid: Optional[int]) -> None:
    """Undo the last memory write."""
    from ..core.process import attach, detach
    from ..utils.ce_backend import write_process_memory

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    write = ctx.session.pop_undo()
    if write is None:
        error_output("Nothing to undo.", ctx)
        return

    try:
        proc = attach(pid)
        try:
            write_process_memory(proc.handle, write.address, write.old_value)
            output(
                {"success": True, "address": f"0x{write.address:X}",
                 "restored": write.old_value.hex()},
                ctx,
                f"Undid write at 0x{write.address:X}",
            )
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@session.command("redo")
@click.option("--pid", type=int, default=None)
@pass_ctx
def session_redo(ctx: CLIContext, pid: Optional[int]) -> None:
    """Redo the last undone memory write."""
    from ..core.process import attach, detach
    from ..utils.ce_backend import write_process_memory

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    write = ctx.session.pop_redo()
    if write is None:
        error_output("Nothing to redo.", ctx)
        return

    try:
        proc = attach(pid)
        try:
            write_process_memory(proc.handle, write.address, write.new_value)
            output(
                {"success": True, "address": f"0x{write.address:X}",
                 "applied": write.new_value.hex()},
                ctx,
                f"Redid write at 0x{write.address:X}",
            )
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@session.command("reset")
@pass_ctx
def session_reset(ctx: CLIContext) -> None:
    """Reset the session to a clean state."""
    ctx.session.reset()
    output({"success": True}, ctx, "Session reset.")
