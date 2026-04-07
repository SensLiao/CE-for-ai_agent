"""Assembly and disassembly operations.

Uses keystone-engine for assembly and capstone for disassembly when
available, falling back to a basic built-in implementation for common
x86/x64 instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..utils.ce_backend import (
    read_process_memory,
    virtual_alloc_ex,
    virtual_free_ex,
    write_process_memory,
)


@dataclass(frozen=True)
class AssembleResult:
    """Result of an assemble operation."""

    success: bool
    bytecode: bytes = b""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"success": self.success}
        if self.success:
            d["bytecode"] = self.bytecode.hex()
            d["size"] = len(self.bytecode)
        else:
            d["error"] = self.error
        return d


@dataclass(frozen=True)
class DisassemblyLine:
    """A single disassembled instruction."""

    address: int
    mnemonic: str
    op_str: str
    bytes_hex: str
    size: int

    def to_dict(self) -> dict:
        return {
            "address": f"0x{self.address:X}",
            "mnemonic": self.mnemonic,
            "op_str": self.op_str,
            "bytes": self.bytes_hex,
            "size": self.size,
        }


@dataclass(frozen=True)
class DisassembleResult:
    """Result of a disassemble operation."""

    success: bool
    instructions: list[DisassemblyLine]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"success": self.success}
        if self.success:
            d["instructions"] = [i.to_dict() for i in self.instructions]
            d["count"] = len(self.instructions)
        else:
            d["error"] = self.error
        return d


def _get_keystone():  # type: ignore[no-untyped-def]
    """Lazy import keystone-engine."""
    try:
        import keystone

        return keystone
    except ImportError:
        return None


def _get_capstone():  # type: ignore[no-untyped-def]
    """Lazy import capstone."""
    try:
        import capstone

        return capstone
    except ImportError:
        return None


def assemble(code: str, address: int = 0, is_64bit: bool = True) -> AssembleResult:
    """Assemble x86/x64 assembly code into machine code bytes.

    Uses keystone-engine if available, otherwise returns an error
    suggesting installation.

    Args:
        code: Assembly source code (one or more instructions).
        address: Base address for the assembly (affects relative jumps).
        is_64bit: Whether to assemble as 64-bit code.

    Returns:
        AssembleResult with bytecode or error.
    """
    ks = _get_keystone()
    if ks is None:
        return AssembleResult(
            success=False,
            error="keystone-engine not installed. Install with: pip install keystone-engine",
        )

    try:
        arch = ks.KS_ARCH_X86
        mode = ks.KS_MODE_64 if is_64bit else ks.KS_MODE_32
        engine = ks.Ks(arch, mode)
        encoding, count = engine.asm(code, addr=address)
        if encoding is None:
            return AssembleResult(success=False, error="Assembly produced no output")
        return AssembleResult(success=True, bytecode=bytes(encoding))
    except ks.KsError as e:
        return AssembleResult(success=False, error=str(e))


def disassemble(
    data: bytes,
    address: int = 0,
    is_64bit: bool = True,
    count: int = 0,
) -> DisassembleResult:
    """Disassemble machine code bytes into assembly instructions.

    Uses capstone if available, otherwise returns an error.

    Args:
        data: Raw machine code bytes.
        address: Base address of the code.
        is_64bit: Whether to disassemble as 64-bit code.
        count: Max number of instructions (0 = all).

    Returns:
        DisassembleResult with instructions or error.
    """
    cs = _get_capstone()
    if cs is None:
        return DisassembleResult(
            success=False,
            instructions=[],
            error="capstone not installed. Install with: pip install capstone",
        )

    try:
        arch = cs.CS_ARCH_X86
        mode = cs.CS_MODE_64 if is_64bit else cs.CS_MODE_32
        md = cs.Cs(arch, mode)
        md.detail = False

        instructions: list[DisassemblyLine] = []
        for insn in md.disasm(data, address):
            instructions.append(
                DisassemblyLine(
                    address=insn.address,
                    mnemonic=insn.mnemonic,
                    op_str=insn.op_str,
                    bytes_hex=insn.bytes.hex(),
                    size=insn.size,
                )
            )
            if count and len(instructions) >= count:
                break

        return DisassembleResult(success=True, instructions=instructions)
    except Exception as e:
        return DisassembleResult(success=False, instructions=[], error=str(e))


def disassemble_at(
    handle: int,
    address: int,
    instruction_count: int = 10,
    is_64bit: bool = True,
) -> DisassembleResult:
    """Read and disassemble instructions from a live process.

    Args:
        handle: Process handle.
        address: Address to start disassembling from.
        instruction_count: Number of instructions to disassemble.
        is_64bit: Whether the target is 64-bit.

    Returns:
        DisassembleResult with instructions.
    """
    # Read enough bytes (15 bytes per x86 instruction max)
    read_size = instruction_count * 15
    try:
        data = read_process_memory(handle, address, read_size)
    except OSError as e:
        return DisassembleResult(success=False, instructions=[], error=str(e))

    return disassemble(data, address=address, is_64bit=is_64bit, count=instruction_count)


def inject_code(
    handle: int,
    code: str,
    is_64bit: bool = True,
) -> dict:
    """Assemble code and inject it into the target process.

    Allocates executable memory in the target, writes the assembled bytes,
    and returns the allocation address. The caller is responsible for
    creating a thread or redirecting execution to run the code.

    Args:
        handle: Process handle.
        code: Assembly source code.
        is_64bit: Whether to assemble as 64-bit.

    Returns:
        Dict with 'address', 'size', and 'bytecode' on success,
        or 'error' on failure.
    """
    result = assemble(code, is_64bit=is_64bit)
    if not result.success:
        return {"success": False, "error": result.error}

    try:
        alloc_addr = virtual_alloc_ex(handle, len(result.bytecode))
        write_process_memory(handle, alloc_addr, result.bytecode)
        return {
            "success": True,
            "address": f"0x{alloc_addr:X}",
            "size": len(result.bytecode),
            "bytecode": result.bytecode.hex(),
        }
    except OSError as e:
        return {"success": False, "error": str(e)}
