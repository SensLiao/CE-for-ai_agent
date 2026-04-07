"""CLI integration tests using Click's CliRunner.

No admin privileges or running processes required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli_anything.cheat_engine.cheat_engine_cli import cli
from .conftest import SAMPLE_CT_XML


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_ct(tmp_path: Path) -> Path:
    ct = tmp_path / "sample.ct"
    ct.write_text(SAMPLE_CT_XML, encoding="utf-8")
    return ct


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


class TestRootGroup:
    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "CLI-Anything Cheat Engine harness" in result.output

    def test_version(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output


# ---------------------------------------------------------------------------
# Command group help
# ---------------------------------------------------------------------------


class TestCommandGroupHelp:
    @pytest.mark.parametrize("group", [
        "table", "session", "memory", "scan", "asm", "symbol", "process",
    ])
    def test_group_help(self, runner: CliRunner, group: str):
        result = runner.invoke(cli, [group, "--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output


# ---------------------------------------------------------------------------
# Table commands
# ---------------------------------------------------------------------------


class TestTableLoad:
    def test_load_success(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["table", "load", str(sample_ct)])
        assert result.exit_code == 0
        assert "3 entries" in result.output or "Loaded" in result.output

    def test_load_json(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["--json", "table", "load", str(sample_ct)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["entry_count"] == 3

    def test_load_nonexistent(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(cli, ["table", "load", str(tmp_path / "nope.ct")])
        # Click validates path existence before the command runs
        assert result.exit_code != 0


class TestTableListEntries:
    def test_list(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["table", "list-entries", str(sample_ct)])
        assert result.exit_code == 0
        assert "Health" in result.output
        assert "Mana" in result.output

    def test_list_json(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["--json", "table", "list-entries", str(sample_ct)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["entries"]) == 3


class TestTableSave:
    def test_save_overwrite(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["table", "save", str(sample_ct)])
        assert result.exit_code == 0
        assert "Saved" in result.output or "success" in result.output

    def test_save_to_new_path(self, runner: CliRunner, sample_ct: Path, tmp_path: Path):
        out = tmp_path / "copy.ct"
        result = runner.invoke(cli, ["table", "save", str(sample_ct), "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()


class TestTableAddEntry:
    def test_add(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, [
            "table", "add-entry", str(sample_ct),
            "-d", "Speed", "-a", "game.exe+5000", "-t", "float", "-v", "1.5",
        ])
        assert result.exit_code == 0
        assert "Speed" in result.output or "success" in result.output

        # Verify it was persisted
        result2 = runner.invoke(cli, ["--json", "table", "list-entries", str(sample_ct)])
        data = json.loads(result2.output)
        descs = [e["description"] for e in data["entries"]]
        assert "Speed" in descs


class TestTableRemoveEntry:
    def test_remove(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["table", "remove-entry", str(sample_ct), "0"])
        assert result.exit_code == 0
        assert "Removed" in result.output or "success" in result.output

    def test_remove_nonexistent(self, runner: CliRunner, sample_ct: Path):
        result = runner.invoke(cli, ["table", "remove-entry", str(sample_ct), "999"])
        assert result.exit_code == 0  # command doesn't fail, prints error
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestTableFreezeUnfreeze:
    def test_freeze(self, runner: CliRunner, sample_ct: Path):
        # Entry 1 (Mana) is not frozen
        result = runner.invoke(cli, ["table", "freeze", str(sample_ct), "1"])
        assert result.exit_code == 0
        assert "frozen" in result.output.lower() or "success" in result.output.lower()

    def test_unfreeze(self, runner: CliRunner, sample_ct: Path):
        # Entry 0 (Health) is frozen
        result = runner.invoke(cli, ["table", "unfreeze", str(sample_ct), "0"])
        assert result.exit_code == 0
        assert "unfrozen" in result.output.lower() or "success" in result.output.lower()


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------


class TestSessionCommands:
    def test_status(self, runner: CliRunner):
        result = runner.invoke(cli, ["session", "status"])
        assert result.exit_code == 0
        assert "Session" in result.output or "session" in result.output

    def test_status_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "session", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "session_id" in data

    def test_reset(self, runner: CliRunner):
        result = runner.invoke(cli, ["session", "reset"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower() or "success" in result.output.lower()

    def test_history(self, runner: CliRunner):
        result = runner.invoke(cli, ["session", "history"])
        assert result.exit_code == 0
