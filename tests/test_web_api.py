"""Tests for the DreamWork HTTP API.

These drive the FastAPI app with fastapi's TestClient — no socket is ever bound. To keep the
tests deterministic we seed `api.repo` directly with known ids rather than relying on demo_seed
(which is written by another agent and may or may not be present).
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from dreamwork.web import api
from dreamwork.core.domain import (
    Firm,
    Partner,
    Round,
    PipelineEntry,
    Stage,
    Outcome,
)
from dreamwork.core.memory_store import InMemoryRepository


ROUND_ID = "rnd-test"
FIRM_ID = "firm-test"
PARTNER_ID = "partner-test"
ENTRY_A = "entry-a"
ENTRY_B = "entry-b"


@pytest.fixture(autouse=True)
def seeded_repo():
    """Give the app a fresh in-memory repo with a known round, firm, partner, and entries."""
    repo = InMemoryRepository()
    repo.add_round(
        Round(
            id=ROUND_ID,
            company="Acme",
            label="Seed",
            target_usd=2_000_000,
            opened_at=date(2026, 1, 15),
        )
    )
    repo.add_firm(
        Firm(
            id=FIRM_ID,
            name="North Star Capital",
            leads=True,
            sectors=["climate", "energy"],
            geographies=["EU", "US"],
            ticket_size_usd_range=(250_000, 1_000_000),
            founder_rating=4,
        )
    )
    repo.add_partner(
        Partner(id=PARTNER_ID, firm_id=FIRM_ID, name="Dana Lee", role="Partner")
    )
    repo.add_pipeline_entry(
        PipelineEntry(
            id=ENTRY_A,
            round_id=ROUND_ID,
            firm_id=FIRM_ID,
            partner_id=PARTNER_ID,
            stage=Stage.CONTACTED,
            outcome=Outcome.ACTIVE,
            is_lead=True,
            ticket_estimate_usd=500_000,
            first_contact_date=date(2026, 2, 1),
            last_contact_date=date(2026, 2, 10),
            next_step="send deck",
        )
    )
    repo.add_pipeline_entry(
        PipelineEntry(
            id=ENTRY_B,
            round_id=ROUND_ID,
            firm_id=FIRM_ID,
            stage=Stage.SOURCED,
            outcome=Outcome.ACTIVE,
        )
    )
    # Swap the module-level repo so the routes read our deterministic data.
    original = api.repo
    api.repo = repo
    yield repo
    api.repo = original


@pytest.fixture
def client():
    return TestClient(api.app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_list_rounds_includes_seeded_round(client):
    resp = client.get("/api/rounds")
    assert resp.status_code == 200
    rounds = resp.json()
    ours = next(r for r in rounds if r["id"] == ROUND_ID)
    assert ours["company"] == "Acme"
    assert ours["label"] == "Seed"
    assert ours["target_usd"] == 2_000_000
    assert ours["opened_at"] == "2026-01-15"


def test_snapshot_shape(client):
    resp = client.get(f"/api/rounds/{ROUND_ID}/snapshot")
    assert resp.status_code == 200
    snap = resp.json()
    assert snap["round_id"] == ROUND_ID
    assert snap["total"] == 2
    assert isinstance(snap["by_stage"], dict)
    assert snap["active_leads"] == 1
    # needs_follow_up must be a list of entry ids (strings), not entry objects.
    assert isinstance(snap["needs_follow_up"], list)
    for item in snap["needs_follow_up"]:
        assert isinstance(item, str)
    # ENTRY_B is SOURCED with no last contact -> needs follow up.
    assert ENTRY_B in snap["needs_follow_up"]


def test_snapshot_missing_round_404(client):
    resp = client.get("/api/rounds/nope/snapshot")
    assert resp.status_code == 404


def test_investors_returns_canonical_rows(client):
    resp = client.get(f"/api/rounds/{ROUND_ID}/investors")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    row = next(r for r in rows if r["entryId"] == ENTRY_A)
    assert row["stage"] == "contacted"
    assert row["outcome"] == "active"
    assert row["isLead"] is True
    assert row["ticketRange"] == [250_000, 1_000_000]
    assert row["firm"] == "North Star Capital"
    assert row["name"] == "Dana Lee"  # partner name wins
    assert row["role"] == "Partner"
    assert row["location"] == "EU"
    assert row["sectors"] == ["climate", "energy"]
    assert row["leads"] is True
    assert row["firstContact"] == "2026-02-01"
    assert row["type"] is None

    # Entry without a partner falls back to the firm name.
    row_b = next(r for r in rows if r["entryId"] == ENTRY_B)
    assert row_b["name"] == "North Star Capital"
    assert row_b["partnerId"] is None
    assert row_b["role"] is None


def test_firms_includes_seeded_firm(client):
    resp = client.get("/api/firms")
    assert resp.status_code == 200
    firms = resp.json()
    ours = next(f for f in firms if f["id"] == FIRM_ID)
    assert ours["name"] == "North Star Capital"
    assert ours["ticket_size_usd_range"] == [250_000, 1_000_000]
    assert ours["founder_rating"] == 4


def test_get_firm_404(client):
    resp = client.get("/api/firms/nope")
    assert resp.status_code == 404


def test_patch_pipeline_updates_stage(client):
    resp = client.patch(f"/api/pipeline/{ENTRY_A}", json={"stage": "meeting"})
    assert resp.status_code == 200
    row = resp.json()
    assert row["stage"] == "meeting"
    assert row["entryId"] == ENTRY_A
    # Persisted?
    resp2 = client.get(f"/api/rounds/{ROUND_ID}/investors")
    updated = next(r for r in resp2.json() if r["entryId"] == ENTRY_A)
    assert updated["stage"] == "meeting"


def test_patch_pipeline_invalid_stage_400(client):
    resp = client.patch(f"/api/pipeline/{ENTRY_A}", json={"stage": "bogus"})
    assert resp.status_code == 400


def test_patch_pipeline_missing_entry_404(client):
    resp = client.patch("/api/pipeline/nope", json={"stage": "meeting"})
    assert resp.status_code == 404
