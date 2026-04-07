"""Memory scanner — standalone Python implementation.

Performs value scanning across committed memory regions of a target process,
similar to CE's memscan_* Lua API. Uses native ctypes via ce_backend for
all memory access.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Optional

from ..utils.ce_backend import (
    MEM_COMMIT,
    MEMORY_BASIC_INFORMATION,
    read_process_memory,
    virtual_query_ex,
)
from .memory import VarType, _STRUCT_FMT


class ScanOption(IntEnum):
    """Scan comparison options, matching CE's soXxx constants."""

    EXACT_VALUE = 1
    VALUE_BETWEEN = 2
    BIGGER_THAN = 3
    SMALLER_THAN = 4
    INCREASED_VALUE = 5
    DECREASED_VALUE = 7
    CHANGED = 9
    UNCHANGED = 10


@dataclass
class ScanResult:
    """A single address that matched a scan criterion."""

    address: int
    value: Any
    previous_value: Optional[Any] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "address": f"0x{self.address:X}",
            "value": self.value,
        }
        if self.previous_value is not None:
            d["previous_value"] = self.previous_value
        return d


@dataclass
class ScanState:
    """Tracks the state of an ongoing scan session."""

    var_type: VarType = VarType.DWORD
    results: list[ScanResult] = field(default_factory=list)
    scan_count: int = 0
    last_scan_option: Optional[ScanOption] = None
    last_scan_value: Any = None
    start_address: int = 0x00000000
    end_address: int = 0x7FFFFFFFFFFF
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "var_type": self.var_type.name,
            "result_count": len(self.results),
            "scan_count": self.scan_count,
            "last_scan_option": self.last_scan_option.name if self.last_scan_option else None,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


def _read_value_at(handle: int, address: int, var_type: VarType) -> Any:
    """Read a typed value at the given address. Returns None on failure."""
    try:
        if var_type == VarType.STRING or var_type == VarType.BYTE_ARRAY:
            return None  # Not supported for scanning
        fmt, size = _STRUCT_FMT[var_type]
        data = read_process_memory(handle, address, size)
        return struct.unpack(fmt, data)[0]
    except OSError:
        return None


def _value_size(var_type: VarType) -> int:
    """Return the byte size for a numeric VarType."""
    if var_type in _STRUCT_FMT:
        return _STRUCT_FMT[var_type][1]
    return 4  # default


def _make_comparator(
    scan_option: ScanOption,
    target_value: Any = None,
    upper_bound: Any = None,
) -> Callable[[Any, Optional[Any]], bool]:
    """Build a comparator function for the given scan option."""

    if scan_option == ScanOption.EXACT_VALUE:
        return lambda val, _prev: val == target_value
    if scan_option == ScanOption.BIGGER_THAN:
        return lambda val, _prev: val > target_value
    if scan_option == ScanOption.SMALLER_THAN:
        return lambda val, _prev: val < target_value
    if scan_option == ScanOption.VALUE_BETWEEN:
        return lambda val, _prev: target_value <= val <= upper_bound
    if scan_option == ScanOption.INCREASED_VALUE:
        return lambda val, prev: prev is not None and val > prev
    if scan_option == ScanOption.DECREASED_VALUE:
        return lambda val, prev: prev is not None and val < prev
    if scan_option == ScanOption.CHANGED:
        return lambda val, prev: prev is not None and val != prev
    if scan_option == ScanOption.UNCHANGED:
        return lambda val, prev: prev is not None and val == prev
    raise ValueError(f"Unsupported scan option: {scan_option}")


def _iter_committed_regions(
    handle: int, start: int, end: int
) -> list[tuple[int, int]]:
    """Yield (base, size) for committed, readable memory regions."""
    regions: list[tuple[int, int]] = []
    addr = start
    while addr < end:
        mbi = virtual_query_ex(handle, addr)
        if mbi is None:
            break
        region_end = (mbi.BaseAddress or 0) + mbi.RegionSize
        if mbi.State == MEM_COMMIT and mbi.RegionSize > 0:
            # Skip guard / no-access pages
            protect = mbi.Protect
            readable = protect & 0xEE  # PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE_READ | etc.
            if readable:
                regions.append((mbi.BaseAddress or 0, mbi.RegionSize))
        addr = region_end if region_end > addr else addr + 0x1000
    return regions


def first_scan(
    handle: int,
    var_type: VarType,
    scan_option: ScanOption,
    value: Any,
    upper_bound: Any = None,
    start_address: int = 0x00000000,
    end_address: int = 0x7FFFFFFFFFFF,
    max_results: int = 100_000,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ScanState:
    """Perform the initial (first) scan across all committed memory regions.

    Args:
        handle: Target process handle.
        var_type: Type of value to scan for.
        scan_option: Comparison mode.
        value: Target value (or lower bound for BETWEEN).
        upper_bound: Upper bound for VALUE_BETWEEN scans.
        start_address: Scan range start.
        end_address: Scan range end.
        max_results: Cap on number of results to avoid OOM.
        progress_callback: Optional (regions_done, total_regions) callback.

    Returns:
        ScanState with matching results.
    """
    t0 = time.perf_counter()
    state = ScanState(
        var_type=var_type,
        scan_count=1,
        last_scan_option=scan_option,
        last_scan_value=value,
        start_address=start_address,
        end_address=end_address,
    )

    comparator = _make_comparator(scan_option, value, upper_bound)
    val_size = _value_size(var_type)
    fmt = _STRUCT_FMT.get(var_type)
    if fmt is None:
        raise ValueError(f"Scanning not supported for {var_type.name}")
    fmt_str, _ = fmt

    regions = _iter_committed_regions(handle, start_address, end_address)
    total = len(regions)

    for idx, (base, size) in enumerate(regions):
        if len(state.results) >= max_results:
            break
        try:
            data = read_process_memory(handle, base, min(size, 0x100000))  # 1 MB chunks
        except OSError:
            continue

        for offset in range(0, len(data) - val_size + 1, val_size):
            current = struct.unpack(fmt_str, data[offset : offset + val_size])[0]
            if comparator(current, None):
                state.results.append(ScanResult(address=base + offset, value=current))
                if len(state.results) >= max_results:
                    break

        if progress_callback:
            progress_callback(idx + 1, total)

    state.elapsed_ms = (time.perf_counter() - t0) * 1000
    return state


def next_scan(
    handle: int,
    state: ScanState,
    scan_option: ScanOption,
    value: Any = None,
    upper_bound: Any = None,
) -> ScanState:
    """Refine existing scan results with a new comparison.

    Only addresses from the previous result set are re-checked.

    Args:
        handle: Target process handle.
        state: Previous ScanState.
        scan_option: New comparison mode.
        value: New target value (for exact/range scans).
        upper_bound: Upper bound for BETWEEN scans.

    Returns:
        Updated ScanState with filtered results.
    """
    t0 = time.perf_counter()
    comparator = _make_comparator(scan_option, value, upper_bound)
    fmt = _STRUCT_FMT.get(state.var_type)
    if fmt is None:
        raise ValueError(f"Scanning not supported for {state.var_type.name}")
    fmt_str, val_size = fmt

    new_results: list[ScanResult] = []
    for prev in state.results:
        current = _read_value_at(handle, prev.address, state.var_type)
        if current is None:
            continue
        if comparator(current, prev.value):
            new_results.append(
                ScanResult(
                    address=prev.address,
                    value=current,
                    previous_value=prev.value,
                )
            )

    return ScanState(
        var_type=state.var_type,
        results=new_results,
        scan_count=state.scan_count + 1,
        last_scan_option=scan_option,
        last_scan_value=value,
        start_address=state.start_address,
        end_address=state.end_address,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
    )


def reset_scan() -> ScanState:
    """Return a fresh, empty scan state."""
    return ScanState()
