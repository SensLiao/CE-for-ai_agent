"""Memory read/write operations using native Windows API.

Wraps kernel32 ReadProcessMemory / WriteProcessMemory via the ce_backend
module. Supports typed reads (int, float, double, string, bytes) mirroring
the Cheat Engine Lua API surface.
"""

from __future__ import annotations

import struct
from enum import IntEnum
from typing import Any, Union

from ..utils.ce_backend import read_process_memory, write_process_memory


class VarType(IntEnum):
    """Variable types matching CE's vtXxx constants."""

    BYTE = 0
    WORD = 1      # uint16
    DWORD = 2     # uint32
    QWORD = 3     # uint64
    SINGLE = 4    # float32
    DOUBLE = 5    # float64
    STRING = 6
    BYTE_ARRAY = 8


# struct format strings indexed by VarType
_STRUCT_FMT = {
    VarType.BYTE: ("<B", 1),
    VarType.WORD: ("<H", 2),
    VarType.DWORD: ("<I", 4),
    VarType.QWORD: ("<Q", 8),
    VarType.SINGLE: ("<f", 4),
    VarType.DOUBLE: ("<d", 8),
}


def parse_address(addr_str: str) -> int:
    """Parse an address string (hex or decimal) into an integer.

    Accepts: '0x7FF...', '7FF...h', plain decimal.
    """
    s = addr_str.strip()
    if s.lower().startswith("0x"):
        return int(s, 16)
    if s.lower().endswith("h"):
        return int(s[:-1], 16)
    # Try hex first if it looks hex-ish
    try:
        return int(s, 16) if any(c in s.upper() for c in "ABCDEF") else int(s)
    except ValueError:
        return int(s)


# --- Typed reads ---


def read_byte(handle: int, address: int) -> int:
    """Read a single unsigned byte."""
    data = read_process_memory(handle, address, 1)
    return struct.unpack("<B", data)[0]


def read_word(handle: int, address: int) -> int:
    """Read an unsigned 16-bit integer (little-endian)."""
    data = read_process_memory(handle, address, 2)
    return struct.unpack("<H", data)[0]


def read_dword(handle: int, address: int) -> int:
    """Read an unsigned 32-bit integer (little-endian)."""
    data = read_process_memory(handle, address, 4)
    return struct.unpack("<I", data)[0]


def read_qword(handle: int, address: int) -> int:
    """Read an unsigned 64-bit integer (little-endian)."""
    data = read_process_memory(handle, address, 8)
    return struct.unpack("<Q", data)[0]


def read_float(handle: int, address: int) -> float:
    """Read a 32-bit float (little-endian)."""
    data = read_process_memory(handle, address, 4)
    return struct.unpack("<f", data)[0]


def read_double(handle: int, address: int) -> float:
    """Read a 64-bit double (little-endian)."""
    data = read_process_memory(handle, address, 8)
    return struct.unpack("<d", data)[0]


def read_string(handle: int, address: int, max_length: int = 256, encoding: str = "utf-8") -> str:
    """Read a null-terminated string from the target process.

    Args:
        handle: Process handle.
        address: Start address.
        max_length: Maximum bytes to read.
        encoding: String encoding.

    Returns:
        Decoded string (up to the first null byte).
    """
    data = read_process_memory(handle, address, max_length)
    null_pos = data.find(b"\x00")
    if null_pos != -1:
        data = data[:null_pos]
    return data.decode(encoding, errors="replace")


def read_bytes(handle: int, address: int, count: int) -> bytes:
    """Read raw bytes from the target process."""
    return read_process_memory(handle, address, count)


def read_typed(handle: int, address: int, var_type: VarType, **kwargs: Any) -> Any:
    """Read a value of the given VarType.

    Dispatches to the appropriate typed reader.
    """
    if var_type == VarType.STRING:
        return read_string(handle, address, **kwargs)
    if var_type == VarType.BYTE_ARRAY:
        count = kwargs.get("count", kwargs.get("max_length", 16))
        return read_bytes(handle, address, count)
    fmt, size = _STRUCT_FMT[var_type]
    data = read_process_memory(handle, address, size)
    return struct.unpack(fmt, data)[0]


# --- Typed writes ---


def write_byte(handle: int, address: int, value: int) -> int:
    """Write a single unsigned byte."""
    return write_process_memory(handle, address, struct.pack("<B", value & 0xFF))


def write_word(handle: int, address: int, value: int) -> int:
    """Write an unsigned 16-bit integer."""
    return write_process_memory(handle, address, struct.pack("<H", value & 0xFFFF))


def write_dword(handle: int, address: int, value: int) -> int:
    """Write an unsigned 32-bit integer."""
    return write_process_memory(handle, address, struct.pack("<I", value & 0xFFFFFFFF))


def write_qword(handle: int, address: int, value: int) -> int:
    """Write an unsigned 64-bit integer."""
    return write_process_memory(handle, address, struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF))


def write_float(handle: int, address: int, value: float) -> int:
    """Write a 32-bit float."""
    return write_process_memory(handle, address, struct.pack("<f", value))


def write_double(handle: int, address: int, value: float) -> int:
    """Write a 64-bit double."""
    return write_process_memory(handle, address, struct.pack("<d", value))


def write_string(handle: int, address: int, value: str, encoding: str = "utf-8") -> int:
    """Write a null-terminated string."""
    data = value.encode(encoding) + b"\x00"
    return write_process_memory(handle, address, data)


def write_bytes(handle: int, address: int, data: bytes) -> int:
    """Write raw bytes."""
    return write_process_memory(handle, address, data)


def write_typed(handle: int, address: int, var_type: VarType, value: Any, **kwargs: Any) -> int:
    """Write a value of the given VarType.

    Dispatches to the appropriate typed writer.
    """
    writers = {
        VarType.BYTE: write_byte,
        VarType.WORD: write_word,
        VarType.DWORD: write_dword,
        VarType.QWORD: write_qword,
        VarType.SINGLE: write_float,
        VarType.DOUBLE: write_double,
    }
    if var_type == VarType.STRING:
        return write_string(handle, address, value, **kwargs)
    if var_type == VarType.BYTE_ARRAY:
        if isinstance(value, str):
            value = bytes.fromhex(value.replace(" ", ""))
        return write_bytes(handle, address, value)
    writer = writers.get(var_type)
    if writer is None:
        raise ValueError(f"Unsupported VarType for write: {var_type}")
    return writer(handle, address, value)


def dump_memory(handle: int, address: int, size: int, bytes_per_line: int = 16) -> str:
    """Read memory and format as a hex dump string.

    Returns:
        Multi-line hex dump with address offsets and ASCII representation.
    """
    data = read_process_memory(handle, address, size)
    lines: list[str] = []
    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        addr = address + offset
        lines.append(f"0x{addr:08X}  {hex_part:<{bytes_per_line * 3 - 1}}  |{ascii_part}|")
    return "\n".join(lines)
