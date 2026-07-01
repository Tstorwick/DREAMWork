"""Provenance & confidence — where each imported value came from, and how much to trust it.

The spec's rule (§4, §5.2): every field carries its source and a confidence score, and a
human-confirmed value always outranks an inferred one. `core`'s domain rows don't have
per-field provenance columns (that storage question is Chris's — see docs/data-model.md), so
onboarding keeps provenance in *these* objects during an import and writes a readable summary
into the Markdown dossier. Confidence is a 0.0–1.0 float, matching `modules/external`'s
`SharedFact.confidence`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Source(str, Enum):
    """Where a value came from. The chip label shown in the UI is `Source.label`."""

    HUMAN_CONFIRMED = "human_confirmed"
    CALENDAR = "calendar"
    GMAIL_METADATA = "gmail_metadata"
    NOTETAKER = "notetaker"
    NOTION = "notion"
    DOC = "doc"
    CSV = "csv"
    PASTE = "paste"

    @property
    def label(self) -> str:
        """The source chip text (§5.2), e.g. 'From Notion', 'Human-confirmed'."""
        return {
            Source.HUMAN_CONFIRMED: "Human-confirmed",
            Source.CALENDAR: "From calendar",
            Source.GMAIL_METADATA: "From Gmail metadata",
            Source.NOTETAKER: "From notetaker",
            Source.NOTION: "From Notion",
            Source.DOC: "From doc",
            Source.CSV: "From CSV",
            Source.PASTE: "From pasted list",
        }[self]


# Baseline trust per source. A booked calendar invite is stronger evidence than a value typed
# into a spreadsheet; a value the user confirmed by hand beats everything. Used only to pick a
# winner when the same field arrives from two sources in one import.
_BASE_CONFIDENCE: dict[Source, float] = {
    Source.HUMAN_CONFIRMED: 1.0,
    Source.CALENDAR: 0.9,
    Source.GMAIL_METADATA: 0.7,
    Source.NOTETAKER: 0.7,
    Source.NOTION: 0.6,
    Source.DOC: 0.6,
    Source.CSV: 0.6,
    Source.PASTE: 0.5,
}


def base_confidence(source: Source) -> float:
    return _BASE_CONFIDENCE[source]


@dataclass
class Provenanced:
    """A value plus where it came from and how sure we are — the unit the record is built from."""

    value: object
    source: Source
    confidence: float = 0.0
    reason: str | None = None  # optional plain-language 'Why?' (§5.1)

    def __post_init__(self) -> None:
        if not self.confidence:
            self.confidence = base_confidence(self.source)

    @property
    def is_human_confirmed(self) -> bool:
        return self.source is Source.HUMAN_CONFIRMED

    def chip(self) -> str:
        """The source chip shown next to this field, e.g. '[ From Notion ]'."""
        return f"[ {self.source.label} ]"


def prefer(current: Provenanced | None, incoming: Provenanced) -> Provenanced:
    """Pick the value to keep when a field arrives twice.

    Human-confirmed always wins (§4.6). Otherwise the higher confidence wins; on a tie we keep
    what we already had, so import order never silently changes a value.
    """
    if current is None:
        return incoming
    if incoming.is_human_confirmed and not current.is_human_confirmed:
        return incoming
    if current.is_human_confirmed and not incoming.is_human_confirmed:
        return current
    return incoming if incoming.confidence > current.confidence else current
