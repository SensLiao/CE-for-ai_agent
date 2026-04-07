"""CLI commands for CE bridge advanced features.

Requires a running Cheat Engine instance connected via the pipe bridge.
"""

from __future__ import annotations

import click

from .helpers import CLIContext, error_output, output, pass_ctx


def _get_bridge(ctx: CLIContext):  # type: ignore[no-untyped-def]
    """Get or create the CE bridge from session context."""
    if ctx._bridge is None:
        from ..bridge.ce_bridge import CEBridge

        ctx._bridge = CEBridge()
    return ctx._bridge


def _detect_ce_running() -> dict:
    """Check if any Cheat Engine process is running."""
    try:
        import psutil
    except ImportError:
        return {"running": False, "error": "psutil not installed"}

    ce_names = {
        "cheatengine-x86_64.exe",
        "cheatengine-i386.exe",
        "cheatengine.exe",
        "cheat engine.exe",
    }
    found = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in ce_names:
                found.append({"pid": proc.info["pid"], "name": proc.info["name"]})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"running": len(found) > 0, "processes": found}


@click.group("bridge")
def bridge() -> None:
    """CE bridge — connect to Cheat Engine for advanced features."""


@bridge.command("detect")
@pass_ctx
def bridge_detect(ctx: CLIContext) -> None:
    """Detect if Cheat Engine is running (no connection needed)."""
    info = _detect_ce_running()
    if info["running"]:
        procs = info["processes"]
        lines = [f"  PID {p['pid']}  {p['name']}" for p in procs]
        output(
            {"success": True, **info},
            ctx,
            f"Cheat Engine is running ({len(procs)} process(es)):\n" + "\n".join(lines),
        )
    else:
        output(
            {"success": True, **info},
            ctx,
            "Cheat Engine is NOT running.\n"
            "Bridge commands are unavailable. Start CE first.",
        )


@bridge.command("start")
@click.option("--timeout", default=120, help="Seconds to wait for CE connection.")
@pass_ctx
def bridge_start(ctx: CLIContext, timeout: int) -> None:
    """Start pipe server and wait for CE to connect."""
    b = _get_bridge(ctx)

    click.echo("Starting pipe server...")
    b.start()
    click.echo("Pipe ready: \\\\.\\pipe\\cli_anything_ce")
    click.echo()
    click.echo("In CE Lua Engine, execute the client script:")
    click.echo(f"  {b.get_lua_script_path()}")
    click.echo()
    click.echo(f"Waiting for CE (timeout: {timeout}s)...")

    if b.wait_for_ce(timeout=timeout):
        output(
            {"success": True, "ce_version": b.ce_version()},
            ctx,
            f"Connected! {b.ce_version()}",
        )
    else:
        error_output("CE did not connect within timeout.", ctx)


@bridge.command("status")
@pass_ctx
def bridge_status(ctx: CLIContext) -> None:
    """Check bridge connection status."""
    b = _get_bridge(ctx)
    if b.connected and b.ping():
        output(
            {"success": True, "connected": True, "ce_version": b.ce_version()},
            ctx,
            f"Connected to {b.ce_version()}",
        )
    else:
        output(
            {"success": True, "connected": False},
            ctx,
            "Not connected to CE.",
        )


@bridge.command("lua")
@click.argument("code")
@pass_ctx
def bridge_lua(ctx: CLIContext, code: str) -> None:
    """Execute arbitrary Lua code in CE."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE. Run 'bridge start' first.", ctx)
        return
    result = b.execute_safe(code)
    if result.success:
        output({"success": True, "result": result.data}, ctx, result.data)
    else:
        error_output(result.data, ctx)


@bridge.command("stop")
@pass_ctx
def bridge_stop(ctx: CLIContext) -> None:
    """Disconnect from CE and stop the pipe server."""
    b = _get_bridge(ctx)
    b.stop()
    output({"success": True}, ctx, "Bridge stopped.")


# --- Speedhack ---


@bridge.group("speed")
def speed() -> None:
    """Speedhack — control game speed."""


@speed.command("set")
@click.argument("multiplier", type=float)
@pass_ctx
def speed_set(ctx: CLIContext, multiplier: float) -> None:
    """Set speed multiplier (e.g., 2.0 = double speed, 0.5 = half speed)."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        b.speedhack_set_speed(multiplier)
        output(
            {"success": True, "speed": multiplier},
            ctx,
            f"Speed set to {multiplier}x",
        )
    except Exception as e:
        error_output(str(e), ctx)


@speed.command("reset")
@pass_ctx
def speed_reset(ctx: CLIContext) -> None:
    """Reset speed to normal (1.0x)."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        b.speedhack_set_speed(1.0)
        output({"success": True, "speed": 1.0}, ctx, "Speed reset to 1.0x")
    except Exception as e:
        error_output(str(e), ctx)


# --- Debugger ---


@bridge.group("debug")
def debug() -> None:
    """Debugger — breakpoints and stepping."""


@debug.command("break")
@click.argument("address")
@pass_ctx
def debug_break(ctx: CLIContext, address: str) -> None:
    """Set a breakpoint at ADDRESS."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        result = b.set_breakpoint(address)
        output({"success": True, "address": address}, ctx, f"Breakpoint set at {address}")
    except Exception as e:
        error_output(str(e), ctx)


@debug.command("remove")
@click.argument("address")
@pass_ctx
def debug_remove(ctx: CLIContext, address: str) -> None:
    """Remove breakpoint at ADDRESS."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        b.remove_breakpoint(address)
        output({"success": True}, ctx, f"Breakpoint removed at {address}")
    except Exception as e:
        error_output(str(e), ctx)


@debug.command("continue")
@pass_ctx
def debug_continue(ctx: CLIContext) -> None:
    """Continue execution from breakpoint."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        b.continue_from_breakpoint()
        output({"success": True}, ctx, "Continued from breakpoint.")
    except Exception as e:
        error_output(str(e), ctx)


# --- Auto Assemble ---


@bridge.command("aa")
@click.argument("script_path", type=click.Path(exists=True))
@pass_ctx
def auto_assemble(ctx: CLIContext, script_path: str) -> None:
    """Execute a CE Auto Assemble script file."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            script = f.read()
        result = b.auto_assemble(script)
        output(
            {"success": True, "result": result},
            ctx,
            f"Auto assemble: {result}",
        )
    except Exception as e:
        error_output(str(e), ctx)


# --- Cheat Table via CE ---


@bridge.group("ct")
def ct() -> None:
    """Cheat table operations via CE."""


@ct.command("activate")
@click.argument("description")
@pass_ctx
def ct_activate(ctx: CLIContext, description: str) -> None:
    """Activate a cheat table entry by its description."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        result = b.activate_entry(description)
        output({"success": True, "result": result}, ctx, result)
    except Exception as e:
        error_output(str(e), ctx)


@ct.command("deactivate")
@click.argument("description")
@pass_ctx
def ct_deactivate(ctx: CLIContext, description: str) -> None:
    """Deactivate a cheat table entry by its description."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        result = b.deactivate_entry(description)
        output({"success": True, "result": result}, ctx, result)
    except Exception as e:
        error_output(str(e), ctx)


# --- Symbol resolution via CE ---


@bridge.command("resolve")
@click.argument("symbol")
@pass_ctx
def resolve_symbol(ctx: CLIContext, symbol: str) -> None:
    """Resolve a symbol using CE's debug engine (supports PDB)."""
    b = _get_bridge(ctx)
    if not b.connected:
        error_output("Not connected to CE.", ctx)
        return
    try:
        result = b.get_symbol_info(symbol)
        output(
            {"success": True, "symbol": symbol, "address": result},
            ctx,
            f"{symbol} → {result}",
        )
    except Exception as e:
        error_output(str(e), ctx)
