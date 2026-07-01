"""Build an InvestorRecord from a mapped row — the shared step every parser ends on.

A parser's job is reduced to: produce `{canonical_field: raw_value}` dicts and a `Source`. This
module coerces each raw value to the type core expects and attaches provenance, so coercion
rules live in exactly one place for CSV, paste, and Notion alike.
"""

from __future__ import annotations

from dreamwork.modules.onboarding import coerce
from dreamwork.modules.onboarding.provenance import Provenanced, Source
from dreamwork.modules.onboarding.records import InvestorRecord, Note

# canonical field -> how to coerce its raw value. Fields not listed are kept as trimmed strings.
_COERCERS = {
    "fund_size_usd": coerce.money_to_int,
    "aum_usd": coerce.money_to_int,
    "ticket_estimate_usd": coerce.money_to_int,
    "first_contact_date": coerce.to_date,
    "last_contact_date": coerce.to_date,
    "leads": coerce.to_bool,
    "follows_on": coerce.to_bool,
    "is_lead": coerce.to_bool,
    "geographies": coerce.to_list,
    "sectors": coerce.to_list,
    "stage": coerce.to_stage,
}


def record_from_mapped(
    mapped: dict[str, object],
    source: Source,
    *,
    notes: list[str] | None = None,
) -> InvestorRecord | None:
    """Coerce a `{canonical_field: raw}` row into a record. Returns None if it has no firm name."""
    record = InvestorRecord()
    for field_name, raw in mapped.items():
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        value = _COERCERS.get(field_name, _clean_str)(raw)
        if value is None:
            continue
        record.set(field_name, Provenanced(value=value, source=source))
    for text in notes or []:
        if text and text.strip():
            record.notes.append(Note(text=text.strip(), source=source))
    # An investor with no firm name can't become a Firm row — the one hard requirement.
    return record if record.firm_name else None


def _clean_str(raw: object) -> str | None:
    text = str(raw).strip()
    return text or None
