"""Import sources — each turns some external input into InvestorRecords, behind one interface.

Every source (tabular/paste today, Notion next, email/calendar later) implements `SourceImporter`
so the merge engine, dossier writing, and confirm step never care where records came from
(spec §4.5: "same parser powers a plain textarea" and the Notion path share this shape).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from dreamwork.modules.onboarding.mapping import ColumnMapping
from dreamwork.modules.onboarding.records import InvestorRecord


@dataclass
class ImportPreview:
    """What we'd import, shown for one-tap confirmation before touching core (spec §3 Screen 4)."""

    records: list[InvestorRecord] = field(default_factory=list)
    mapping: ColumnMapping | None = None
    warnings: list[str] = field(default_factory=list)
    # Fields we parsed but aren't confident about — flagged for the user (spec §6 "messy doc").
    low_confidence: list[str] = field(default_factory=list)


class SourceImporter(Protocol):
    """A source of investor records. `preview()` never mutates anything."""

    def preview(self) -> ImportPreview: ...
