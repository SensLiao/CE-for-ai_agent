"""Process management: list, attach, detach, info.

Uses psutil for process enumeration and the native ctypes backend
for attach/detach (OpenProcess / CloseHandle).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from dataclasses import dataclass
from typing import Optional

from ..utils.ce_backend import (
    PROCESS_ALL_ACCESS,
    close_handle,
    enum_modules,
    is_admin,
    open_process,
)

# We import psutil lazily to keep the module importable even when
# psutil is not installed (tests can mock it).
_psutil = None


def _get_psutil():  # type: ignore[no-untyped-def]
    global _psutil
    if _psutil is None:
        try:
            import psutil

            _psutil = psutil
        except ImportError as exc:
            raise ImportError(
                "psutil is required for process listing. Install with: pip install psutil"
            ) from exc
    return _psutil


@dataclass(frozen=True)
class ProcessInfo:
    """Snapshot of a running process."""

    pid: int
    name: str
    exe: Optional[str] = None
    username: Optional[str] = None
    memory_mb: Optional[float] = None
    status: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "exe": self.exe,
            "username": self.username,
            "memory_mb": self.memory_mb,
            "status": self.status,
        }


@dataclass
class AttachedProcess:
    """Represents a process we have a handle to."""

    pid: int
    name: str
    handle: int
    is_64bit: bool = True

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "handle": self.handle,
            "is_64bit": self.is_64bit,
        }


def list_processes(name_filter: Optional[str] = None) -> list[ProcessInfo]:
    """List running processes, optionally filtered by name substring.

    Args:
        name_filter: Case-insensitive substring to match against process name.

    Returns:
        List of ProcessInfo snapshots.
    """
    psutil = _get_psutil()
    result: list[ProcessInfo] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "username", "memory_info", "status"]):
        try:
            info = proc.info
            name = info.get("name", "")
            if name_filter and name_filter.lower() not in name.lower():
                continue
            mem = info.get("memory_info")
            result.append(
                ProcessInfo(
                    pid=info["pid"],
                    name=name,
                    exe=info.get("exe"),
                    username=info.get("username"),
                    memory_mb=round(mem.rss / (1024 * 1024), 2) if mem else None,
                    status=info.get("status"),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result


def attach(pid: int) -> AttachedProcess:
    """Attach to a process by PID.

    Opens the process with PROCESS_ALL_ACCESS and determines bitness.

    Raises:
        OSError: If the process cannot be opened.
        PermissionError: If not running as admin.
    """
    if not is_admin():
        raise PermissionError(
            "Administrator privileges required to attach to processes. "
            "Run the CLI as administrator."
        )

    handle = open_process(pid, PROCESS_ALL_ACCESS)
    name = _get_process_name(pid)
    is_64 = _is_process_64bit(handle)
    return AttachedProcess(pid=pid, name=name, handle=handle, is_64bit=is_64)


def detach(proc: AttachedProcess) -> None:
    """Detach from a process by closing its handle."""
    close_handle(proc.handle)


def get_process_info(pid: int) -> ProcessInfo:
    """Get detailed info about a specific process.

    Raises:
        ValueError: If the process does not exist.
    """
    psutil = _get_psutil()
    try:
        proc = psutil.Process(pid)
        mem = proc.memory_info()
        return ProcessInfo(
            pid=proc.pid,
            name=proc.name(),
            exe=proc.exe(),
            username=proc.username(),
            memory_mb=round(mem.rss / (1024 * 1024), 2),
            status=proc.status(),
        )
    except psutil.NoSuchProcess:
        raise ValueError(f"No process with pid {pid}")


def get_modules(pid: int) -> list[dict]:
    """Get loaded modules for a process.

    Returns:
        List of dicts with name, base_address, size, path.
    """
    modules = enum_modules(pid)
    return [
        {
            "name": m.name,
            "base_address": f"0x{m.base_address:X}",
            "size": m.size,
            "path": m.path,
        }
        for m in modules
    ]


def _get_process_name(pid: int) -> str:
    """Get process name by PID via psutil."""
    try:
        psutil = _get_psutil()
        return psutil.Process(pid).name()
    except Exception:
        return f"pid_{pid}"


def _is_process_64bit(handle: int) -> bool:
    """Determine if a process is 64-bit via IsWow64Process."""
    is_wow64 = wt.BOOL(False)
    ctypes.windll.kernel32.IsWow64Process(handle, ctypes.byref(is_wow64))  # type: ignore[attr-defined]
    # On a 64-bit OS: WoW64 = True means 32-bit process
    import platform

    if platform.machine().endswith("64"):
        return not is_wow64.value
    return False
