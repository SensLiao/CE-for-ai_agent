"""Cheat table (.CT) file management commands."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx


@click.group()
def table() -> None:
    """Cheat table (.CT) file management."""


@table.command("load")
@click.argument("path", type=click.Path(exists=True))
@pass_ctx
def table_load(ctx: CLIContext, path: str) -> None:
    """Load a .CT cheat table file."""
    from ..core.table import load_table

    try:
        t = load_table(path)
        ctx.session.set_table(path)
        data = {"success": True, **t.to_dict()}
        output(data, ctx, f"Loaded {len(t.entries)} entries from {path}")
    except Exception as e:
        error_output(str(e), ctx)


@table.command("save")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("-o", "--output-path", default=None, help="Output path (default: overwrite).")
@pass_ctx
def table_save(ctx: CLIContext, input_path: str, output_path: Optional[str]) -> None:
    """Save a cheat table to file."""
    from ..core.table import load_table, save_table

    try:
        t = load_table(input_path)
        saved = save_table(t, output_path)
        output({"success": True, "path": str(saved)}, ctx, f"Saved to {saved}")
    except Exception as e:
        error_output(str(e), ctx)


@table.command("list-entries")
@click.argument("path", type=click.Path(exists=True))
@pass_ctx
def table_list_entries(ctx: CLIContext, path: str) -> None:
    """List all entries in a .CT file."""
    from ..core.table import list_entries, load_table

    try:
        t = load_table(path)
        entries = list_entries(t)
        if ctx.json_mode:
            output({"success": True, "entries": entries}, ctx)
        else:
            for e in entries:
                frozen = " [FROZEN]" if e.get("frozen") else ""
                click.echo(
                    f"  [{e['id']}] {e['description']} "
                    f"@ {e['address']} ({e['variable_type']}){frozen}"
                )
    except Exception as e:
        error_output(str(e), ctx)


@table.command("add-entry")
@click.argument("path", type=click.Path(exists=True))
@click.option("-d", "--desc", required=True, help="Entry description.")
@click.option("-a", "--address", required=True, help="Memory address.")
@click.option("-t", "--type", "var_type", default="dword", help="Variable type.")
@click.option("-v", "--value", default=None, help="Initial value.")
@click.option("--frozen", is_flag=True, help="Freeze the entry.")
@pass_ctx
def table_add_entry(
    ctx: CLIContext, path: str, desc: str, address: str,
    var_type: str, value: Optional[str], frozen: bool,
) -> None:
    """Add an entry to a .CT file."""
    from ..core.table import add_entry, load_table, save_table

    try:
        t = load_table(path)
        entry = add_entry(t, desc, address, var_type, value, frozen)
        save_table(t, path)
        output(
            {"success": True, "entry": entry.to_dict()}, ctx,
            f"Added entry [{entry.id}] '{desc}'",
        )
    except Exception as e:
        error_output(str(e), ctx)


@table.command("remove-entry")
@click.argument("path", type=click.Path(exists=True))
@click.argument("entry_id", type=int)
@pass_ctx
def table_remove_entry(ctx: CLIContext, path: str, entry_id: int) -> None:
    """Remove an entry by ID from a .CT file."""
    from ..core.table import load_table, remove_entry, save_table

    try:
        t = load_table(path)
        removed = remove_entry(t, entry_id)
        if removed:
            save_table(t, path)
            output(
                {"success": True, "removed": removed.to_dict()}, ctx,
                f"Removed entry [{entry_id}]",
            )
        else:
            error_output(f"Entry {entry_id} not found", ctx)
    except Exception as e:
        error_output(str(e), ctx)


@table.command("freeze")
@click.argument("path", type=click.Path(exists=True))
@click.argument("entry_id", type=int)
@pass_ctx
def table_freeze(ctx: CLIContext, path: str, entry_id: int) -> None:
    """Freeze an entry in a .CT file."""
    from ..core.table import freeze_entry, load_table, save_table

    try:
        t = load_table(path)
        if freeze_entry(t, entry_id):
            save_table(t, path)
            output(
                {"success": True, "entry_id": entry_id, "frozen": True}, ctx,
                f"Entry [{entry_id}] frozen.",
            )
        else:
            error_output(f"Entry {entry_id} not found", ctx)
    except Exception as e:
        error_output(str(e), ctx)


@table.command("unfreeze")
@click.argument("path", type=click.Path(exists=True))
@click.argument("entry_id", type=int)
@pass_ctx
def table_unfreeze(ctx: CLIContext, path: str, entry_id: int) -> None:
    """Unfreeze an entry in a .CT file."""
    from ..core.table import load_table, save_table, unfreeze_entry

    try:
        t = load_table(path)
        if unfreeze_entry(t, entry_id):
            save_table(t, path)
            output(
                {"success": True, "entry_id": entry_id, "frozen": False}, ctx,
                f"Entry [{entry_id}] unfrozen.",
            )
        else:
            error_output(f"Entry {entry_id} not found", ctx)
    except Exception as e:
        error_output(str(e), ctx)
