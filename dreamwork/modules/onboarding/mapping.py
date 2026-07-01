"""Column auto-mapping — guess which source column is which canonical field (spec §4.5).

Both the tabular/paste parser and the Notion importer feed their column headers through here,
so the "one-tap confirm the mapping" step is shared code. We never hand-match: we auto-map the
obvious ones and hand back what we couldn't place so the UI can ask.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# canonical field -> keywords that, if found in a header, map to it. Order matters: the first
# canonical field whose keyword matches a header wins, so put the more specific ones first.
_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    ("fund_size_usd", ("fund size", "fund_size", "aum size")),
    ("aum_usd", ("aum", "assets under management")),
    ("ticket_estimate_usd", ("check", "ticket", "investment", "amount", "allocation")),
    ("first_contact_date", ("first contact", "first check", "first_check", "since", "date added",
                            "invested", "first meeting")),
    ("last_contact_date", ("last contact", "last touch", "last spoke", "last email")),
    ("partner_role", ("role", "title", "position")),
    ("partner_influence", ("influence", "seniority", "power")),
    ("partner_name", ("partner", "contact", "person", "who", "name", "lead partner")),
    ("firm_name", ("firm", "fund", "investor", "company", "organization", "organisation", "vc")),
    ("stage", ("stage", "status", "pipeline")),
    ("next_step", ("next step", "next_step", "todo", "action", "follow up", "follow-up")),
    ("sectors", ("sector", "focus", "vertical", "thesis", "industry")),
    ("geographies", ("geo", "geography", "region", "location", "hq")),
    ("leads", ("leads", "lead round", "can lead")),
    ("follows_on", ("follows on", "follow on", "follow-on")),
    ("is_lead", ("is lead", "potential lead", "target lead")),
]


@dataclass
class ColumnMapping:
    """The result of auto-mapping: which header feeds which field, and what we couldn't place."""

    mapping: dict[str, str] = field(default_factory=dict)   # header -> canonical field
    unmapped: list[str] = field(default_factory=list)        # headers we couldn't confidently place
    confidence: dict[str, float] = field(default_factory=dict)  # header -> 0.0..1.0

    def canonical_for(self, header: str) -> str | None:
        return self.mapping.get(header)


def auto_map(headers: list[str]) -> ColumnMapping:
    """Map source column headers onto canonical record fields (case-insensitive keyword match)."""
    result = ColumnMapping()
    taken: set[str] = set()
    for header in headers:
        canonical, score = _best_match(header, taken)
        if canonical is None:
            result.unmapped.append(header)
            result.confidence[header] = 0.0
            continue
        result.mapping[header] = canonical
        result.confidence[header] = score
        taken.add(canonical)
    return result


def _best_match(header: str, taken: set[str]) -> tuple[str | None, float]:
    h = header.strip().lower()
    if not h:
        return None, 0.0
    for canonical, keywords in _ALIASES:
        if canonical in taken:
            continue
        for kw in keywords:
            if h == kw:
                return canonical, 1.0
            if kw in h or h in kw:
                return canonical, 0.7
    return None, 0.0
