"""Unit tests for core modules — no admin privileges or live processes required."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# table.py
# ---------------------------------------------------------------------------
from cli_anything.cheat_engine.core.table import (
    CheatEntry,
    CheatTable,
    VARTYPE_ALIASES,
    _resolve_vartype,
    add_entry,
    find_entry,
    freeze_entry,
    list_entries,
    load_table,
    remove_entry,
    save_table,
    unfreeze_entry,
)


class TestCheatEntry:
    def test_to_dict_basic(self):
        e = CheatEntry(id=0, description="HP", variable_type="4 Bytes", address="0x100")
        d = e.to_dict()
        assert d["id"] == 0
        assert d["description"] == "HP"
        assert d["variable_type"] == "4 Bytes"
        assert d["address"] == "0x100"
        assert d["frozen"] is False
        assert "value" not in d  # value is None

    def test_to_dict_with_value_and_frozen(self):
        e = CheatEntry(id=1, description="MP", value="50", frozen=True)
        d = e.to_dict()
        assert d["value"] == "50"
        assert d["frozen"] is True

    def test_to_dict_with_children(self):
        child = CheatEntry(id=2, description="Child")
        parent = CheatEntry(id=1, description="Group", group=True, children=[child])
        d = parent.to_dict()
        assert d["group"] is True
        assert len(d["children"]) == 1
        assert d["children"][0]["description"] == "Child"


class TestCheatTable:
    def test_to_dict_empty(self):
        t = CheatTable()
        d = t.to_dict()
        assert d["source"] is None
        assert d["entry_count"] == 0
        assert d["entries"] == []


class TestResolveVartype:
    def test_canonical_names(self):
        assert _resolve_vartype("4 Bytes") == "4 Bytes"
        assert _resolve_vartype("Float") == "Float"
        assert _resolve_vartype("Double") == "Double"

    def test_aliases(self):
        assert _resolve_vartype("dword") == "4 Bytes"
        assert _resolve_vartype("int") == "4 Bytes"
        assert _resolve_vartype("float") == "Float"
        assert _resolve_vartype("qword") == "8 Bytes"
        assert _resolve_vartype("byte") == "Byte"
        assert _resolve_vartype("word") == "2 Bytes"
        assert _resolve_vartype("aob") == "Array of byte"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown variable type"):
            _resolve_vartype("invalid_type")


class TestLoadTable:
    def test_load_sample(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert len(t.entries) == 3
        assert t.source_path == tmp_ct_file
        assert t.entries[0].description == "Health"
        assert t.entries[0].frozen is True
        assert t.entries[0].variable_type == "4 Bytes"
        assert t.entries[1].description == "Mana"
        assert t.entries[1].variable_type == "Float"

    def test_load_with_children(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        group = t.entries[2]
        assert group.description == "Stats Group"
        assert group.group is True
        assert len(group.children) == 1
        assert group.children[0].description == "Strength"

    def test_load_empty(self, tmp_empty_ct: Path):
        t = load_table(tmp_empty_ct)
        assert len(t.entries) == 0

    def test_load_nonexistent(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_table(tmp_path / "nope.ct")

    def test_next_id_after_load(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        # load_table only tracks max ID from top-level entries (0,1,2)
        # child IDs are not included in the top-level max scan
        assert t._next_id == 3


class TestSaveTable:
    def test_round_trip(self, tmp_ct_file: Path, tmp_path: Path):
        t = load_table(tmp_ct_file)
        out = tmp_path / "out.ct"
        save_table(t, out)
        t2 = load_table(out)
        assert len(t2.entries) == len(t.entries)
        assert t2.entries[0].description == t.entries[0].description
        assert t2.entries[0].frozen == t.entries[0].frozen

    def test_save_default_path(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        save_table(t)  # uses source_path
        t2 = load_table(tmp_ct_file)
        assert len(t2.entries) == len(t.entries)

    def test_save_no_path_raises(self):
        t = CheatTable()
        with pytest.raises(ValueError, match="No output path"):
            save_table(t)

    def test_round_trip_with_children(self, tmp_ct_file: Path, tmp_path: Path):
        t = load_table(tmp_ct_file)
        out = tmp_path / "out2.ct"
        save_table(t, out)
        t2 = load_table(out)
        assert len(t2.entries[2].children) == 1
        assert t2.entries[2].children[0].description == "Strength"


class TestAddEntry:
    def test_add_basic(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        initial = len(t.entries)
        e = add_entry(t, "Stamina", "game.exe+3000", "dword", "75")
        assert len(t.entries) == initial + 1
        assert e.description == "Stamina"
        assert e.variable_type == "4 Bytes"
        assert e.value == "75"
        assert e.id == 3  # next after top-level max 0,1,2

    def test_add_frozen(self, tmp_empty_ct: Path):
        t = load_table(tmp_empty_ct)
        e = add_entry(t, "HP", "0x100", frozen=True)
        assert e.frozen is True

    def test_add_increments_id(self, tmp_empty_ct: Path):
        t = load_table(tmp_empty_ct)
        e1 = add_entry(t, "A", "0x1")
        e2 = add_entry(t, "B", "0x2")
        assert e2.id == e1.id + 1


class TestRemoveEntry:
    def test_remove_top_level(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        removed = remove_entry(t, 0)
        assert removed is not None
        assert removed.description == "Health"
        assert find_entry(t, 0) is None

    def test_remove_child(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        removed = remove_entry(t, 3)
        assert removed is not None
        assert removed.description == "Strength"
        assert len(t.entries[2].children) == 0

    def test_remove_nonexistent(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert remove_entry(t, 999) is None


class TestFindEntry:
    def test_find_top_level(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        e = find_entry(t, 1)
        assert e is not None
        assert e.description == "Mana"

    def test_find_child(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        e = find_entry(t, 3)
        assert e is not None
        assert e.description == "Strength"

    def test_find_nonexistent(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert find_entry(t, 999) is None


class TestFreezeUnfreeze:
    def test_freeze(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert t.entries[1].frozen is False
        assert freeze_entry(t, 1) is True
        assert t.entries[1].frozen is True

    def test_unfreeze(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert t.entries[0].frozen is True
        assert unfreeze_entry(t, 0) is True
        assert t.entries[0].frozen is False

    def test_freeze_nonexistent(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert freeze_entry(t, 999) is False

    def test_unfreeze_nonexistent(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        assert unfreeze_entry(t, 999) is False


class TestListEntries:
    def test_list(self, tmp_ct_file: Path):
        t = load_table(tmp_ct_file)
        entries = list_entries(t)
        assert len(entries) == 3
        assert all(isinstance(e, dict) for e in entries)
        assert entries[0]["description"] == "Health"


# ---------------------------------------------------------------------------
# session.py
# ---------------------------------------------------------------------------
from cli_anything.cheat_engine.core.session import (
    MemoryWrite,
    SessionManager,
    SessionState,
)


class TestMemoryWrite:
    def test_round_trip(self):
        w = MemoryWrite(
            address=0x1000,
            old_value=b"\x64\x00\x00\x00",
            new_value=b"\xC8\x00\x00\x00",
            var_type="dword",
            timestamp=1000.0,
        )
        d = w.to_dict()
        assert d["address"] == "0x1000"
        assert d["old_value"] == "64000000"
        assert d["new_value"] == "c8000000"

        w2 = MemoryWrite.from_dict(d)
        assert w2.address == 0x1000
        assert w2.old_value == b"\x64\x00\x00\x00"
        assert w2.new_value == b"\xC8\x00\x00\x00"
        assert w2.var_type == "dword"


class TestSessionState:
    def test_to_dict(self):
        s = SessionState(session_id="test_1")
        d = s.to_dict()
        assert d["session_id"] == "test_1"
        assert d["attached_pid"] is None
        assert d["undo_count"] == 0
        assert d["redo_count"] == 0


class TestSessionManager:
    def test_creates_session(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        assert sm.state.session_id.startswith("session_")
        assert (tmp_session_dir / "current_session.json").exists()

    def test_status(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        s = sm.status()
        assert "session_id" in s
        assert "attached_pid" in s

    def test_set_attached_detached(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        sm.set_attached(1234, "game.exe")
        assert sm.state.attached_pid == 1234
        assert sm.state.attached_name == "game.exe"

        sm.set_detached()
        assert sm.state.attached_pid is None
        assert sm.state.attached_name is None

    def test_set_table(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        sm.set_table("C:/test.ct")
        assert sm.state.loaded_table == "C:/test.ct"

    def test_update_scan(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        sm.update_scan(True, 42)
        assert sm.state.scan_active is True
        assert sm.state.scan_result_count == 42

    def test_push_write_and_undo(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        w = MemoryWrite(0x100, b"\x01", b"\x02", "byte")
        sm.push_write(w)
        assert len(sm.state.undo_stack) == 1
        assert len(sm.state.redo_stack) == 0

        popped = sm.pop_undo()
        assert popped is not None
        assert popped.address == 0x100
        assert len(sm.state.undo_stack) == 0
        assert len(sm.state.redo_stack) == 1

    def test_pop_redo(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        w = MemoryWrite(0x200, b"\x03", b"\x04", "byte")
        sm.push_write(w)
        sm.pop_undo()

        popped = sm.pop_redo()
        assert popped is not None
        assert popped.address == 0x200
        assert len(sm.state.undo_stack) == 1
        assert len(sm.state.redo_stack) == 0

    def test_push_write_clears_redo(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        sm.push_write(MemoryWrite(0x1, b"\x01", b"\x02", "byte"))
        sm.pop_undo()
        assert len(sm.state.redo_stack) == 1
        sm.push_write(MemoryWrite(0x2, b"\x03", b"\x04", "byte"))
        assert len(sm.state.redo_stack) == 0

    def test_undo_stack_capped(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        for i in range(60):
            sm.push_write(MemoryWrite(i, b"\x00", b"\x01", "byte"))
        assert len(sm.state.undo_stack) == 50

    def test_pop_undo_empty(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        assert sm.pop_undo() is None

    def test_pop_redo_empty(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        assert sm.pop_redo() is None

    def test_reset(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        sm.set_attached(111, "x.exe")
        sm.push_write(MemoryWrite(0x1, b"\x00", b"\x01", "byte"))
        sm.reset()
        assert sm.state.attached_pid is None
        assert len(sm.state.undo_stack) == 0

    def test_get_history(self, tmp_session_dir: Path):
        sm = SessionManager(session_dir=tmp_session_dir)
        sm.set_attached(1, "a.exe")
        sm.set_detached()
        h = sm.get_history()
        assert len(h) == 2
        assert h[0]["command"] == "attach"
        assert h[1]["command"] == "detach"

    def test_persistence(self, tmp_session_dir: Path):
        sm1 = SessionManager(session_dir=tmp_session_dir)
        sm1.set_attached(999, "persist.exe")
        sid = sm1.state.session_id

        sm2 = SessionManager(session_dir=tmp_session_dir)
        assert sm2.state.session_id == sid
        assert sm2.state.attached_pid == 999
        assert sm2.state.attached_name == "persist.exe"


# ---------------------------------------------------------------------------
# scanner.py (helpers only — no live process)
# ---------------------------------------------------------------------------
from cli_anything.cheat_engine.core.scanner import (
    ScanOption,
    ScanResult,
    ScanState,
    _make_comparator,
    _value_size,
    reset_scan,
)
from cli_anything.cheat_engine.core.memory import VarType


class TestScanOption:
    def test_values(self):
        assert ScanOption.EXACT_VALUE == 1
        assert ScanOption.VALUE_BETWEEN == 2
        assert ScanOption.BIGGER_THAN == 3
        assert ScanOption.SMALLER_THAN == 4
        assert ScanOption.UNCHANGED == 10


class TestScanResult:
    def test_to_dict(self):
        r = ScanResult(address=0xDEAD, value=42)
        d = r.to_dict()
        assert d["address"] == "0xDEAD"
        assert d["value"] == 42
        assert "previous_value" not in d

    def test_to_dict_with_previous(self):
        r = ScanResult(address=0xBEEF, value=10, previous_value=5)
        d = r.to_dict()
        assert d["previous_value"] == 5


class TestScanState:
    def test_to_dict(self):
        s = ScanState(var_type=VarType.DWORD, scan_count=2)
        d = s.to_dict()
        assert d["var_type"] == "DWORD"
        assert d["result_count"] == 0
        assert d["scan_count"] == 2


class TestMakeComparator:
    def test_exact(self):
        cmp = _make_comparator(ScanOption.EXACT_VALUE, 42)
        assert cmp(42, None) is True
        assert cmp(43, None) is False

    def test_bigger(self):
        cmp = _make_comparator(ScanOption.BIGGER_THAN, 10)
        assert cmp(11, None) is True
        assert cmp(10, None) is False

    def test_smaller(self):
        cmp = _make_comparator(ScanOption.SMALLER_THAN, 10)
        assert cmp(9, None) is True
        assert cmp(10, None) is False

    def test_between(self):
        cmp = _make_comparator(ScanOption.VALUE_BETWEEN, 5, 15)
        assert cmp(10, None) is True
        assert cmp(5, None) is True
        assert cmp(15, None) is True
        assert cmp(4, None) is False
        assert cmp(16, None) is False

    def test_increased(self):
        cmp = _make_comparator(ScanOption.INCREASED_VALUE)
        assert cmp(10, 5) is True
        assert cmp(5, 10) is False
        assert cmp(10, None) is False

    def test_decreased(self):
        cmp = _make_comparator(ScanOption.DECREASED_VALUE)
        assert cmp(5, 10) is True
        assert cmp(10, 5) is False

    def test_changed(self):
        cmp = _make_comparator(ScanOption.CHANGED)
        assert cmp(10, 5) is True
        assert cmp(5, 5) is False

    def test_unchanged(self):
        cmp = _make_comparator(ScanOption.UNCHANGED)
        assert cmp(5, 5) is True
        assert cmp(10, 5) is False


class TestValueSize:
    def test_sizes(self):
        assert _value_size(VarType.BYTE) == 1
        assert _value_size(VarType.WORD) == 2
        assert _value_size(VarType.DWORD) == 4
        assert _value_size(VarType.QWORD) == 8
        assert _value_size(VarType.SINGLE) == 4
        assert _value_size(VarType.DOUBLE) == 8


class TestResetScan:
    def test_fresh_state(self):
        s = reset_scan()
        assert s.scan_count == 0
        assert len(s.results) == 0
        assert s.last_scan_option is None


# ---------------------------------------------------------------------------
# memory.py (helpers only — no live process)
# ---------------------------------------------------------------------------
from cli_anything.cheat_engine.core.memory import (
    VarType as VT,
    _STRUCT_FMT,
    parse_address,
)


class TestParseAddress:
    def test_hex_prefix(self):
        assert parse_address("0x1A2B") == 0x1A2B

    def test_hex_suffix(self):
        assert parse_address("1A2Bh") == 0x1A2B

    def test_plain_decimal(self):
        assert parse_address("1000") == 1000

    def test_hex_like(self):
        # Contains A-F characters, should parse as hex
        assert parse_address("DEAD") == 0xDEAD

    def test_whitespace_stripped(self):
        assert parse_address("  0xFF  ") == 0xFF


class TestStructFmt:
    def test_all_numeric_types_covered(self):
        for vt in (VT.BYTE, VT.WORD, VT.DWORD, VT.QWORD, VT.SINGLE, VT.DOUBLE):
            assert vt in _STRUCT_FMT
            fmt, size = _STRUCT_FMT[vt]
            assert struct.calcsize(fmt) == size

    def test_string_not_in_struct_fmt(self):
        assert VT.STRING not in _STRUCT_FMT
        assert VT.BYTE_ARRAY not in _STRUCT_FMT


# ---------------------------------------------------------------------------
# assembler.py
# ---------------------------------------------------------------------------
from cli_anything.cheat_engine.core.assembler import (
    AssembleResult,
    DisassemblyLine,
    DisassembleResult,
    assemble,
    disassemble,
)


class TestAssembleResult:
    def test_success_dict(self):
        r = AssembleResult(success=True, bytecode=b"\x90\x90")
        d = r.to_dict()
        assert d["success"] is True
        assert d["bytecode"] == "9090"
        assert d["size"] == 2

    def test_failure_dict(self):
        r = AssembleResult(success=False, error="bad code")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "bad code"


class TestDisassemblyLine:
    def test_to_dict(self):
        line = DisassemblyLine(
            address=0x401000, mnemonic="nop", op_str="",
            bytes_hex="90", size=1,
        )
        d = line.to_dict()
        assert d["address"] == "0x401000"
        assert d["mnemonic"] == "nop"


class TestDisassembleResult:
    def test_success(self):
        line = DisassemblyLine(0x0, "nop", "", "90", 1)
        r = DisassembleResult(success=True, instructions=[line])
        d = r.to_dict()
        assert d["success"] is True
        assert d["count"] == 1

    def test_failure(self):
        r = DisassembleResult(success=False, instructions=[], error="no capstone")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "no capstone"


class TestAssembleDisassemble:
    def test_assemble_without_keystone(self, monkeypatch):
        """If keystone is not installed, assemble returns a graceful error."""
        import cli_anything.cheat_engine.core.assembler as asm_mod
        monkeypatch.setattr(asm_mod, "_get_keystone", lambda: None)
        r = assemble("nop")
        assert r.success is False
        assert "keystone-engine" in r.error

    def test_disassemble_without_capstone(self, monkeypatch):
        """If capstone is not installed, disassemble returns a graceful error."""
        import cli_anything.cheat_engine.core.assembler as asm_mod
        monkeypatch.setattr(asm_mod, "_get_capstone", lambda: None)
        r = disassemble(b"\x90")
        assert r.success is False
        assert "capstone" in r.error


# ---------------------------------------------------------------------------
# symbols.py (helpers only)
# ---------------------------------------------------------------------------
from cli_anything.cheat_engine.core.symbols import (
    ModuleInfo,
    SymbolInfo,
    _format_size,
)


class TestSymbolInfo:
    def test_to_dict(self):
        s = SymbolInfo(name="CreateFileA", address=0x7FF00000, module="kernel32.dll", ordinal=5)
        d = s.to_dict()
        assert d["address"] == "0x7FF00000"
        assert d["name"] == "CreateFileA"
        assert d["module"] == "kernel32.dll"
        assert d["ordinal"] == 5


class TestModuleInfo:
    def test_to_dict(self):
        m = ModuleInfo(name="game.exe", base_address=0x400000, size=1048576, path="C:\\game.exe")
        d = m.to_dict()
        assert d["base_address"] == "0x400000"
        assert d["size"] == 1048576
        assert "1.0 MB" in d["size_readable"]


class TestFormatSize:
    def test_bytes(self):
        assert _format_size(500) == "500 B"

    def test_kb(self):
        assert _format_size(2048) == "2.0 KB"

    def test_mb(self):
        assert _format_size(5 * 1024 * 1024) == "5.0 MB"
