"""An in-memory Repository so DreamWork runs with zero setup.

This is not the real database — it's the scaffold that lets everyone build and demo before
Postgres exists. Chris's `modules/qualified_list` provides the real Postgres implementation
behind the same `Repository` contract; when it lands, code that used `InMemoryRepository`
switches by swapping this one object.
"""

from __future__ import annotations

from datetime import date

from dreamwork.core.domain import (
    Firm,
    Interaction,
    IntroRequest,
    Outcome,
    Partner,
    PipelineEntry,
    Round,
    Stage,
)


class InMemoryRepository:
    """Dict-backed implementation of the `Repository` Protocol. Not persistent."""

    def __init__(self) -> None:
        self._firms: dict[str, Firm] = {}
        self._partners: dict[str, Partner] = {}
        self._rounds: dict[str, Round] = {}
        self._pipeline: dict[str, PipelineEntry] = {}
        self._intros: dict[str, IntroRequest] = {}
        self._interactions: dict[str, Interaction] = {}

    # --- Firms & Partners -------------------------------------------------
    def add_firm(self, firm: Firm) -> Firm:
        self._firms[firm.id] = firm
        return firm

    def get_firm(self, firm_id: str) -> Firm | None:
        return self._firms.get(firm_id)

    def list_firms(self) -> list[Firm]:
        return list(self._firms.values())

    def add_partner(self, partner: Partner) -> Partner:
        self._partners[partner.id] = partner
        return partner

    def get_partner(self, partner_id: str) -> Partner | None:
        return self._partners.get(partner_id)

    def list_partners(self, firm_id: str | None = None) -> list[Partner]:
        partners = self._partners.values()
        return [p for p in partners if firm_id is None or p.firm_id == firm_id]

    # --- Rounds -----------------------------------------------------------
    def add_round(self, round_: Round) -> Round:
        self._rounds[round_.id] = round_
        return round_

    def get_round(self, round_id: str) -> Round | None:
        return self._rounds.get(round_id)

    def list_rounds(self) -> list[Round]:
        return list(self._rounds.values())

    # --- Pipeline ---------------------------------------------------------
    def add_pipeline_entry(self, entry: PipelineEntry) -> PipelineEntry:
        self._pipeline[entry.id] = entry
        return entry

    def update_pipeline_entry(self, entry: PipelineEntry) -> PipelineEntry:
        if entry.id not in self._pipeline:
            raise KeyError(f"no pipeline entry {entry.id!r}")
        self._pipeline[entry.id] = entry
        return entry

    def get_pipeline_entry(self, entry_id: str) -> PipelineEntry | None:
        return self._pipeline.get(entry_id)

    def list_pipeline(self, round_id: str) -> list[PipelineEntry]:
        return [e for e in self._pipeline.values() if e.round_id == round_id]

    # --- Intro requests ---------------------------------------------------
    def add_intro_request(self, req: IntroRequest) -> IntroRequest:
        self._intros[req.id] = req
        return req

    def list_intro_requests(self, round_id: str) -> list[IntroRequest]:
        return [r for r in self._intros.values() if r.round_id == round_id]

    # --- Interactions (activity feed) -------------------------------------
    def add_interaction(self, interaction: Interaction) -> Interaction:
        self._interactions[interaction.id] = interaction
        return interaction

    def list_interactions(self, round_id: str) -> list[Interaction]:
        return [i for i in self._interactions.values() if i.round_id == round_id]


def seeded_store() -> InMemoryRepository:
    """A small demo dataset so newcomers see something real on first run."""
    repo = InMemoryRepository()

    round_ = repo.add_round(
        Round(id="r1", company="Acme Climate", target_usd=5_000_000, label="Seed",
              opened_at=date(2026, 6, 1))
    )

    repo.add_firm(Firm(id="f1", name="Breakthrough Energy", fund_size_usd=200_000_000,
                       leads=True, geographies=["US", "EU"], sectors=["climate"],
                       follows_on=True, dossier_path="data/dossiers/firm/f1.md"))
    repo.add_firm(Firm(id="f2", name="Toyota Climate Fund", leads=False,
                       geographies=["Global"], sectors=["climate", "mobility"]))

    repo.add_partner(Partner(id="p1", firm_id="f1", name="Lisa Chen", role="Partner",
                             influence="Decision maker on climate deals."))

    repo.add_pipeline_entry(PipelineEntry(
        id="pe1", round_id="r1", firm_id="f1", partner_id="p1",
        stage=Stage.IN_CONVERSATION, outcome=Outcome.ACTIVE, is_lead=True,
        ticket_estimate_usd=2_000_000, first_contact_date=date(2026, 6, 5),
        last_contact_date=date(2026, 6, 20), next_step="Send updated deck",
        next_step_due=date(2026, 6, 25),
    ))
    repo.add_pipeline_entry(PipelineEntry(
        id="pe2", round_id="r1", firm_id="f2",
        stage=Stage.SOURCED, outcome=Outcome.ACTIVE, is_lead=False,
    ))

    return repo
