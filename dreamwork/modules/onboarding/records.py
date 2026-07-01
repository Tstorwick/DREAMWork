"""The unified investor record — one per investor, every field provenanced (spec §4.6).

This is onboarding's *intermediate* shape. Parsers (CSV, paste, Notion, later email/calendar)
all produce `InvestorRecord`s; the importer then merges them and writes `core`'s Firm / Partner
/ PipelineEntry rows. Keeping a single intermediate is what lets the "paste-anything" fallback
and the Notion importer share the same merge, dedupe, and dossier code (spec §4.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dreamwork.modules.onboarding.provenance import Provenanced, Source, prefer

# Canonical field names an InvestorRecord may carry. Parsers map their columns onto these; the
# importer routes them onto the right core entity. Grouped by destination for readability.
FIRM_FIELDS = ("firm_name", "fund_size_usd", "aum_usd", "leads", "geographies",
               "sectors", "follows_on")
PARTNER_FIELDS = ("partner_name", "partner_role", "partner_influence")
ENTRY_FIELDS = ("stage", "ticket_estimate_usd", "first_contact_date",
                "last_contact_date", "next_step", "is_lead")
CANONICAL_FIELDS = FIRM_FIELDS + PARTNER_FIELDS + ENTRY_FIELDS


@dataclass
class Note:
    """A freeform note kept verbatim (spec §4.5: 'preserve the user's notes verbatim')."""

    text: str
    source: Source


@dataclass
class InvestorRecord:
    """A single investor's imported data: canonical field -> provenanced value, plus notes."""

    fields: dict[str, Provenanced] = field(default_factory=dict)
    notes: list[Note] = field(default_factory=list)

    def set(self, name: str, prov: Provenanced) -> None:
        """Set/merge a field, keeping the higher-precedence value (see provenance.prefer)."""
        if name not in CANONICAL_FIELDS:
            raise ValueError(f"unknown record field {name!r}")
        self.fields[name] = prefer(self.fields.get(name), prov)

    def get(self, name: str) -> Provenanced | None:
        return self.fields.get(name)

    def value(self, name: str) -> object | None:
        prov = self.fields.get(name)
        return prov.value if prov else None

    @property
    def firm_name(self) -> str | None:
        return self.value("firm_name")  # type: ignore[return-value]

    def merge(self, other: InvestorRecord) -> None:
        """Fold another record for the same investor into this one (in-import dedupe)."""
        for name, prov in other.fields.items():
            self.set(name, prov)
        self.notes.extend(other.notes)
