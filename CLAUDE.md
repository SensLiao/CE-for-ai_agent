# CE for AI Agent

## Project Overview

Python CLI tool that replicates Cheat Engine's core functionality as a command-line interface, designed to be invoked by AI agents via the CLI-Anything skills system.

**Two-tier architecture:**
- **Standalone** (no CE needed): process attach, memory read/write, value scanning, cheat table management, assembly/disassembly, symbol resolution — all via Python ctypes + kernel32
- **Bridge** (CE required): speedhack, debugger, auto assemble, PDB symbols — via named pipe to a running CE instance

## Quick Start

```bash
pip install -e .
cli-anything-cheatengine --help
```

## Architecture

```
cli_anything/cheat_engine/
  cheat_engine_cli.py     # Click CLI entry point, registers 8 command groups
  core/                   # Business logic (no CLI dependency)
    process.py            # Process list/attach/detach via psutil + kernel32
    memory.py             # Typed read/write/dump via ReadProcessMemory/WriteProcessMemory
    scanner.py            # First/next scan engine with comparators
    session.py            # Undo/redo + session persistence (~/.cli-anything/)
    table.py              # .CT (Cheat Table) XML parse/save/CRUD
    assembler.py          # Keystone/Capstone assembly (optional dep)
    symbols.py            # PE export parsing, module+offset resolution
  commands/               # Click command groups (thin wrappers over core/)
    helpers.py            # CLIContext, output(), error_output()
  bridge/                 # CE integration via Windows named pipe
    pipe_server.py        # Low-level pipe protocol (Python = server, CE = client)
    ce_bridge.py          # High-level bridge API
    ce_lua_client.lua     # Lua script to paste into CE's Lua Engine
  utils/
    ce_backend.py         # ctypes kernel32 wrappers (the only native layer)
  skills/
    SKILL.md              # AI agent skill descriptor (triggers, command ref)
```

## Key Commands

| Group | Purpose |
|-------|---------|
| `process` | list, attach, detach, info |
| `memory` | read, write, dump |
| `scan` | first, next, results, reset |
| `table` | load, save, list-entries, add-entry, remove-entry, freeze, unfreeze |
| `asm` | assemble, disassemble, inject |
| `symbol` | lookup, list-modules |
| `session` | status, history, undo, redo, reset |
| `bridge` | detect, start, status, lua, stop, speed, debug, aa, ct, resolve |

## Testing

```bash
pytest cli_anything/cheat_engine/tests/ -v
```

104 tests, no admin required. Tests mock the kernel32 layer.

## Platform

Windows only (kernel32 ctypes). Python 3.9+.
