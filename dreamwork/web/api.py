"""HTTP API for DreamWork — exposes module logic as JSON and serves the static frontend.

This is a thin translation layer: it validates input, calls into `core`'s Repository and the
`dashboard` module, and serializes domain objects into the exact JSON shapes the frontend
consumes. It holds no business rules of its own (those live in the modules).

Serialization conventions:
    enum   -> `.value`  (e.g. Stage.SOURCED -> "sourced")
    date   -> `.isoformat()` or null
    None   -> null

Run it with `python -m dreamwork.web.api` (starts uvicorn), or drive it in tests with
fastapi's TestClient without ever binding a socket.
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dreamwork.config import get_repository
from dreamwork.core.domain import (
    Firm,
    IntroRequest,
    PipelineEntry,
    Round,
    Stage,
    Outcome,
)
from dreamwork.core.repository import Repository
from dreamwork.modules import dashboard


# --- helpers ------------------------------------------------------------------


def _iso(d: date | None) -> str | None:
    """A date as an ISO string, or null."""
    return d.isoformat() if d is not None else None


def _ticket_range(firm: Firm) -> list:
    """firm.ticket_size_usd_range serialized as [min, max]; [null, null] when unset."""
    rng = firm.ticket_size_usd_range
    if not rng:
        return [None, None]
    return [rng[0], rng[1]]


def _round_dict(round_: Round) -> dict:
    return {
        "id": round_.id,
        "company": round_.company,
        "label": round_.label,
        "target_usd": round_.target_usd,
        "opened_at": _iso(round_.opened_at),
    }


def _firm_dict(firm: Firm) -> dict:
    """Every Firm field. founder_rating is included — this is the founder's own internal UI;
    it's only barred from the EXTERNAL book-face, not from here."""
    return {
        "id": firm.id,
        "name": firm.name,
        "website": firm.website,
        "fund_size_usd": firm.fund_size_usd,
        "aum_usd": firm.aum_usd,
        "leads": firm.leads,
        "geographies": firm.geographies,
        "sectors": firm.sectors,
        "follows_on": firm.follows_on,
        "team_members": firm.team_members,
        "ticket_size_usd_range": _ticket_range(firm)
        if firm.ticket_size_usd_range
        else None,
        "portfolio_companies": firm.portfolio_companies,
        "extantia_portfolio_overlap": firm.extantia_portfolio_overlap,
        "still_investing": firm.still_investing,
        "founder_rating": firm.founder_rating,
        "dossier_path": firm.dossier_path,
    }


def _intro_dict(req: IntroRequest) -> dict:
    return {
        "id": req.id,
        "round_id": req.round_id,
        "target_firm_id": req.target_firm_id,
        "asked_of": req.asked_of,
        "target_partner_id": req.target_partner_id,
        "channel": req.channel,
        "status": req.status,
        "requested_at": _iso(req.requested_at),
    }


def _investor_row(repo: Repository, entry: PipelineEntry) -> dict:
    """A PipelineEntry joined to its Firm (and Partner, if any) — the exact shape the
    frontend investor table consumes."""
    firm = repo.get_firm(entry.firm_id)
    partner = repo.get_partner(entry.partner_id) if entry.partner_id else None
    return {
        "id": entry.id,
        "entryId": entry.id,
        "firmId": firm.id if firm else entry.firm_id,
        "partnerId": partner.id if partner else None,
        "stage": entry.stage.value,
        "outcome": entry.outcome.value,
        "isLead": entry.is_lead,
        "ticketEstimateUsd": entry.ticket_estimate_usd,
        "firstContact": _iso(entry.first_contact_date),
        "lastActivity": _iso(entry.last_contact_date),
        "nextStep": entry.next_step,
        "snoozeUntil": _iso(entry.snooze_until),
        "name": (partner.name if partner else (firm.name if firm else None)),
        "role": partner.role if partner else None,
        "firm": firm.name if firm else None,
        "type": None,
        "ticketRange": _ticket_range(firm) if firm else [None, None],
        "sectors": firm.sectors if firm else [],
        "location": (firm.geographies[0] if firm and firm.geographies else None),
        "leads": firm.leads if firm else None,
    }


# --- app + repo ---------------------------------------------------------------

app = FastAPI(title="DreamWork")

repo = get_repository()

# Seed demo data if the store is empty. demo_seed is written by another agent and may not
# exist yet — tolerate its absence so this module always imports and runs.
try:
    from dreamwork.web.demo_seed import seed_demo

    if not repo.list_rounds():
        seed_demo(repo)
except Exception:
    pass


class PipelinePatch(BaseModel):
    stage: str | None = None
    outcome: str | None = None


# --- API routes ---------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/rounds")
def list_rounds() -> list:
    return [_round_dict(r) for r in repo.list_rounds()]


@app.get("/api/rounds/{round_id}/snapshot")
def round_snapshot(round_id: str) -> dict:
    if repo.get_round(round_id) is None:
        raise HTTPException(status_code=404, detail="round not found")
    snap = dashboard.round_snapshot(repo, round_id)
    return {
        "round_id": snap.round_id,
        "total": snap.total,
        "by_stage": snap.by_stage,
        "active_leads": snap.active_leads,
        "weighted_pipeline_usd": snap.weighted_pipeline_usd,
        "needs_follow_up": [e.id for e in snap.needs_follow_up],
    }


@app.get("/api/rounds/{round_id}/investors")
def round_investors(round_id: str) -> list:
    return [_investor_row(repo, e) for e in repo.list_pipeline(round_id)]


@app.get("/api/rounds/{round_id}/intros")
def round_intros(round_id: str) -> list:
    return [_intro_dict(req) for req in repo.list_intro_requests(round_id)]


@app.get("/api/firms")
def list_firms() -> list:
    return [_firm_dict(f) for f in repo.list_firms()]


@app.get("/api/firms/{firm_id}")
def get_firm(firm_id: str) -> dict:
    firm = repo.get_firm(firm_id)
    if firm is None:
        raise HTTPException(status_code=404, detail="firm not found")
    return _firm_dict(firm)


@app.patch("/api/pipeline/{entry_id}")
def patch_pipeline(entry_id: str, patch: PipelinePatch) -> dict:
    # Validate provided values against the enums before touching the store.
    new_stage: Stage | None = None
    new_outcome: Outcome | None = None
    if patch.stage is not None:
        try:
            new_stage = Stage(patch.stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid stage: {patch.stage}")
    if patch.outcome is not None:
        try:
            new_outcome = Outcome(patch.outcome)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"invalid outcome: {patch.outcome}"
            )

    entry = repo.get_pipeline_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="pipeline entry not found")

    if new_stage is not None:
        entry.stage = new_stage
    if new_outcome is not None:
        entry.outcome = new_outcome
    repo.update_pipeline_entry(entry)
    return _investor_row(repo, entry)


# Mount the static UI LAST so it doesn't shadow the /api routes above.
app.mount(
    "/",
    StaticFiles(directory="prototypes/dashboard-web", html=True),
    name="ui",
)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
