"""Session state management.

Persists CLI session state (attached process, scan history, undo/redo
stack) as JSON files under a session directory. Enables resuming work
across CLI invocations.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

# Default session directory
DEFAULT_SESSION_DIR = Path.home() / ".cli-anything" / "cheat-engine" / "sessions"


@dataclass
class MemoryWrite:
    """Record of a memory write operation (for undo)."""

    address: int
    old_value: bytes
    new_value: bytes
    var_type: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": f"0x{self.address:X}",
            "old_value": self.old_value.hex(),
            "new_value": self.new_value.hex(),
            "var_type": self.var_type,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryWrite:
        return cls(
            address=int(d["address"], 16) if isinstance(d["address"], str) else d["address"],
            old_value=bytes.fromhex(d["old_value"]),
            new_value=bytes.fromhex(d["new_value"]),
            var_type=d["var_type"],
            timestamp=d.get("timestamp", 0.0),
        )


@dataclass
class SessionState:
    """Serializable session state."""

    session_id: str = ""
    attached_pid: Optional[int] = None
    attached_name: Optional[str] = None
    loaded_table: Optional[str] = None
    scan_active: bool = False
    scan_result_count: int = 0
    undo_stack: list[MemoryWrite] = field(default_factory=list)
    redo_stack: list[MemoryWrite] = field(default_factory=list)
    command_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "attached_pid": self.attached_pid,
            "attached_name": self.attached_name,
            "loaded_table": self.loaded_table,
            "scan_active": self.scan_active,
            "scan_result_count": self.scan_result_count,
            "undo_count": len(self.undo_stack),
            "redo_count": len(self.redo_stack),
            "command_count": len(self.command_history),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SessionManager:
    """Manages session persistence and state transitions."""

    def __init__(self, session_dir: Optional[Path] = None) -> None:
        self.session_dir = session_dir or DEFAULT_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.state = SessionState()
        self._load_or_create()

    def _session_file(self) -> Path:
        return self.session_dir / "current_session.json"

    def _load_or_create(self) -> None:
        """Load existing session or create a new one."""
        sf = self._session_file()
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                self.state = self._deserialize(data)
                return
            except (json.JSONDecodeError, KeyError):
                pass
        self.state = SessionState(
            session_id=f"session_{int(time.time())}",
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._save()

    def _save(self) -> None:
        """Persist current state to disk."""
        self.state.updated_at = time.time()
        data = self._serialize(self.state)
        self._session_file().write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _serialize(self, state: SessionState) -> dict[str, Any]:
        """Serialize state to a JSON-compatible dict."""
        return {
            "session_id": state.session_id,
            "attached_pid": state.attached_pid,
            "attached_name": state.attached_name,
            "loaded_table": state.loaded_table,
            "scan_active": state.scan_active,
            "scan_result_count": state.scan_result_count,
            "undo_stack": [w.to_dict() for w in state.undo_stack],
            "redo_stack": [w.to_dict() for w in state.redo_stack],
            "command_history": state.command_history[-100:],  # keep last 100
            "created_at": state.created_at,
            "updated_at": state.updated_at,
        }

    def _deserialize(self, data: dict[str, Any]) -> SessionState:
        """Deserialize a dict into SessionState."""
        return SessionState(
            session_id=data.get("session_id", ""),
            attached_pid=data.get("attached_pid"),
            attached_name=data.get("attached_name"),
            loaded_table=data.get("loaded_table"),
            scan_active=data.get("scan_active", False),
            scan_result_count=data.get("scan_result_count", 0),
            undo_stack=[MemoryWrite.from_dict(w) for w in data.get("undo_stack", [])],
            redo_stack=[MemoryWrite.from_dict(w) for w in data.get("redo_stack", [])],
            command_history=data.get("command_history", []),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )

    def set_attached(self, pid: int, name: str) -> None:
        """Record that we attached to a process."""
        self.state.attached_pid = pid
        self.state.attached_name = name
        self._add_command("attach", {"pid": pid, "name": name})
        self._save()

    def set_detached(self) -> None:
        """Record that we detached from a process."""
        self._add_command("detach", {
            "pid": self.state.attached_pid,
            "name": self.state.attached_name,
        })
        self.state.attached_pid = None
        self.state.attached_name = None
        self._save()

    def set_table(self, path: Optional[str]) -> None:
        """Record loaded cheat table path."""
        self.state.loaded_table = path
        self._save()

    def update_scan(self, active: bool, result_count: int = 0) -> None:
        """Update scan state."""
        self.state.scan_active = active
        self.state.scan_result_count = result_count
        self._save()

    def push_write(self, write: MemoryWrite) -> None:
        """Record a memory write for undo support."""
        self.state.undo_stack.append(write)
        self.state.redo_stack.clear()  # new write invalidates redo
        # Cap undo stack at 50 entries
        if len(self.state.undo_stack) > 50:
            self.state.undo_stack = self.state.undo_stack[-50:]
        self._save()

    def pop_undo(self) -> Optional[MemoryWrite]:
        """Pop the last write from the undo stack (for undo)."""
        if not self.state.undo_stack:
            return None
        write = self.state.undo_stack.pop()
        self.state.redo_stack.append(write)
        self._save()
        return write

    def pop_redo(self) -> Optional[MemoryWrite]:
        """Pop from the redo stack (for redo)."""
        if not self.state.redo_stack:
            return None
        write = self.state.redo_stack.pop()
        self.state.undo_stack.append(write)
        self._save()
        return write

    def get_history(self, count: int = 20) -> list[dict[str, Any]]:
        """Get the last N commands from history."""
        return self.state.command_history[-count:]

    def reset(self) -> None:
        """Reset the session to a clean state."""
        self.state = SessionState(
            session_id=f"session_{int(time.time())}",
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._save()

    def status(self) -> dict[str, Any]:
        """Return current session status as a dict."""
        return self.state.to_dict()

    def _add_command(self, cmd: str, args: dict[str, Any]) -> None:
        """Add a command to history."""
        self.state.command_history.append({
            "command": cmd,
            "args": args,
            "timestamp": time.time(),
        })
