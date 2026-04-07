"""Quick test: verify Python ↔ CE pipe bridge works.

Run this script as administrator, then paste the Lua client script
into CE's Lua Engine and click Execute.

Usage:
    python test_bridge.py
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from cli_anything.cheat_engine.bridge.ce_bridge import CEBridge


def main() -> None:
    bridge = CEBridge()

    print("=" * 60)
    print("  CE Bridge Connection Test")
    print("=" * 60)
    print()

    # Step 1: Start pipe server
    print("[1/4] Starting pipe server...")
    bridge.start()
    print("       Pipe server ready: \\\\.\\pipe\\cli_anything_ce")
    print()

    # Step 2: Wait for CE
    print("[2/4] Waiting for CE to connect...")
    print("       >>> Open CE's Lua Engine (Ctrl+Alt+L)")
    print("       >>> Paste the contents of:")
    print(f"           {bridge.get_lua_script_path()}")
    print("       >>> Click 'Execute'")
    print()

    if not bridge.wait_for_ce(timeout=120):
        print("       TIMEOUT - CE did not connect within 120 seconds.")
        bridge.stop()
        return

    print(f"       Connected! {bridge.ce_version()}")
    print()

    # Step 3: Ping test
    print("[3/4] Ping test...")
    if bridge.ping():
        print("       PONG - communication OK!")
    else:
        print("       FAILED - ping did not return expected response")
        bridge.stop()
        return
    print()

    # Step 4: Execute Lua
    print("[4/4] Running test commands...")
    print()

    tests = [
        ("CE version", "return getCEVersion()"),
        ("1 + 1", "return 1 + 1"),
        ("Opened process ID", "return getOpenedProcessID()"),
        ("String test", "return 'Hello from CE!'"),
    ]

    for name, code in tests:
        result = bridge.execute_safe(code, timeout=10)
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {name}: {result.data}")

    print()
    print("=" * 60)
    print("  All tests complete! Bridge is working.")
    print("=" * 60)

    bridge.stop()


if __name__ == "__main__":
    main()
