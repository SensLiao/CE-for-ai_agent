"""Assembly and disassembly commands."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx


@click.group()
def asm() -> None:
    """Assembly and disassembly operations."""


@asm.command("assemble")
@click.argument("code")
@click.option("--address", default="0", help="Base address for assembly.")
@click.option("--x86", "bits32", is_flag=True, help="Assemble as 32-bit (default: 64-bit).")
@pass_ctx
def asm_assemble(ctx: CLIContext, code: str, address: str, bits32: bool) -> None:
    """Assemble x86/x64 code into bytes."""
    from ..core.assembler import assemble
    from ..core.memory import parse_address

    addr = parse_address(address)
    result = assemble(code, address=addr, is_64bit=not bits32)
    output(
        result.to_dict(), ctx,
        result.bytecode.hex() if result.success else f"Error: {result.error}",
    )


@asm.command("disassemble")
@click.argument("address")
@click.option("-c", "--count", default=10, help="Number of instructions.")
@click.option("--x86", "bits32", is_flag=True, help="Disassemble as 32-bit.")
@click.option("--pid", type=int, default=None)
@pass_ctx
def asm_disassemble(
    ctx: CLIContext, address: str, count: int, bits32: bool, pid: Optional[int]
) -> None:
    """Disassemble instructions at ADDRESS in a live process."""
    from ..core.assembler import disassemble_at
    from ..core.memory import parse_address
    from ..core.process import attach, detach

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    try:
        addr = parse_address(address)
        proc = attach(pid)
        try:
            result = disassemble_at(proc.handle, addr, count, is_64bit=not bits32)
            if ctx.json_mode:
                output(result.to_dict(), ctx)
            else:
                if result.success:
                    for insn in result.instructions:
                        click.echo(
                            f"  0x{insn.address:X}  {insn.bytes_hex:<20}  "
                            f"{insn.mnemonic} {insn.op_str}"
                        )
                else:
                    click.echo(f"Error: {result.error}")
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@asm.command("inject")
@click.argument("code")
@click.option("--x86", "bits32", is_flag=True, help="Assemble as 32-bit.")
@click.option("--pid", type=int, default=None)
@pass_ctx
def asm_inject(ctx: CLIContext, code: str, bits32: bool, pid: Optional[int]) -> None:
    """Assemble and inject code into the target process."""
    from ..core.assembler import inject_code
    from ..core.process import attach, detach

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    try:
        proc = attach(pid)
        try:
            result = inject_code(proc.handle, code, is_64bit=not bits32)
            text = (
                f"Injected at {result.get('address', '?')}"
                if result.get("success")
                else f"Error: {result.get('error')}"
            )
            output(result, ctx, text)
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)
