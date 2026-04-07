# Test Plan — cli-anything-cheatengine

## Test Inventory

| Module | Test File | Type | Admin Required |
|--------|-----------|------|----------------|
| `core/table.py` | `test_core.py` | Unit | No |
| `core/session.py` | `test_core.py` | Unit | No |
| `core/scanner.py` | `test_core.py` | Unit (helpers only) | No |
| `core/memory.py` | `test_core.py` | Unit (helpers only) | No |
| `core/assembler.py` | `test_core.py` | Unit | No |
| `core/symbols.py` | `test_core.py` | Unit (helpers only) | No |
| CLI entry point | `test_cli.py` | Integration (CliRunner) | No |

## Unit Test Plan (`test_core.py`)

### table.py
- Load a valid .CT XML file and verify parsed entries
- Save a CheatTable and verify round-trip XML fidelity
- Add entries with various variable types (dword, float, string aliases)
- Remove entries by ID (top-level and nested children)
- Find entries by ID (top-level and nested)
- Freeze / unfreeze entries
- list_entries returns flat dict list
- CheatEntry.to_dict includes all expected keys
- Edge: load nonexistent file raises FileNotFoundError
- Edge: save with no path raises ValueError
- Edge: invalid variable type raises ValueError
- Edge: empty CheatTable round-trips correctly
- Edge: entries with children (groups) round-trip correctly

### session.py
- SessionManager creates session dir and file on init
- status() returns expected keys
- set_attached / set_detached updates state
- set_table records loaded table path
- update_scan records scan state
- push_write adds to undo stack, clears redo
- pop_undo returns last write, moves to redo
- pop_redo returns last undone write, moves to undo
- reset() clears all state
- get_history returns command history
- Undo stack capped at 50 entries
- Session persists across SessionManager instances (same dir)
- MemoryWrite serialization round-trip (to_dict / from_dict)

### scanner.py (no live process needed)
- ScanOption enum values match expected constants
- ScanResult.to_dict formats address as hex
- ScanState.to_dict includes result_count
- _make_comparator: EXACT_VALUE, BIGGER_THAN, SMALLER_THAN, VALUE_BETWEEN
- _make_comparator: INCREASED_VALUE, DECREASED_VALUE, CHANGED, UNCHANGED
- _value_size returns correct sizes for each VarType
- reset_scan returns fresh state

### memory.py (no live process needed)
- VarType enum has all expected members
- parse_address handles 0x prefix, h suffix, plain decimal, hex-like strings
- _STRUCT_FMT covers all numeric VarTypes

### assembler.py
- AssembleResult.to_dict with success=True and success=False
- DisassemblyLine.to_dict formats address as hex
- DisassembleResult.to_dict with success/failure
- assemble() without keystone returns graceful error
- disassemble() without capstone returns graceful error

### symbols.py (helpers only, no live process)
- SymbolInfo.to_dict formats address as hex
- ModuleInfo.to_dict includes human-readable size
- _format_size: bytes, KB, MB formatting

## CLI Integration Test Plan (`test_cli.py`)

All tests use Click's `CliRunner` -- no admin privileges needed.

- `--help` prints usage for root group
- `--version` prints version string
- `table --help` shows subcommands
- `table load <sample.ct>` succeeds with valid file
- `table list-entries <sample.ct>` lists entries
- `table list-entries <sample.ct> --json` outputs JSON
- `table save <sample.ct>` round-trips without error
- `table add-entry` adds entry and saves
- `table remove-entry` removes entry
- `table freeze / unfreeze` toggles frozen state
- `session --help` shows subcommands
- `session status` succeeds
- `session reset` succeeds
- `memory --help` shows subcommands
- `scan --help` shows subcommands
- `asm --help` shows subcommands
- `symbol --help` shows subcommands
- `process --help` shows subcommands
- Error handling: load nonexistent file

## E2E / Workflow Scenarios (manual, requires admin + target process)

1. **Basic value scan**: attach to a process, scan for known int value,
   modify value in-process, next-scan for changed, write new value
2. **Cheat table round-trip**: load .CT, add entry, freeze, save, reload, verify
3. **Undo/redo**: write memory, undo, verify old value restored, redo
4. **Module enumeration**: attach, list modules, resolve symbol address

## Test Results

**Run date:** 2026-04-06
**Platform:** Windows 11 / Python 3.9.13 / pytest 7.1.2
**Duration:** 0.35s

```
104 passed in 0.35s
```

All 104 tests pass:
- 25 CLI integration tests (test_cli.py) — root help/version, 7 command group help, table CRUD, session status/reset/history
- 79 core unit tests (test_core.py) — table load/save/add/remove/find/freeze, session manager lifecycle, scanner comparators, memory parse_address, assembler data classes, symbol helpers
