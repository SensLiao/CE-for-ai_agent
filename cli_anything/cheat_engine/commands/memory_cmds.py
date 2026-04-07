"""Memory read/write/dump commands."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx


@click.group()
def memory() -> None:
    """Memory read/write/dump operations."""


@memory.command("read")
@click.argument("address")
@click.option(
    "-t", "--type", "var_type", default="dword",
    type=click.Choice(["byte", "word", "dword", "qword", "float", "double", "string"]),
    help="Value type to read.",
)
@click.option("--pid", type=int, default=None, help="Process PID (uses attached if omitted).")
@pass_ctx
def memory_read(ctx: CLIContext, address: str, var_type: str, pid: Optional[int]) -> None:
    """Read a value from memory at ADDRESS (hex or decimal)."""
    from ..core.memory import VarType, parse_address, read_typed
    from ..core.process import attach, detach

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached. Use 'process attach <pid>' first.", ctx)
        return

    vt_map = {
        "byte": VarType.BYTE, "word": VarType.WORD, "dword": VarType.DWORD,
        "qword": VarType.QWORD, "float": VarType.SINGLE, "double": VarType.DOUBLE,
        "string": VarType.STRING,
    }
    try:
        addr = parse_address(address)
        vt = vt_map[var_type]
        proc = attach(pid)
        try:
            val = read_typed(proc.handle, addr, vt)
            data = {"success": True, "address": f"0x{addr:X}", "type": var_type, "value": val}
            output(data, ctx, f"0x{addr:X} ({var_type}) = {val}")
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@memory.command("write")
@click.argument("address")
@click.argument("value")
@click.option(
    "-t", "--type", "var_type", default="dword",
    type=click.Choice(["byte", "word", "dword", "qword", "float", "double", "string"]),
    help="Value type to write.",
)
@click.option("--pid", type=int, default=None, help="Process PID.")
@pass_ctx
def memory_write(
    ctx: CLIContext, address: str, value: str, var_type: str, pid: Optional[int]
) -> None:
    """Write a value to memory at ADDRESS."""
    from ..core.memory import VarType, _STRUCT_FMT, parse_address, read_bytes, write_typed
    from ..core.process import attach, detach
    from ..core.session import MemoryWrite

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    vt_map = {
        "byte": VarType.BYTE, "word": VarType.WORD, "dword": VarType.DWORD,
        "qword": VarType.QWORD, "float": VarType.SINGLE, "double": VarType.DOUBLE,
        "string": VarType.STRING,
    }
    try:
        addr = parse_address(address)
        vt = vt_map[var_type]

        # Convert value string to typed Python value
        if vt in (VarType.SINGLE, VarType.DOUBLE):
            typed_val = float(value)
        elif vt == VarType.STRING:
            typed_val = value
        else:
            typed_val = int(value, 0)

        proc = attach(pid)
        try:
            # Read old value for undo
            if vt in _STRUCT_FMT:
                size = _STRUCT_FMT[vt][1]
                old = read_bytes(proc.handle, addr, size)
            else:
                old = b""

            written = write_typed(proc.handle, addr, vt, typed_val)

            # Read back new value for undo record
            if vt in _STRUCT_FMT:
                new = read_bytes(proc.handle, addr, _STRUCT_FMT[vt][1])
            else:
                new = value.encode("utf-8")

            ctx.session.push_write(
                MemoryWrite(address=addr, old_value=old, new_value=new, var_type=var_type)
            )

            data = {"success": True, "address": f"0x{addr:X}", "written": written}
            output(data, ctx, f"Wrote {value} to 0x{addr:X}")
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@memory.command("dump")
@click.argument("address")
@click.option("-s", "--size", default=256, help="Number of bytes to dump.")
@click.option("--pid", type=int, default=None, help="Process PID.")
@pass_ctx
def memory_dump(ctx: CLIContext, address: str, size: int, pid: Optional[int]) -> None:
    """Hex dump memory at ADDRESS."""
    from ..core.memory import dump_memory, parse_address, read_bytes
    from ..core.process import attach, detach

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    try:
        addr = parse_address(address)
        proc = attach(pid)
        try:
            if ctx.json_mode:
                raw = read_bytes(proc.handle, addr, size)
                output(
                    {"success": True, "address": f"0x{addr:X}", "size": size, "hex": raw.hex()},
                    ctx,
                )
            else:
                dump = dump_memory(proc.handle, addr, size)
                click.echo(dump)
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)
