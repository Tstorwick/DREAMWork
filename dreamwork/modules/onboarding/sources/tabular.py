"""Tabular / paste-anything importer — a CSV file or a pasted table becomes InvestorRecords.

This is the "paste-anything fallback" from spec §4.5: the same parser powers a drag-dropped CSV
and a plain textarea. It sniffs the delimiter (comma, tab, pipe, or a Markdown table), reads the
header row, auto-maps columns, and builds one record per data row. Unmapped columns are kept as
notes so nothing the user typed is silently dropped.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from dreamwork.modules.onboarding.build import record_from_mapped
from dreamwork.modules.onboarding.mapping import ColumnMapping, auto_map
from dreamwork.modules.onboarding.provenance import Source
from dreamwork.modules.onboarding.records import InvestorRecord
from dreamwork.modules.onboarding.sources import ImportPreview


@dataclass
class ParsedTable:
    headers: list[str]
    rows: list[list[str]]


def parse_table(text: str) -> ParsedTable:
    """Parse pasted text into headers + rows, sniffing the delimiter. Handles Markdown tables."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ParsedTable(headers=[], rows=[])

    if _looks_like_markdown_table(lines):
        return _parse_markdown_table(lines)

    delimiter = _sniff_delimiter(lines[0])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    parsed = [row for row in reader if any(cell.strip() for cell in row)]
    if not parsed:
        return ParsedTable(headers=[], rows=[])
    headers = [h.strip() for h in parsed[0]]
    rows = [[c.strip() for c in r] for r in parsed[1:]]
    return ParsedTable(headers=headers, rows=rows)


def _sniff_delimiter(header_line: str) -> str:
    for delim in ("\t", "|", ";", ","):
        if delim in header_line:
            return delim
    return ","


def _looks_like_markdown_table(lines: list[str]) -> bool:
    return (
        len(lines) >= 2
        and lines[0].lstrip().startswith("|")
        and set(lines[1].replace("|", "").replace(":", "").strip()) <= {"-", " "}
    )


def _parse_markdown_table(lines: list[str]) -> ParsedTable:
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    headers = cells(lines[0])
    rows = [cells(ln) for ln in lines[2:]]  # skip the |---| separator row
    return ParsedTable(headers=headers, rows=rows)


class TabularImporter:
    """Turns pasted/CSV text into records. `source` distinguishes an uploaded CSV from a paste."""

    def __init__(self, text: str, *, source: Source = Source.PASTE) -> None:
        self._text = text
        self._source = source

    def preview(self) -> ImportPreview:
        table = parse_table(self._text)
        if not table.headers:
            return ImportPreview(warnings=["Nothing to import — no columns were found."])

        mapping = auto_map(table.headers)
        records = self._records(table, mapping)
        preview = ImportPreview(records=records, mapping=mapping)

        if not records:
            preview.warnings.append(
                "No investors discovered — is there a 'Firm' or 'Investor' column?"
            )
        # Flag headers we couldn't place so the confirm screen can ask (spec §6 "messy doc").
        for header in mapping.unmapped:
            preview.low_confidence.append(f"Column {header!r} wasn't mapped — kept as a note.")
        return preview

    def _records(self, table: ParsedTable, mapping: ColumnMapping) -> list[InvestorRecord]:
        records: list[InvestorRecord] = []
        for row in table.rows:
            mapped: dict[str, object] = {}
            notes: list[str] = []
            for i, header in enumerate(table.headers):
                cell = row[i] if i < len(row) else ""
                canonical = mapping.canonical_for(header)
                if canonical:
                    mapped[canonical] = cell
                elif cell.strip():
                    notes.append(f"{header}: {cell.strip()}")
            record = record_from_mapped(mapped, self._source, notes=notes)
            if record:
                records.append(record)
        return records
