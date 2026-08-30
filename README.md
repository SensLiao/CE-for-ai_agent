<div align="right"><a href="README.zh-CN.md">简体中文</a></div>

<p align="center"><img src="docs/hero.png" alt="CE Agent CLI — Cheat-Engine-style process memory analysis as an AI-agent-ready CLI" width="100%"></p>

CE Agent CLI (`cli-anything-cheatengine`) reimplements Cheat Engine's core workflow — process attach, typed memory read/write, value scanning, cheat-table (`.CT`) CRUD, assembly/disassembly, and symbol resolution — as a Windows command-line tool. Every command speaks a `--json` contract designed for AI agents, and an optional named-pipe bridge drives a running Cheat Engine 7.x instance (speedhack, debugger, auto-assemble, PDB symbols) when one is present. It is built for local debugging, security research, and process introspection.

> **Authorised use only.** Attach to and analyse only processes you own or have explicit written permission to inspect. This tool is for local debugging, security research, and process introspection — do not use it to violate any software's terms of service or anti-cheat protections, or any applicable law.

## ✨ Highlights

- **Broad command surface** — 8 command groups and about 30 subcommands covering attach, memory, scanning, `.CT` tables, assembly, and symbols.
- **Agent-ready `--json` contract** — a global `--json` mode on every command produces structured output, plus a `SKILL.md` descriptor so agents can discover its capabilities.
- **98 tests, no admin or target needed** — 79 core + 19 CLI tests all run without administrator rights or a live target process.
- **Typed memory read/write** — typed readers and writers over process memory; value scanning walks only committed memory regions.
- **Symbol resolution** — resolves symbols from PE exports, with optional PDB symbols through the Cheat Engine bridge.
- **Optional assembly/disassembly** — Capstone and Keystone power disassembly and assembly when the `[asm]` extra is installed.
- **Cheat Engine 7.x bridge** — drives speedhack, debugger, and auto-assemble over a named pipe, degrading gracefully when CE is not running.

## 🏗 Architecture

<p align="center"><img src="docs/architecture.png" alt="CE Agent CLI architecture: CLI command groups over a ctypes core, with an optional Cheat Engine bridge" width="100%"></p>
<p align="center"><sub>A self-contained core over the Windows API, plus an optional bridge to a running Cheat Engine 7.x.</sub></p>

The CLI is the whole surface: eight command groups — `process`, `memory`, `scan`, `table`, `asm`, `symbol`, `session`, and `bridge` — sit on top of a core that does process attach, typed memory reads and writes, value scanning over committed regions, `.CT` cheat-table CRUD, assembly and disassembly, and symbol resolution. That core talks to Windows directly through `ctypes`, with no `pywin32` layer in between, which is why the standalone tool has no dependency on Cheat Engine itself.

The dashed path in the diagram is the optional half. When a Cheat Engine 7.x instance is running, the CLI connects to it over a named pipe and gains speedhack, the debugger, auto-assemble, and PDB symbols; when it is not, those features degrade gracefully and everything in the core keeps working. Cutting across both halves is the global `--json` flag: any command can emit structured output instead of human-readable text, which — together with the shipped `SKILL.md` descriptor — is the contract an AI agent drives the tool through.

## 🧰 Tech stack

| Area | Details |
| --- | --- |
| Language | Python ≥ 3.9 |
| OS interface | Windows API via `ctypes` (no `pywin32`) |
| CLI & process | `click`, `psutil` |
| Optional `[asm]` extra | `keystone-engine`, `capstone` |
| Bridge | Cheat Engine 7.x over a named pipe (optional) |

## 🚀 Getting started

Prerequisites: Windows, Python 3.9+, and administrator privileges for live memory operations. Cheat Engine 7.x is optional and only needed for the bridge.

```bash
# Install (core)
pip install -e .

# Or with assembly/disassembly support
pip install -e ".[asm]"

# List processes as JSON
cli-anything-cheatengine --json process list
```

## 🧪 Testing

```bash
pytest
```

98 tests (79 core + 19 CLI) run without administrator rights or a live target process.

## 📄 License

MIT — see the [LICENSE](LICENSE) file.

<p align="center"><sub>Built by <a href="https://github.com/SensLiao">Ruixuan "Sens" Liao</a> · USYD Advanced Computing (Honours)</sub></p>
