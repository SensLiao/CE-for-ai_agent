"""Cheat Table (.CT) file management.

Parses and generates CE cheat table XML files. Supports entry CRUD,
freeze/unfreeze, and round-trip save. No CE dependency — pure Python
XML processing.

CT file format (simplified):
```xml
<?xml version="1.0" encoding="utf-8"?>
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
  </CheatEntries>
</CheatTable>
```
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# CE variable type names as they appear in .CT XML
_VARTYPE_MAP = {
    "Byte": "Byte",
    "2 Bytes": "2 Bytes",
    "4 Bytes": "4 Bytes",
    "8 Bytes": "8 Bytes",
    "Float": "Float",
    "Double": "Double",
    "String": "String",
    "Array of byte": "Array of byte",
    "Binary": "Binary",
}

# Reverse: friendly name -> CT XML name
VARTYPE_ALIASES: dict[str, str] = {
    "byte": "Byte",
    "word": "2 Bytes",
    "int16": "2 Bytes",
    "dword": "4 Bytes",
    "int32": "4 Bytes",
    "int": "4 Bytes",
    "qword": "8 Bytes",
    "int64": "8 Bytes",
    "float": "Float",
    "single": "Float",
    "double": "Double",
    "string": "String",
    "aob": "Array of byte",
    "binary": "Binary",
}


@dataclass
class CheatEntry:
    """Represents a single cheat table entry."""

    id: int
    description: str
    variable_type: str = "4 Bytes"
    address: str = "0"
    value: Optional[str] = None
    frozen: bool = False
    group: bool = False
    children: list[CheatEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "variable_type": self.variable_type,
            "address": self.address,
            "frozen": self.frozen,
        }
        if self.value is not None:
            d["value"] = self.value
        if self.group:
            d["group"] = True
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class CheatTable:
    """In-memory representation of a .CT file."""

    entries: list[CheatEntry] = field(default_factory=list)
    source_path: Optional[Path] = None
    _next_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source_path) if self.source_path else None,
            "entry_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }


def load_table(path: str | Path) -> CheatTable:
    """Load a .CT file and parse it into a CheatTable.

    Args:
        path: Path to the .CT file.

    Returns:
        Parsed CheatTable.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ET.ParseError: If XML is malformed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Cheat table not found: {p}")

    tree = ET.parse(p)
    root = tree.getroot()
    entries_el = root.find("CheatEntries")
    entries: list[CheatEntry] = []
    max_id = -1

    if entries_el is not None:
        for entry_el in entries_el.findall("CheatEntry"):
            entry, eid = _parse_entry(entry_el)
            entries.append(entry)
            if eid > max_id:
                max_id = eid

    return CheatTable(entries=entries, source_path=p, _next_id=max_id + 1)


def save_table(table: CheatTable, path: Optional[str | Path] = None) -> Path:
    """Save a CheatTable to a .CT XML file.

    Args:
        table: The CheatTable to save.
        path: Output path. Defaults to table.source_path.

    Returns:
        Path to the saved file.

    Raises:
        ValueError: If no path specified and table has no source_path.
    """
    out = Path(path) if path else table.source_path
    if out is None:
        raise ValueError("No output path specified and table has no source_path")

    root = ET.Element("CheatTable")
    entries_el = ET.SubElement(root, "CheatEntries")
    for entry in table.entries:
        _build_entry_xml(entries_el, entry)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(out), encoding="utf-8", xml_declaration=True)
    return out


def add_entry(
    table: CheatTable,
    description: str,
    address: str,
    variable_type: str = "4 Bytes",
    value: Optional[str] = None,
    frozen: bool = False,
) -> CheatEntry:
    """Add a new entry to the cheat table.

    Args:
        table: Target CheatTable.
        description: Human-readable name.
        address: Memory address expression (e.g. 'game.exe+1A2B').
        variable_type: CE type name or alias (e.g. 'dword', 'float').
        value: Optional initial value string.
        frozen: Whether to freeze the value.

    Returns:
        The newly created CheatEntry.
    """
    vt = _resolve_vartype(variable_type)
    entry = CheatEntry(
        id=table._next_id,
        description=description,
        variable_type=vt,
        address=address,
        value=value,
        frozen=frozen,
    )
    table._next_id += 1
    table.entries.append(entry)
    return entry


def remove_entry(table: CheatTable, entry_id: int) -> Optional[CheatEntry]:
    """Remove an entry by ID.

    Returns:
        The removed entry, or None if not found.
    """
    for i, entry in enumerate(table.entries):
        if entry.id == entry_id:
            return table.entries.pop(i)
        # Check children
        for j, child in enumerate(entry.children):
            if child.id == entry_id:
                return entry.children.pop(j)
    return None


def find_entry(table: CheatTable, entry_id: int) -> Optional[CheatEntry]:
    """Find an entry by ID (searches children too)."""
    for entry in table.entries:
        if entry.id == entry_id:
            return entry
        for child in entry.children:
            if child.id == entry_id:
                return child
    return None


def freeze_entry(table: CheatTable, entry_id: int) -> bool:
    """Set frozen=True on an entry. Returns True if found."""
    entry = find_entry(table, entry_id)
    if entry:
        entry.frozen = True
        return True
    return False


def unfreeze_entry(table: CheatTable, entry_id: int) -> bool:
    """Set frozen=False on an entry. Returns True if found."""
    entry = find_entry(table, entry_id)
    if entry:
        entry.frozen = False
        return True
    return False


def list_entries(table: CheatTable) -> list[dict[str, Any]]:
    """Return all entries as a flat list of dicts."""
    return [e.to_dict() for e in table.entries]


# --- Internal helpers ---


def _resolve_vartype(name: str) -> str:
    """Resolve a variable type name or alias to the canonical CT name."""
    if name in _VARTYPE_MAP:
        return name
    canonical = VARTYPE_ALIASES.get(name.lower())
    if canonical:
        return canonical
    raise ValueError(
        f"Unknown variable type: {name}. "
        f"Valid types: {', '.join(sorted(VARTYPE_ALIASES.keys()))}"
    )


def _parse_entry(el: ET.Element) -> tuple[CheatEntry, int]:
    """Parse an XML CheatEntry element into a CheatEntry dataclass."""
    eid = int(_text(el, "ID", "0"))
    desc = _text(el, "Description", "").strip('"')
    vtype = _text(el, "VariableType", "4 Bytes")
    addr = _text(el, "Address", "0")
    val = _text(el, "Value")
    frozen = _text(el, "Frozen", "0") == "1"
    group_header = el.find("GroupHeader") is not None

    children: list[CheatEntry] = []
    children_el = el.find("CheatEntries")
    if children_el is not None:
        for child_el in children_el.findall("CheatEntry"):
            child, _ = _parse_entry(child_el)
            children.append(child)

    entry = CheatEntry(
        id=eid,
        description=desc,
        variable_type=vtype,
        address=addr,
        value=val,
        frozen=frozen,
        group=group_header,
        children=children,
    )
    return entry, eid


def _text(el: ET.Element, tag: str, default: Optional[str] = None) -> Optional[str]:
    """Get text content of a child element."""
    child = el.find(tag)
    if child is not None and child.text:
        return child.text
    return default


def _build_entry_xml(parent: ET.Element, entry: CheatEntry) -> ET.Element:
    """Build an XML element for a CheatEntry."""
    el = ET.SubElement(parent, "CheatEntry")
    _add_text(el, "ID", str(entry.id))
    _add_text(el, "Description", f'"{entry.description}"')
    if entry.group:
        ET.SubElement(el, "GroupHeader")
    _add_text(el, "VariableType", entry.variable_type)
    _add_text(el, "Address", entry.address)
    if entry.value is not None:
        _add_text(el, "Value", entry.value)
    if entry.frozen:
        _add_text(el, "Frozen", "1")

    if entry.children:
        children_el = ET.SubElement(el, "CheatEntries")
        for child in entry.children:
            _build_entry_xml(children_el, child)

    return el


def _add_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Add a child element with text content."""
    el = ET.SubElement(parent, tag)
    el.text = text
    return el
