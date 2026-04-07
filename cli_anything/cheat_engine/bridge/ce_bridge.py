"""High-level bridge to Cheat Engine.

Manages the pipe server lifecycle and provides a clean Python API
for executing Lua commands in the running CE instance.

Usage:
    from cli_anything.cheat_engine.bridge.ce_bridge import CEBridge

    bridge = CEBridge()
    bridge.start()
    # ... user pastes Lua client script into CE ...
    bridge.wait_for_ce()
    version = bridge.ce_version()
    bridge.speedhack(2.0)
    bridge.stop()
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .pipe_server import CEPipeServer, PipeMessage

# Path to the Lua client script shipped with this package
LUA_CLIENT_SCRIPT = Path(__file__).parent / "ce_lua_client.lua"


class CEBridgeError(Exception):
    """Raised when a CE bridge operation fails."""


class CEBridge:
    """High-level interface to a connected Cheat Engine instance."""

    def __init__(self, pipe_name: str = r"\\.\pipe\cli_anything_ce") -> None:
        self._server = CEPipeServer(pipe_name)
        self._ce_version: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._server.connected

    def start(self) -> None:
        """Start the pipe server and wait for CE to connect."""
        self._server.start()

    def wait_for_ce(self, timeout: float = 120.0) -> bool:
        """Wait for CE to connect. Returns True on success."""
        if not self._server.wait_for_ce(timeout):
            return False

        # Read the hello message CE sends on connect
        hello = self._server._read_response(timeout=10.0)
        if hello.success and hello.data.startswith("CE "):
            self._ce_version = hello.data
        return True

    def stop(self) -> None:
        """Disconnect and stop the pipe server."""
        if self._server.connected:
            try:
                self._server.execute_lua("__QUIT__", timeout=3.0)
            except Exception:
                pass
        self._server.stop()

    def get_lua_script(self) -> str:
        """Return the Lua client script that should be pasted into CE."""
        return LUA_CLIENT_SCRIPT.read_text(encoding="utf-8")

    def get_lua_script_path(self) -> Path:
        """Return the path to the Lua client script."""
        return LUA_CLIENT_SCRIPT

    # --- Core API ---

    def execute(self, lua_code: str, timeout: float = 30.0) -> str:
        """Execute arbitrary Lua code in CE and return the result string.

        Raises CEBridgeError on failure.
        """
        result = self._server.execute_lua(lua_code, timeout)
        if not result.success:
            raise CEBridgeError(result.data)
        return result.data

    def execute_safe(self, lua_code: str, timeout: float = 30.0) -> PipeMessage:
        """Execute Lua code and return the raw PipeMessage (no exception)."""
        return self._server.execute_lua(lua_code, timeout)

    def ping(self) -> bool:
        """Check if CE is still responsive."""
        result = self._server.execute_lua("__PING__", timeout=5.0)
        return result.success and result.data == "PONG"

    def ce_version(self) -> str:
        """Get the CE version string."""
        if self._ce_version:
            return self._ce_version
        return self.execute("return getCEVersion()")

    # --- Process ---

    def open_process(self, pid_or_name: str) -> str:
        """Open a process in CE by PID or name."""
        return self.execute(f"openProcess('{pid_or_name}')\nreturn 'ok'")

    def get_opened_process_id(self) -> str:
        """Get the PID of the currently opened process in CE."""
        return self.execute("return getOpenedProcessID()")

    # --- Speedhack ---

    def speedhack_enable(self) -> str:
        """Enable the speedhack."""
        return self.execute("speedhack_setSpeed(1.0)\nreturn 'enabled'")

    def speedhack_set_speed(self, speed: float) -> str:
        """Set the speedhack multiplier."""
        return self.execute(f"speedhack_setSpeed({speed})\nreturn 'speed set to {speed}'")

    def speedhack_disable(self) -> str:
        """Disable the speedhack (restore normal speed)."""
        return self.execute("speedhack_setSpeed(1.0)\nreturn 'disabled'")

    # --- Debugger ---

    def set_breakpoint(self, address: str) -> str:
        """Set a breakpoint at the given address."""
        return self.execute(
            f"debug_setBreakpoint('{address}')\nreturn 'breakpoint set at {address}'"
        )

    def remove_breakpoint(self, address: str) -> str:
        """Remove a breakpoint."""
        return self.execute(
            f"debug_removeBreakpoint('{address}')\nreturn 'breakpoint removed'"
        )

    def continue_from_breakpoint(self) -> str:
        """Continue execution from a breakpoint."""
        return self.execute(
            "debug_continueFromBreakpoint('cycf_continue')\nreturn 'continued'"
        )

    # --- Auto Assemble ---

    def auto_assemble(self, script: str) -> str:
        """Execute a CE Auto Assemble script."""
        escaped = script.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        return self.execute(
            f"local ok, info = autoAssemble('{escaped}')\n"
            f"if ok then return 'success' else return 'failed' end"
        )

    # --- Pointer Scan ---

    def create_pointer_map(self) -> str:
        """Create a pointer map for the current process."""
        return self.execute(
            "local pm = generatePointermap()\nreturn 'pointer map generated'"
        )

    # --- Symbol Resolution (via CE's debug engine) ---

    def get_symbol_info(self, symbol: str) -> str:
        """Resolve a symbol using CE's symbol engine (includes PDB)."""
        return self.execute(f"return getAddress('{symbol}')")

    # --- Cheat Table ---

    def activate_entry(self, description: str) -> str:
        """Activate a cheat table entry by description."""
        return self.execute(
            f"local al = getAddressList()\n"
            f"for i=0, al.Count-1 do\n"
            f"  if al[i].Description == '{description}' then\n"
            f"    al[i].Active = true\n"
            f"    return 'activated: {description}'\n"
            f"  end\n"
            f"end\n"
            f"return 'not found: {description}'"
        )

    def deactivate_entry(self, description: str) -> str:
        """Deactivate a cheat table entry by description."""
        return self.execute(
            f"local al = getAddressList()\n"
            f"for i=0, al.Count-1 do\n"
            f"  if al[i].Description == '{description}' then\n"
            f"    al[i].Active = false\n"
            f"    return 'deactivated: {description}'\n"
            f"  end\n"
            f"end\n"
            f"return 'not found: {description}'"
        )

    def __enter__(self) -> CEBridge:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
