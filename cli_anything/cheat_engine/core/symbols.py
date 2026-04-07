"""Symbol resolution and module enumeration.

Provides symbol lookup by parsing module exports from loaded DLLs
in the target process. For full debug symbol resolution (PDB files),
this would need either CE's symbol engine or the dbghelp.dll API.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import struct
from dataclasses import dataclass
from typing import Optional

from ..utils.ce_backend import (
    enum_modules,
    read_process_memory,
)


@dataclass(frozen=True)
class SymbolInfo:
    """Resolved symbol information."""

    name: str
    address: int
    module: str
    ordinal: Optional[int] = None

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "address": f"0x{self.address:X}",
            "module": self.module,
        }
        if self.ordinal is not None:
            d["ordinal"] = self.ordinal
        return d


@dataclass(frozen=True)
class ModuleInfo:
    """Module information for symbol listing."""

    name: str
    base_address: int
    size: int
    path: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "base_address": f"0x{self.base_address:X}",
            "size": self.size,
            "size_readable": _format_size(self.size),
            "path": self.path,
        }


def list_modules(pid: int) -> list[ModuleInfo]:
    """List all loaded modules for a process.

    Args:
        pid: Target process ID.

    Returns:
        List of ModuleInfo for each loaded module.
    """
    raw = enum_modules(pid)
    return [
        ModuleInfo(
            name=m.name,
            base_address=m.base_address,
            size=m.size,
            path=m.path,
        )
        for m in raw
    ]


def lookup_symbol(
    handle: int,
    pid: int,
    symbol_name: str,
) -> Optional[SymbolInfo]:
    """Look up a symbol by name.

    Supports module+offset notation: 'module.dll+0x1234' or just
    'module.dll' (returns base address).

    For exported function names, attempts to parse the module's
    export table.

    Args:
        handle: Process handle.
        pid: Process ID.
        symbol_name: Symbol to look up.

    Returns:
        SymbolInfo if found, None otherwise.
    """
    # Handle module+offset syntax
    if "+" in symbol_name:
        parts = symbol_name.split("+", 1)
        module_name = parts[0].strip()
        offset_str = parts[1].strip()
        try:
            offset = int(offset_str, 16) if offset_str.startswith("0x") else int(offset_str)
        except ValueError:
            return None

        modules = enum_modules(pid)
        for m in modules:
            if m.name.lower() == module_name.lower():
                return SymbolInfo(
                    name=symbol_name,
                    address=m.base_address + offset,
                    module=m.name,
                )
        return None

    # Try as module name (returns base address)
    modules = enum_modules(pid)
    for m in modules:
        if m.name.lower() == symbol_name.lower():
            return SymbolInfo(
                name=symbol_name,
                address=m.base_address,
                module=m.name,
            )

    # Try as exported function name across all modules
    for m in modules:
        try:
            exports = _parse_exports(handle, m.base_address)
            for exp in exports:
                if exp.name.lower() == symbol_name.lower():
                    return SymbolInfo(
                        name=exp.name,
                        address=exp.address,
                        module=m.name,
                        ordinal=exp.ordinal,
                    )
        except (OSError, struct.error):
            continue

    return None


def list_exports(handle: int, pid: int, module_name: str) -> list[SymbolInfo]:
    """List exported symbols from a specific module.

    Args:
        handle: Process handle.
        pid: Process ID.
        module_name: Name of the module to inspect.

    Returns:
        List of exported symbols.
    """
    modules = enum_modules(pid)
    for m in modules:
        if m.name.lower() == module_name.lower():
            try:
                return _parse_exports(handle, m.base_address)
            except (OSError, struct.error):
                return []
    return []


def resolve_address(
    pid: int,
    address: int,
) -> Optional[str]:
    """Resolve an address to a module+offset string.

    Args:
        pid: Process ID.
        address: Memory address to resolve.

    Returns:
        String like 'module.dll+0x1234' or None if not in any module.
    """
    modules = enum_modules(pid)
    for m in modules:
        if m.base_address <= address < m.base_address + m.size:
            offset = address - m.base_address
            return f"{m.name}+0x{offset:X}"
    return None


# --- Internal helpers ---


@dataclass(frozen=True)
class _ExportEntry:
    name: str
    address: int
    ordinal: int


def _parse_exports(handle: int, base: int) -> list[SymbolInfo]:
    """Parse the PE export table from a module loaded in the target process.

    Reads the PE headers and export directory to extract function names
    and addresses.
    """
    # Read DOS header
    dos_header = read_process_memory(handle, base, 64)
    if dos_header[:2] != b"MZ":
        return []

    e_lfanew = struct.unpack_from("<I", dos_header, 60)[0]

    # Read PE signature + optional header
    pe_header = read_process_memory(handle, base + e_lfanew, 264)
    if pe_header[:4] != b"PE\x00\x00":
        return []

    # Determine if PE32 or PE32+
    magic = struct.unpack_from("<H", pe_header, 24)[0]
    if magic == 0x20B:  # PE32+ (64-bit)
        export_rva = struct.unpack_from("<I", pe_header, 136)[0]
        export_size = struct.unpack_from("<I", pe_header, 140)[0]
    elif magic == 0x10B:  # PE32 (32-bit)
        export_rva = struct.unpack_from("<I", pe_header, 120)[0]
        export_size = struct.unpack_from("<I", pe_header, 124)[0]
    else:
        return []

    if export_rva == 0 or export_size == 0:
        return []

    # Read export directory
    export_dir = read_process_memory(handle, base + export_rva, min(export_size, 4096))
    num_functions = struct.unpack_from("<I", export_dir, 20)[0]
    num_names = struct.unpack_from("<I", export_dir, 24)[0]
    addr_rva = struct.unpack_from("<I", export_dir, 28)[0]
    name_rva = struct.unpack_from("<I", export_dir, 32)[0]
    ordinal_rva = struct.unpack_from("<I", export_dir, 36)[0]
    ordinal_base = struct.unpack_from("<I", export_dir, 16)[0]

    # Cap to prevent excessive reads
    num_names = min(num_names, 2000)

    # Read the three tables
    name_ptrs = read_process_memory(handle, base + name_rva, num_names * 4)
    ordinals = read_process_memory(handle, base + ordinal_rva, num_names * 2)
    func_addrs = read_process_memory(handle, base + addr_rva, num_functions * 4)

    results: list[SymbolInfo] = []
    for i in range(num_names):
        name_ptr = struct.unpack_from("<I", name_ptrs, i * 4)[0]
        ordinal = struct.unpack_from("<H", ordinals, i * 2)[0]
        func_addr = struct.unpack_from("<I", func_addrs, ordinal * 4)[0]

        # Read the name string (max 256 chars)
        try:
            name_bytes = read_process_memory(handle, base + name_ptr, 256)
            null_idx = name_bytes.find(b"\x00")
            name = name_bytes[:null_idx].decode("ascii", errors="replace") if null_idx != -1 else ""
        except OSError:
            continue

        if name:
            results.append(
                SymbolInfo(
                    name=name,
                    address=base + func_addr,
                    module="",  # caller should fill this in
                    ordinal=ordinal + ordinal_base,
                )
            )

    return results


def _format_size(size: int) -> str:
    """Format a byte size into a human-readable string."""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"
