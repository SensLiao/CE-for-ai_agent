"""Named pipe server for communicating with Cheat Engine.

Python acts as the pipe server (controller). CE Lua connects as a client
via connectToPipe(). Communication uses a simple length-prefixed string
protocol over Windows named pipes via ctypes (no pywin32 dependency).

Protocol:
  Request  (Python → CE):  [4-byte LE length] [UTF-8 Lua code]
  Response (CE → Python):  [1-byte status] [4-byte LE length] [UTF-8 result]
  Status bytes: 0x00 = success, 0x01 = error
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

_k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

# Windows constants
PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_BYTE = 0x00000000
PIPE_READMODE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
PIPE_UNLIMITED_INSTANCES = 255
INVALID_HANDLE_VALUE = -1
ERROR_PIPE_CONNECTED = 535
ERROR_BROKEN_PIPE = 109

# Default buffer sizes
BUFFER_SIZE = 65536
DEFAULT_PIPE_NAME = r"\\.\pipe\cli_anything_ce"


@dataclass
class PipeMessage:
    """A message exchanged over the pipe."""

    success: bool
    data: str

    def to_bytes(self) -> bytes:
        """Serialize for sending (status + length-prefixed string)."""
        encoded = self.data.encode("utf-8")
        status = b"\x00" if self.success else b"\x01"
        return status + struct.pack("<I", len(encoded)) + encoded

    @classmethod
    def from_response_bytes(cls, raw: bytes) -> PipeMessage:
        """Parse a response from CE."""
        if len(raw) < 5:
            return cls(success=False, data="Incomplete response")
        status = raw[0]
        length = struct.unpack("<I", raw[1:5])[0]
        data = raw[5 : 5 + length].decode("utf-8", errors="replace")
        return cls(success=(status == 0), data=data)


class CEPipeServer:
    """Named pipe server that CE Lua connects to.

    Usage:
        server = CEPipeServer()
        server.start()          # starts listening in background thread
        server.wait_for_ce()    # blocks until CE connects
        result = server.execute_lua('return getCEVersion()')
        server.stop()
    """

    def __init__(self, pipe_name: str = DEFAULT_PIPE_NAME) -> None:
        self.pipe_name = pipe_name
        self._pipe_handle: int = INVALID_HANDLE_VALUE
        self._connected = False
        self._lock = threading.Lock()
        self._listen_thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        """Create the named pipe and start listening for CE connection."""
        if self._running:
            return

        self._pipe_handle = _k32.CreateNamedPipeW(
            self.pipe_name,
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            1,  # max instances
            BUFFER_SIZE,
            BUFFER_SIZE,
            0,  # default timeout
            None,  # default security
        )
        if self._pipe_handle == INVALID_HANDLE_VALUE:
            err = ctypes.get_last_error()
            raise OSError(f"CreateNamedPipe failed (error {err})")

        self._running = True

    def wait_for_ce(self, timeout: float = 60.0) -> bool:
        """Block until CE connects to the pipe or timeout.

        Returns True if CE connected, False on timeout.
        """
        if self._connected:
            return True
        if self._pipe_handle == INVALID_HANDLE_VALUE:
            raise RuntimeError("Pipe not started. Call start() first.")

        # ConnectNamedPipe in a thread so we can enforce timeout
        connected_event = threading.Event()

        def _wait_connect() -> None:
            result = _k32.ConnectNamedPipe(self._pipe_handle, None)
            if result or ctypes.get_last_error() == ERROR_PIPE_CONNECTED:
                self._connected = True
                connected_event.set()

        t = threading.Thread(target=_wait_connect, daemon=True)
        t.start()
        connected_event.wait(timeout=timeout)
        return self._connected

    def execute_lua(self, lua_code: str, timeout: float = 30.0) -> PipeMessage:
        """Send Lua code to CE for execution and return the result.

        Args:
            lua_code: Lua code string to execute in CE.
            timeout: Max seconds to wait for response.

        Returns:
            PipeMessage with success status and result data.
        """
        if not self._connected:
            return PipeMessage(success=False, data="CE not connected")

        with self._lock:
            try:
                self._write_command(lua_code)
                return self._read_response(timeout)
            except OSError as e:
                self._connected = False
                return PipeMessage(success=False, data=f"Pipe error: {e}")

    def stop(self) -> None:
        """Disconnect and close the pipe."""
        self._running = False
        self._connected = False
        if self._pipe_handle != INVALID_HANDLE_VALUE:
            _k32.DisconnectNamedPipe(self._pipe_handle)
            _k32.CloseHandle(self._pipe_handle)
            self._pipe_handle = INVALID_HANDLE_VALUE

    def _write_command(self, lua_code: str) -> None:
        """Write a length-prefixed Lua command to the pipe."""
        encoded = lua_code.encode("utf-8")
        header = struct.pack("<I", len(encoded))
        data = header + encoded
        written = wt.DWORD(0)
        ok = _k32.WriteFile(
            self._pipe_handle,
            data,
            len(data),
            ctypes.byref(written),
            None,
        )
        if not ok:
            raise OSError(f"WriteFile failed (error {ctypes.get_last_error()})")

    def _read_response(self, timeout: float = 30.0) -> PipeMessage:
        """Read a status + length-prefixed response from CE."""
        # Read status byte + 4-byte length header
        header = self._read_exact(5, timeout)
        if header is None:
            return PipeMessage(success=False, data="Timeout reading response header")

        status = header[0]
        length = struct.unpack("<I", header[1:5])[0]

        if length == 0:
            return PipeMessage(success=(status == 0), data="")

        if length > 10 * 1024 * 1024:  # 10 MB sanity cap
            return PipeMessage(success=False, data=f"Response too large: {length} bytes")

        body = self._read_exact(length, timeout)
        if body is None:
            return PipeMessage(success=False, data="Timeout reading response body")

        data = body.decode("utf-8", errors="replace")
        return PipeMessage(success=(status == 0), data=data)

    def _read_exact(self, size: int, timeout: float) -> Optional[bytes]:
        """Read exactly `size` bytes from the pipe, with timeout."""
        buf = ctypes.create_string_buffer(size)
        read_bytes = wt.DWORD(0)
        total_read = 0
        deadline = time.monotonic() + timeout

        while total_read < size:
            if time.monotonic() > deadline:
                return None
            remaining = size - total_read
            ok = _k32.ReadFile(
                self._pipe_handle,
                ctypes.cast(ctypes.addressof(buf) + total_read, ctypes.c_void_p),
                remaining,
                ctypes.byref(read_bytes),
                None,
            )
            if not ok:
                err = ctypes.get_last_error()
                if err == ERROR_BROKEN_PIPE:
                    self._connected = False
                    return None
                raise OSError(f"ReadFile failed (error {err})")
            if read_bytes.value == 0:
                return None
            total_read += read_bytes.value

        return buf.raw[:size]

    def __enter__(self) -> CEPipeServer:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def __del__(self) -> None:
        self.stop()
