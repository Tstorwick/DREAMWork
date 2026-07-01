"""onboarding (owner: Helge) — get a founder's investor data in, painlessly.

Take an investor list, a **cap table**, a pasted table, or a Notion database and create Firm /
Partner / PipelineEntry rows in `core` — deduping and merging, never duplicating. The design bar
is *friendliness* (spec §3.7): sensible defaults, blanks always allowed, and every imported
value carries where it came from (spec §5).

Depends only on `core`; never talks to `modules/external` directly. See docs/module-contracts.md.

Public API
----------
    import_captable(repo, round_id, rows)  # list[dict] -> ImportResult  (the module contract)
    import_tabular(repo, round_id, text)   # CSV / pasted table / Markdown table
    import_records(repo, round_id, records)# pre-built InvestorRecords (used by every source)

The Notion importer lives in `.sources.notion`; it produces the same InvestorRecords, so it
flows through the same merge engine.
"""

from __future__ import annotations

from dreamwork.core.repository import Repository
from dreamwork.modules.onboarding.build import record_from_mapped
from dreamwork.modules.onboarding.importer import ImportResult, import_records, normalize_name
from dreamwork.modules.onboarding.mapping import auto_map
from dreamwork.modules.onboarding.provenance import Provenanced, Source
from dreamwork.modules.onboarding.records import InvestorRecord
from dreamwork.modules.onboarding.sources import ImportPreview
from dreamwork.modules.onboarding.sources.tabular import TabularImporter

__all__ = [
    "ImportResult",
    "ImportPreview",
    "InvestorRecord",
    "Provenanced",
    "Source",
    "import_records",
    "import_tabular",
    "import_captable",
    "import_notion",
    "preview_tabular",
    "preview_notion",
    "normalize_name",
]


def preview_notion(link: str, client) -> ImportPreview:
    """Show what a shared Notion database would import — without touching core.

    `client` implements `sources.notion.NotionClient`; use `build_notion_client()` for the real
    SDK. Raises `NotionPermissionError` if the page wasn't shared with the integration.
    """
    from dreamwork.modules.onboarding.sources.notion import NotionImporter

    return NotionImporter(link, client).preview()


def import_notion(repo: Repository, round_id: str, link: str, client) -> ImportResult:
    """Read a shared Notion database and merge it into core."""
    return import_records(repo, round_id, preview_notion(link, client).records)


def preview_tabular(text: str, *, source: Source = Source.PASTE) -> ImportPreview:
    """Parse pasted/CSV text and show what would be imported — without touching core."""
    return TabularImporter(text, source=source).preview()


def import_tabular(
    repo: Repository, round_id: str, text: str, *, source: Source = Source.PASTE
) -> ImportResult:
    """Parse a CSV / pasted table and merge it into core."""
    return import_records(repo, round_id, preview_tabular(text, source=source).records)


def import_captable(repo: Repository, round_id: str, rows: list[dict]) -> ImportResult:
    """Import a cap table given as a list of dict rows (the documented module contract).

    Dict keys are treated as column headers and auto-mapped to record fields; the cap table is
    the source of truth for firm, check size, and first-check date (docs/data-model.md).
    """
    if not rows:
        return import_records(repo, round_id, [])
    headers = list({k for row in rows for k in row})
    mapping = auto_map(headers)
    records: list[InvestorRecord] = []
    for row in rows:
        mapped: dict[str, object] = {}
        notes: list[str] = []
        for key, value in row.items():
            canonical = mapping.canonical_for(key)
            if canonical:
                mapped[canonical] = value
            elif value not in (None, ""):
                notes.append(f"{key}: {value}")
        record = record_from_mapped(mapped, Source.CSV, notes=notes)
        if record:
            records.append(record)
    return import_records(repo, round_id, records)
