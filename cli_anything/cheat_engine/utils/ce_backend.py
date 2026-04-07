"""Backend integration for native Windows memory operations.

Provides ctypes wrappers around kernel32 for ReadProcessMemory,
WriteProcessMemory, OpenProcess, etc. This makes the CLI fully
standalone without requiring Cheat Engine installed.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from dataclasses import dataclass
from typing import Optional

# --- Windows constants ---

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

# --- kernel32 shortcuts ---

_k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ModuleEntry:
    """Snapshot of a loaded module."""

    name: str
    base_address: int
    size: int
    path: str


class MODULEENTRY32(ctypes.Structure):
    """Win32 MODULEENTRY32 structure."""

    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlsUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    """Win32 MEMORY_BASIC_INFORMATION structure."""

    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


def open_process(pid: int, access: int = PROCESS_ALL_ACCESS) -> int:
    """Open a process and return its handle.

    Raises:
        OSError: If OpenProcess fails (insufficient privileges, bad pid).
    """
    handle = _k32.OpenProcess(access, False, pid)
    if not handle:
        raise OSError(f"OpenProcess failed for pid {pid} (error {ctypes.get_last_error()})")
    return handle


def close_handle(handle: int) -> None:
    """Close a kernel object handle."""
    _k32.CloseHandle(handle)


def read_process_memory(handle: int, address: int, size: int) -> bytes:
    """Read *size* bytes from *address* in the target process.

    Returns:
        Raw bytes read from the process.

    Raises:
        OSError: If ReadProcessMemory fails.
    """
    buf = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)
    ok = _k32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_read))
    if not ok:
        raise OSError(
            f"ReadProcessMemory failed at 0x{address:X}, size={size} "
            f"(error {ctypes.get_last_error()})"
        )
    return buf.raw[: bytes_read.value]


def write_process_memory(handle: int, address: int, data: bytes) -> int:
    """Write *data* to *address* in the target process.

    Returns:
        Number of bytes written.

    Raises:
        OSError: If WriteProcessMemory fails.
    """
    size = len(data)
    buf = ctypes.create_string_buffer(data, size)
    bytes_written = ctypes.c_size_t(0)
    ok = _k32.WriteProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_written))
    if not ok:
        raise OSError(
            f"WriteProcessMemory failed at 0x{address:X}, size={size} "
            f"(error {ctypes.get_last_error()})"
        )
    return bytes_written.value


def virtual_alloc_ex(
    handle: int,
    size: int,
    alloc_type: int = MEM_COMMIT | MEM_RESERVE,
    protect: int = PAGE_EXECUTE_READWRITE,
) -> int:
    """Allocate memory in the target process. Returns the base address."""
    addr = _k32.VirtualAllocEx(handle, None, size, alloc_type, protect)
    if not addr:
        raise OSError(f"VirtualAllocEx failed (error {ctypes.get_last_error()})")
    return addr


def virtual_free_ex(handle: int, address: int) -> None:
    """Free memory previously allocated with virtual_alloc_ex."""
    _k32.VirtualFreeEx(handle, ctypes.c_void_p(address), 0, MEM_RELEASE)


def virtual_query_ex(handle: int, address: int) -> Optional[MEMORY_BASIC_INFORMATION]:
    """Query memory region information at *address*."""
    mbi = MEMORY_BASIC_INFORMATION()
    result = _k32.VirtualQueryEx(
        handle,
        ctypes.c_void_p(address),
        ctypes.byref(mbi),
        ctypes.sizeof(mbi),
    )
    return mbi if result else None


def enum_modules(pid: int) -> list[ModuleEntry]:
    """Enumerate loaded modules for the given process id."""
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == -1:
        raise OSError(f"CreateToolhelp32Snapshot failed for pid {pid}")

    entry = MODULEENTRY32()
    entry.dwSize = ctypes.sizeof(MODULEENTRY32)
    modules: list[ModuleEntry] = []

    try:
        if _k32.Module32First(snap, ctypes.byref(entry)):
            while True:
                modules.append(
                    ModuleEntry(
                        name=entry.szModule.decode("utf-8", errors="replace"),
                        base_address=ctypes.addressof(entry.modBaseAddr.contents),
                        size=entry.modBaseSize,
                        path=entry.szExePath.decode("utf-8", errors="replace"),
                    )
                )
                if not _k32.Module32Next(snap, ctypes.byref(entry)):
                    break
    finally:
        close_handle(snap)

    return modules


def is_admin() -> bool:
    """Check whether the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False
