# CE for AI Agent

A Python CLI tool that replicates [Cheat Engine](https://www.cheatengine.org/)'s core functionality as a command-line interface, designed for AI agent integration via the CLI-Anything skills system.

## Features

### Standalone (no Cheat Engine needed)
- **Process Management** — list, attach, detach processes
- **Memory Operations** — typed read/write/hex dump via Windows API
- **Value Scanning** — first scan + next scan with multiple comparison modes
- **Cheat Table (.CT)** — full XML parse/save/CRUD, compatible with CE format
- **Assembly/Disassembly** — via Keystone/Capstone (optional)
- **Symbol Resolution** — PE export parsing, module+offset lookup

### Bridge Mode (requires running CE)
- **Speedhack** — control game speed
- **Debugger** — breakpoints, stepping
- **Auto Assemble** — execute CE AA scripts
- **PDB Symbols** — resolve debug symbols via CE's engine
- **Cheat Table Activation** — activate/deactivate entries in CE

## Installation

```bash
pip install -e .

# With assembly support
pip install -e ".[asm]"
```

## Usage

```bash
# List processes
cli-anything-cheatengine process list -n notepad

# Attach and scan
cli-anything-cheatengine process attach 12345
cli-anything-cheatengine scan first 100 -t dword
cli-anything-cheatengine scan next 95

# Read/write memory
cli-anything-cheatengine memory read 0x1A2B3C -t dword
cli-anything-cheatengine memory write 0x1A2B3C 999 -t dword

# JSON output for AI agents
cli-anything-cheatengine --json process list
```

## AI Agent Integration

This tool is part of the **CLI-Anything** ecosystem. The skill descriptor at `cli_anything/cheat_engine/skills/SKILL.md` defines triggers and the full command reference for AI agent discovery.

AI agents can invoke any command with `--json` for structured output:
```json
{"success": true, "...": "command-specific fields"}
```

## Requirements

- Windows OS
- Python 3.9+
- Administrator privileges (for memory operations)
- Optional: Cheat Engine 7.x (for bridge mode)

## License

MIT
