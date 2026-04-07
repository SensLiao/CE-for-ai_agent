"""Memory scanning commands: first, next, results, reset."""

from __future__ import annotations

from typing import Optional

import click

from .helpers import CLIContext, error_output, output, pass_ctx

# Module-level scan state (lives for the process lifetime of the CLI).
_scan_state = None


@click.group()
def scan() -> None:
    """Memory scanning: first scan, next scan, results."""


@scan.command("first")
@click.argument("value")
@click.option(
    "-t", "--type", "var_type", default="dword",
    type=click.Choice(["byte", "word", "dword", "qword", "float", "double"]),
)
@click.option(
    "-m", "--mode", "scan_mode", default="exact",
    type=click.Choice(["exact", "between", "bigger", "smaller"]),
)
@click.option("--upper", default=None, help="Upper bound for 'between' mode.")
@click.option("--max-results", default=100000, help="Cap on results.")
@click.option("--pid", type=int, default=None)
@pass_ctx
def scan_first(
    ctx: CLIContext, value: str, var_type: str, scan_mode: str,
    upper: Optional[str], max_results: int, pid: Optional[int],
) -> None:
    """Start a new first scan for VALUE."""
    from ..core.memory import VarType
    from ..core.process import attach, detach
    from ..core.scanner import ScanOption, first_scan

    global _scan_state

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    vt_map = {
        "byte": VarType.BYTE, "word": VarType.WORD, "dword": VarType.DWORD,
        "qword": VarType.QWORD, "float": VarType.SINGLE, "double": VarType.DOUBLE,
    }
    so_map = {
        "exact": ScanOption.EXACT_VALUE, "between": ScanOption.VALUE_BETWEEN,
        "bigger": ScanOption.BIGGER_THAN, "smaller": ScanOption.SMALLER_THAN,
    }

    vt = vt_map[var_type]
    so = so_map[scan_mode]

    if vt in (VarType.SINGLE, VarType.DOUBLE):
        target = float(value)
        ub = float(upper) if upper else None
    else:
        target = int(value, 0)
        ub = int(upper, 0) if upper else None

    try:
        proc = attach(pid)
        try:
            _scan_state = first_scan(
                proc.handle, vt, so, target,
                upper_bound=ub, max_results=max_results,
            )
            ctx.session.update_scan(True, len(_scan_state.results))
            data = {"success": True, **_scan_state.to_dict()}
            output(
                data, ctx,
                f"Found {len(_scan_state.results)} results in {_scan_state.elapsed_ms:.0f}ms",
            )
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@scan.command("next")
@click.argument("value", required=False, default=None)
@click.option(
    "-m", "--mode", "scan_mode", default="exact",
    type=click.Choice([
        "exact", "between", "bigger", "smaller",
        "increased", "decreased", "changed", "unchanged",
    ]),
)
@click.option("--upper", default=None)
@click.option("--pid", type=int, default=None)
@pass_ctx
def scan_next(
    ctx: CLIContext, value: Optional[str], scan_mode: str,
    upper: Optional[str], pid: Optional[int],
) -> None:
    """Refine scan results with a next scan."""
    from ..core.memory import VarType
    from ..core.process import attach, detach
    from ..core.scanner import ScanOption, next_scan

    global _scan_state

    if _scan_state is None:
        error_output("No active scan. Run 'scan first' first.", ctx)
        return

    pid = pid or ctx.session.state.attached_pid
    if pid is None:
        error_output("No process attached.", ctx)
        return

    so_map = {
        "exact": ScanOption.EXACT_VALUE, "between": ScanOption.VALUE_BETWEEN,
        "bigger": ScanOption.BIGGER_THAN, "smaller": ScanOption.SMALLER_THAN,
        "increased": ScanOption.INCREASED_VALUE, "decreased": ScanOption.DECREASED_VALUE,
        "changed": ScanOption.CHANGED, "unchanged": ScanOption.UNCHANGED,
    }
    so = so_map[scan_mode]

    target = None
    ub = None
    if value is not None:
        vt = _scan_state.var_type
        if vt in (VarType.SINGLE, VarType.DOUBLE):
            target = float(value)
            ub = float(upper) if upper else None
        else:
            target = int(value, 0)
            ub = int(upper, 0) if upper else None

    try:
        proc = attach(pid)
        try:
            _scan_state = next_scan(proc.handle, _scan_state, so, target, ub)
            ctx.session.update_scan(True, len(_scan_state.results))
            data = {"success": True, **_scan_state.to_dict()}
            output(
                data, ctx,
                f"Narrowed to {len(_scan_state.results)} results "
                f"in {_scan_state.elapsed_ms:.0f}ms",
            )
        finally:
            detach(proc)
    except Exception as e:
        error_output(str(e), ctx)


@scan.command("results")
@click.option("--limit", default=20, help="Max results to display.")
@click.option("--offset", default=0, help="Skip first N results.")
@pass_ctx
def scan_results(ctx: CLIContext, limit: int, offset: int) -> None:
    """Show current scan results."""
    global _scan_state

    if _scan_state is None:
        error_output("No active scan.", ctx)
        return

    total = len(_scan_state.results)
    page = _scan_state.results[offset : offset + limit]
    data = {
        "success": True,
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": [r.to_dict() for r in page],
    }
    if ctx.json_mode:
        output(data, ctx)
    else:
        click.echo(f"Scan results ({offset + 1}-{offset + len(page)} of {total}):")
        for r in page:
            prev = f" (was {r.previous_value})" if r.previous_value is not None else ""
            click.echo(f"  0x{r.address:X}  =  {r.value}{prev}")


@scan.command("reset")
@pass_ctx
def scan_reset(ctx: CLIContext) -> None:
    """Reset / clear current scan."""
    global _scan_state
    _scan_state = None
    ctx.session.update_scan(False, 0)
    output({"success": True}, ctx, "Scan reset.")
