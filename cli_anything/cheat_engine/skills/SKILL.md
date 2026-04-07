---
name: cheat-engine
description: Memory inspection, scanning, and cheat table management for Windows processes
version: 0.2.0
cli: cli-anything-cheatengine
triggers:
  - memory scan
  - cheat table
  - cheat engine
  - process memory
  - memory hack
  - game trainer
  - speedhack
  - debugger
  - auto assemble
---

# Cheat Engine CLI Skill

Standalone CLI for Windows process memory inspection, value scanning, cheat table (.CT) management, assembly/disassembly, and symbol resolution. Uses native Windows API via ctypes -- no Cheat Engine installation required.

When Cheat Engine is running and connected via the bridge, advanced features (speedhack, debugger, auto assemble, PDB symbols, kernel access) are also available. **If CE is not running, all bridge commands are unavailable — only the standalone Python features work.** Use `bridge detect` to check whether CE is running.

## Prerequisites

- Windows OS (uses kernel32 via ctypes)
- Administrator privileges for process attach/memory operations
- Python 3.9+
- Optional: `keystone-engine` for assembly, `capstone` for disassembly
- Optional: Cheat Engine 7.x installed for advanced features

## Installation

```bash
pip install -e path/to/cheat-engine
```

## Global Options

| Flag | Description |
|------|-------------|
| `--json` | Output all results as JSON |
| `--version` | Show version |
| `--help` | Show help |

---

## Standalone Commands (no CE needed)

### process -- Process Management

```bash
cli-anything-cheatengine process list [-n NAME] [--limit N]
cli-anything-cheatengine process attach PID
cli-anything-cheatengine process detach
cli-anything-cheatengine process info PID
```

### memory -- Memory Read/Write/Dump

```bash
# Read a typed value at ADDRESS
cli-anything-cheatengine memory read ADDRESS [-t TYPE] [--pid PID]
# TYPE: byte, word, dword, qword, float, double, string

# Write a value to ADDRESS
cli-anything-cheatengine memory write ADDRESS VALUE [-t TYPE] [--pid PID]

# Hex dump memory
cli-anything-cheatengine memory dump ADDRESS [-s SIZE] [--pid PID]
```

### scan -- Memory Scanning

```bash
cli-anything-cheatengine scan first VALUE [-t TYPE] [-m MODE] [--upper N] [--pid PID]
cli-anything-cheatengine scan next [VALUE] [-m MODE] [--upper N] [--pid PID]
cli-anything-cheatengine scan results [--limit N] [--offset N]
cli-anything-cheatengine scan reset
```

### table -- Cheat Table (.CT) Management

```bash
cli-anything-cheatengine table load PATH
cli-anything-cheatengine table save PATH [-o OUTPUT]
cli-anything-cheatengine table list-entries PATH
cli-anything-cheatengine table add-entry PATH -d DESC -a ADDRESS [-t TYPE] [-v VALUE] [--frozen]
cli-anything-cheatengine table remove-entry PATH ENTRY_ID
cli-anything-cheatengine table freeze PATH ENTRY_ID
cli-anything-cheatengine table unfreeze PATH ENTRY_ID
```

### asm -- Assembly / Disassembly

```bash
cli-anything-cheatengine asm assemble CODE [--address ADDR] [--x86]
cli-anything-cheatengine asm disassemble ADDRESS [-c COUNT] [--x86] [--pid PID]
cli-anything-cheatengine asm inject CODE [--x86] [--pid PID]
```

### symbol -- Symbol Resolution

```bash
cli-anything-cheatengine symbol lookup NAME [--pid PID]
cli-anything-cheatengine symbol list-modules [--pid PID]
```

### session -- Session State

```bash
cli-anything-cheatengine session status
cli-anything-cheatengine session history [-n COUNT]
cli-anything-cheatengine session undo [--pid PID]
cli-anything-cheatengine session redo [--pid PID]
cli-anything-cheatengine session reset
```

---

## Bridge Commands (requires CE running + connected)

> **If CE is not running, these commands are unavailable.** Use `bridge detect` to check.

### bridge -- Connection Management

```bash
# Detect if Cheat Engine is running (no connection needed)
cli-anything-cheatengine bridge detect

# Start pipe server and wait for CE to connect
cli-anything-cheatengine bridge start [--timeout 120]

# Check connection status
cli-anything-cheatengine bridge status

# Execute arbitrary Lua code in CE
cli-anything-cheatengine bridge lua "return getCEVersion()"

# Disconnect
cli-anything-cheatengine bridge stop
```

### bridge speed -- Speedhack

```bash
cli-anything-cheatengine bridge speed set 2.0    # double speed
cli-anything-cheatengine bridge speed set 0.5    # half speed
cli-anything-cheatengine bridge speed reset       # normal speed
```

### bridge debug -- Debugger

```bash
cli-anything-cheatengine bridge debug break ADDRESS
cli-anything-cheatengine bridge debug remove ADDRESS
cli-anything-cheatengine bridge debug continue
```

### bridge aa -- Auto Assemble

```bash
cli-anything-cheatengine bridge aa script.asm
```

### bridge ct -- Cheat Table via CE

```bash
cli-anything-cheatengine bridge ct activate "Health"
cli-anything-cheatengine bridge ct deactivate "Health"
```

### bridge resolve -- PDB Symbol Resolution

```bash
cli-anything-cheatengine bridge resolve "kernel32.CreateFileW"
```

---

## Typical Workflows

### Find and modify a game value (standalone, no CE needed)

```bash
cli-anything-cheatengine process list -n game
cli-anything-cheatengine process attach 12345
cli-anything-cheatengine scan first 100 -t dword
# change value in game...
cli-anything-cheatengine scan next 95 -m exact
cli-anything-cheatengine scan results
cli-anything-cheatengine memory write 0x1A2B3C 999 -t dword
cli-anything-cheatengine table add-entry my.ct -d "Health" -a 0x1A2B3C -t dword -v 999 --frozen
```

### Use CE advanced features (requires CE)

```bash
# Check if CE is running
cli-anything-cheatengine bridge detect

# Connect to CE
cli-anything-cheatengine bridge start

# Speedhack
cli-anything-cheatengine bridge speed set 3.0

# Set breakpoint
cli-anything-cheatengine bridge debug break "game.exe+0x1234"

# Execute auto assemble script
cli-anything-cheatengine bridge aa trainer.asm

# Disconnect
cli-anything-cheatengine bridge stop
```

## JSON Output

All commands support `--json` for structured output:

```json
{"success": true, "...": "command-specific fields"}
{"success": false, "error": "description"}
```
