"""The merge engine — turn InvestorRecords into core rows, deduping instead of duplicating.

This is the shared destination for every source. It (1) folds records that describe the same
investor together, (2) upserts Firm / Partner / PipelineEntry into the `Repository`, merging into
existing rows rather than creating duplicates (spec §3.7, §4.5, §6 "duplicates found"), and
(3) writes a provenance summary into each firm's dossier so every value shows where it came from
(spec §5). Human-confirmed values overwrite; inferred ones only fill blanks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dreamwork.core.domain import Firm, Outcome, Partner, PipelineEntry, Stage
from dreamwork.core.dossiers import dossier_path_for, read_dossier, write_dossier
from dreamwork.core.repository import Repository
from dreamwork.modules.onboarding.records import (
    ENTRY_FIELDS,
    FIRM_FIELDS,
    PARTNER_FIELDS,
    InvestorRecord,
)


@dataclass
class ImportResult:
    """A summary of what an import did — the confirmation the user (and tests) read."""

    firms_created: int = 0
    firms_merged: int = 0
    partners_created: int = 0
    partners_merged: int = 0
    entries_created: int = 0
    entries_merged: int = 0
    merges: list[str] = field(default_factory=list)     # "merged 3 records" note + basis for undo
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [
            f"{self.firms_created} firms",
            f"{self.partners_created} partners",
            f"{self.entries_created} pipeline entries",
        ]
        line = "Created " + ", ".join(parts) + "."
        merged = self.firms_merged + self.partners_merged + self.entries_merged
        if merged:
            line += f" Merged into {merged} existing record(s)."
        return line


def normalize_name(name: str) -> str:
    """Fold a firm/person name to a dedupe key: lowercase, no punctuation, single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "x"


def import_records(
    repo: Repository,
    round_id: str,
    records: list[InvestorRecord],
    *,
    write_dossiers: bool = True,
) -> ImportResult:
    """Merge records into core. Never creates a second row for an investor we already have."""
    result = ImportResult()
    if not records:
        result.warnings.append(
            "No investors discovered — connect another source or paste a list to get started."
        )
        return result

    for record in _dedupe(records):
        if not record.firm_name:
            continue
        firm = _upsert_firm(repo, record, result)
        partner = _upsert_partner(repo, firm, record, result)
        _upsert_entry(repo, round_id, firm, partner, record, result)
        if write_dossiers:
            _write_firm_dossier(repo, firm, record)
    return result


def _dedupe(records: list[InvestorRecord]) -> list[InvestorRecord]:
    """Fold records that name the same firm+partner into one before touching core."""
    merged: dict[tuple[str, str], InvestorRecord] = {}
    for record in records:
        if not record.firm_name:
            continue
        key = (normalize_name(record.firm_name), normalize_name(str(record.value("partner_name") or "")))
        if key in merged:
            merged[key].merge(record)
        else:
            merged[key] = record
    return list(merged.values())


def _find_firm(repo: Repository, name: str) -> Firm | None:
    target = normalize_name(name)
    for firm in repo.list_firms():
        if normalize_name(firm.name) == target:
            return firm
    return None


def _upsert_firm(repo: Repository, record: InvestorRecord, result: ImportResult) -> Firm:
    name = str(record.firm_name)
    existing = _find_firm(repo, name)
    if existing is None:
        firm = Firm(id=_fresh_id(repo.get_firm, "f", _slug(name)), name=name)
        _apply_fields(firm, record, FIRM_FIELDS, is_new=True)
        repo.add_firm(firm)
        result.firms_created += 1
        return firm

    if _apply_fields(existing, record, FIRM_FIELDS, is_new=False):
        result.firms_merged += 1
        result.merges.append(f"Merged new details into existing firm {existing.name!r}.")
    return existing


def _upsert_partner(
    repo: Repository, firm: Firm, record: InvestorRecord, result: ImportResult
) -> Partner | None:
    name = record.value("partner_name")
    if not name:
        return None
    name = str(name)
    target = normalize_name(name)
    existing = next(
        (p for p in repo.list_partners(firm.id) if normalize_name(p.name) == target), None
    )
    if existing is None:
        partner = Partner(
            id=_fresh_id(repo.get_partner, "p", f"{_slug(firm.name)}_{_slug(name)}"),
            firm_id=firm.id,
            name=name,
        )
        _apply_fields(partner, record, PARTNER_FIELDS, is_new=True)
        repo.add_partner(partner)
        result.partners_created += 1
        return partner

    if _apply_fields(existing, record, PARTNER_FIELDS, is_new=False):
        result.partners_merged += 1
    return existing


def _upsert_entry(
    repo: Repository,
    round_id: str,
    firm: Firm,
    partner: Partner | None,
    record: InvestorRecord,
    result: ImportResult,
) -> PipelineEntry:
    partner_id = partner.id if partner else None
    existing = next(
        (
            e
            for e in repo.list_pipeline(round_id)
            if e.firm_id == firm.id and e.partner_id == partner_id
        ),
        None,
    )
    if existing is None:
        entry = PipelineEntry(
            id=_fresh_id(repo.get_pipeline_entry, "pe", f"{round_id}_{_slug(firm.name)}"),
            round_id=round_id,
            firm_id=firm.id,
            partner_id=partner_id,
            stage=record.value("stage") or Stage.SOURCED,  # type: ignore[arg-type]
            outcome=Outcome.ACTIVE,
        )
        _apply_fields(entry, record, ENTRY_FIELDS, is_new=True)
        repo.add_pipeline_entry(entry)
        result.entries_created += 1
        return entry

    if _apply_fields(existing, record, ENTRY_FIELDS, is_new=False):
        repo.update_pipeline_entry(existing)
        result.entries_merged += 1
    return existing


def _apply_fields(entity: object, record: InvestorRecord, names: tuple[str, ...], *, is_new: bool) -> bool:
    """Copy record fields onto a core entity. Fill blanks always; overwrite only if human-confirmed.

    Returns True if any existing (non-new) value changed — the signal that a merge happened.
    """
    changed = False
    for name in names:
        prov = record.get(name)
        if prov is None:
            continue
        attr = _ATTR.get(name, name)
        if not hasattr(entity, attr):
            continue
        current = getattr(entity, attr)
        blank = current in (None, [], "", False) if not is_new else True
        if is_new:
            setattr(entity, attr, prov.value)
        elif blank or prov.is_human_confirmed:
            if current != prov.value:
                setattr(entity, attr, prov.value)
                changed = True
    return changed


# canonical record field -> core entity attribute, where the names differ.
_ATTR = {
    "partner_name": "name",
    "partner_role": "role",
    "partner_influence": "influence",
    "firm_name": "name",
}


def _fresh_id(getter, prefix: str, slug: str) -> str:
    """A readable id (f_sequoia) that doesn't collide with an existing row of a different name."""
    candidate = f"{prefix}_{slug}"
    if getter(candidate) is None:
        return candidate
    n = 2
    while getter(f"{candidate}_{n}") is not None:
        n += 1
    return f"{candidate}_{n}"


def _write_firm_dossier(repo: Repository, firm: Firm, record: InvestorRecord) -> None:
    """Write the firm's dossier with source chips per field and any verbatim notes (spec §5)."""
    if not firm.dossier_path:
        firm.dossier_path = dossier_path_for("firm", firm.id)
        repo.add_firm(firm)  # persist the path back onto the row

    lines = [f"# {firm.name}", ""]
    existing = read_dossier(firm.dossier_path)
    if "## Onboarding import" not in existing:
        lines.append("## Onboarding import")
        for name, prov in record.fields.items():
            lines.append(f"- **{name}**: {prov.value}  {prov.chip()}")
        for note in record.notes:
            lines.append(f"- {note.text}  [ {note.source.label} ]")
        body = existing + "\n" + "\n".join(lines) if existing else "\n".join(lines)
        write_dossier(firm.dossier_path, body, meta={"id": firm.id})
