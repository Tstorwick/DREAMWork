"""qualified_list (owner: Chris) — qualification + the REAL Postgres store.

Two jobs (see docs/module-contracts.md):

  1. The real local Postgres implementation of `core.repository.Repository`. When it exists,
     everything else keeps working unchanged — that's the whole point of the contract. You also
     own how `dossier_path` is stored/generated (see core/dossiers.py).

  2. Qualification: turn the investor universe into "who it makes sense to talk to this round",
     filtering/scoring by round, ticket size, geography, sector, stage. A no or a next-round fit
     becomes an Outcome flag on the PipelineEntry, never a deletion (see docs/pipeline.md).

Job 1 (the Postgres Repository) lives in `store.py` as `PostgresRepository`, applied via
`schema.sql`. The app selects it through `dreamwork.config.get_repository()` when
`DREAMWORK_DB_URL` is set; otherwise it runs on the in-memory store. This file is job 2
(qualification), which works against any `Repository`.

NOTE: qualification reads `ticket_size_usd_range` and `extantia_portfolio_overlap` on `Firm`
(accepted in PR #1). It degrades gracefully if a Firm doesn't have them set.
"""

from __future__ import annotations

from dataclasses import dataclass

from dreamwork.core.domain import Firm, Outcome, PipelineEntry, Stage
from dreamwork.core.repository import Repository


@dataclass
class QualificationCriteria:
    """Filters that turn the investor universe into "who it makes sense to talk to this round".

    Every field is optional — an unset field imposes no constraint. All set fields are AND'd
    together: a Firm must clear every constraint you specify to qualify. This is deliberately
    "just filters" per the scope decision — no separate qualification-status field on Firm.
    """

    min_ticket_usd: int | None = None
    max_ticket_usd: int | None = None
    geographies: list[str] | None = None   # Firm must operate in at least one of these
    sectors: list[str] | None = None       # Firm must invest in at least one of these
    require_lead: bool | None = None       # True: must lead. False: must NOT lead. None: no constraint.
    min_fund_size_usd: int | None = None
    require_extantia_overlap: bool = False  # only firms that already know an Extantia portco


def _ticket_size_fits(firm: Firm, criteria: QualificationCriteria) -> bool:
    """True if the firm's typical check range overlaps the round's [min_ticket, max_ticket].

    A firm with no known ticket range only qualifies for an unconstrained search — we don't
    guess a fit we can't back up.
    """
    if not criteria.min_ticket_usd and not criteria.max_ticket_usd:
        return True
    if firm.ticket_size_usd_range is None:
        return False
    firm_min, firm_max = firm.ticket_size_usd_range
    if criteria.max_ticket_usd is not None and firm_min is not None and firm_min > criteria.max_ticket_usd:
        return False
    if criteria.min_ticket_usd is not None and firm_max is not None and firm_max < criteria.min_ticket_usd:
        return False
    return True


def matches(firm: Firm, criteria: QualificationCriteria) -> bool:
    """Whether a single Firm passes every constraint set on `criteria`."""
    if criteria.geographies and not (set(firm.geographies) & set(criteria.geographies)):
        return False
    if criteria.sectors and not (set(firm.sectors) & set(criteria.sectors)):
        return False
    if criteria.require_lead is True and not firm.leads:
        return False
    if criteria.require_lead is False and firm.leads:
        return False
    if criteria.min_fund_size_usd is not None:
        if firm.fund_size_usd is None or firm.fund_size_usd < criteria.min_fund_size_usd:
            return False
    if criteria.require_extantia_overlap and not firm.extantia_portfolio_overlap:
        return False
    if not _ticket_size_fits(firm, criteria):
        return False
    return True


def filter_firms(repo: Repository, criteria: QualificationCriteria) -> list[Firm]:
    """The pure filtering step, independent of any round.

    Useful on its own for previewing a criteria set before committing it to a round — e.g. a
    founder trying "what if I widen geography" and seeing the count change live.
    """
    return [firm for firm in repo.list_firms() if matches(firm, criteria)]


def qualify(repo: Repository, round_id: str, criteria: QualificationCriteria) -> list[PipelineEntry]:
    """Turn the investor universe into this round's qualified list.

    Firms matching `criteria` get a new PipelineEntry (Stage.SOURCED, Outcome.ACTIVE) unless
    they already have one in this round. Existing entries are never touched — re-running
    qualification (e.g. after widening a filter) only adds newly-matching firms, it never
    resets where a live conversation stands. Returns just the newly created entries.
    """
    already_in_round = {entry.firm_id for entry in repo.list_pipeline(round_id)}
    created: list[PipelineEntry] = []
    for firm in filter_firms(repo, criteria):
        if firm.id in already_in_round:
            continue
        entry = repo.add_pipeline_entry(PipelineEntry(
            id=f"pe-{round_id}-{firm.id}",
            round_id=round_id,
            firm_id=firm.id,
            stage=Stage.SOURCED,
            outcome=Outcome.ACTIVE,
            is_lead=bool(firm.leads),
        ))
        created.append(entry)
    return created
