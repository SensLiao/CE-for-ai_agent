"""Shared fixtures for cli-anything-cheatengine tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


SAMPLE_CT_XML = textwrap.dedent("""\
    <?xml version='1.0' encoding='utf-8'?>
    <CheatTable>
      <CheatEntries>
        <CheatEntry>
          <ID>0</ID>
          <Description>"Health"</Description>
          <VariableType>4 Bytes</VariableType>
          <Address>game.exe+1A2B3C</Address>
          <Value>100</Value>
          <Frozen>1</Frozen>
        </CheatEntry>
        <CheatEntry>
          <ID>1</ID>
          <Description>"Mana"</Description>
          <VariableType>Float</VariableType>
          <Address>game.exe+1A2B40</Address>
          <Value>50.0</Value>
        </CheatEntry>
        <CheatEntry>
          <ID>2</ID>
          <Description>"Stats Group"</Description>
          <VariableType>4 Bytes</VariableType>
          <Address>0</Address>
          <GroupHeader />
          <CheatEntries>
            <CheatEntry>
              <ID>3</ID>
              <Description>"Strength"</Description>
              <VariableType>4 Bytes</VariableType>
              <Address>game.exe+2000</Address>
              <Value>25</Value>
            </CheatEntry>
          </CheatEntries>
        </CheatEntry>
      </CheatEntries>
    </CheatTable>
""")

EMPTY_CT_XML = textwrap.dedent("""\
    <?xml version='1.0' encoding='utf-8'?>
    <CheatTable>
      <CheatEntries />
    </CheatTable>
""")


@pytest.fixture
def tmp_ct_file(tmp_path: Path) -> Path:
    """Create a temporary .CT file with sample entries."""
    ct = tmp_path / "test.ct"
    ct.write_text(SAMPLE_CT_XML, encoding="utf-8")
    return ct


@pytest.fixture
def tmp_empty_ct(tmp_path: Path) -> Path:
    """Create a temporary empty .CT file."""
    ct = tmp_path / "empty.ct"
    ct.write_text(EMPTY_CT_XML, encoding="utf-8")
    return ct


@pytest.fixture
def tmp_session_dir(tmp_path: Path) -> Path:
    """Create a temporary session directory."""
    d = tmp_path / "sessions"
    d.mkdir()
    return d
