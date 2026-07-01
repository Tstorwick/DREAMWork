"""Contract tests — the promise that every Repository implementation behaves identically.

Each test runs against *both* stores via the `repo` fixture:
  - InMemoryRepository — always.
  - PostgresRepository — only when DREAMWORK_TEST_DB_URL points at a throwaway Postgres, e.g.:
      docker run --rm -e POSTGRES_PASSWORD=x -p 5432:5432 postgres:16
      DREAMWORK_TEST_DB_URL=postgresql://postgres:x@localhost:5432/postgres pytest

If they both pass this file, swapping one for the other changes nothing else in the app — which
is the entire point of coding against the `Repository` Protocol.
"""

import os
from datetime import date

import pytest

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
from dreamwork.core.memory_store import InMemoryRepository

TEST_DB_ENV = "DREAMWORK_TEST_DB_URL"


def _make_memory():
    return InMemoryRepository()


def _make_postgres():
    from dreamwork.modules.qualified_list.store import PostgresRepository

    repo = PostgresRepository(os.environ[TEST_DB_ENV])
    repo._truncate_all()  # clean slate for each test
    return repo


_params = [pytest.param(_make_memory, id="memory")]
if os.environ.get(TEST_DB_ENV):
    _params.append(pytest.param(_make_postgres, id="postgres"))


@pytest.fixture(params=_params)
def repo(request):
    return request.param()


# --- helpers to build a valid graph (Postgres enforces the FKs the in-memory store doesn't) ---

def _seed_firm_and_round(repo, firm_id="f1", round_id="r1"):
    repo.add_firm(Firm(id=firm_id, name="Breakthrough Energy"))
    repo.add_round(Round(id=round_id, company="Acme Climate"))


# --- Firms --------------------------------------------------------------------

def test_firm_roundtrip_preserves_every_field_type(repo):
    firm = Firm(
        id="f1", name="Sequoia", website="https://sequoiacap.com",
        fund_size_usd=8_000_000_000, aum_usd=85_000_000_000, leads=True,
        geographies=["US", "EU"], sectors=["climate", "fintech"], follows_on=False,
        team_members=["Roelof Botha — Partner"], ticket_size_usd_range=(1_000_000, 5_000_000),
        portfolio_companies=["Stripe", "Klarna"], extantia_portfolio_overlap=["Fervo"],
        still_investing=True, founder_rating=4, dossier_path="data/dossiers/firm/f1.md",
    )
    repo.add_firm(firm)
    got = repo.get_firm("f1")
    assert got == firm  # dataclass equality: lists, tuple range, bools, ints all survive


def test_get_missing_returns_none(repo):
    assert repo.get_firm("nope") is None
    assert repo.get_partner("nope") is None
    assert repo.get_round("nope") is None
    assert repo.get_pipeline_entry("nope") is None


def test_add_firm_overwrites_by_id(repo):
    repo.add_firm(Firm(id="f1", name="Old Name"))
    repo.add_firm(Firm(id="f1", name="New Name", leads=True))
    assert len(repo.list_firms()) == 1
    assert repo.get_firm("f1").name == "New Name"
    assert repo.get_firm("f1").leads is True


def test_firm_with_no_ticket_range_roundtrips_as_none(repo):
    repo.add_firm(Firm(id="f1", name="Angel"))
    assert repo.get_firm("f1").ticket_size_usd_range is None


# --- Partners -----------------------------------------------------------------

def test_list_partners_filters_by_firm(repo):
    repo.add_firm(Firm(id="f1", name="Sequoia"))
    repo.add_firm(Firm(id="f2", name="Benchmark"))
    repo.add_partner(Partner(id="p1", firm_id="f1", name="Roelof", role="Partner"))
    repo.add_partner(Partner(id="p2", firm_id="f1", name="Alfred"))
    repo.add_partner(Partner(id="p3", firm_id="f2", name="Sarah"))
    assert {p.id for p in repo.list_partners("f1")} == {"p1", "p2"}
    assert {p.id for p in repo.list_partners()} == {"p1", "p2", "p3"}


# --- Rounds -------------------------------------------------------------------

def test_round_roundtrip(repo):
    r = Round(id="r1", company="Acme", target_usd=5_000_000, label="Seed",
              opened_at=date(2026, 6, 1))
    repo.add_round(r)
    assert repo.get_round("r1") == r


# --- Pipeline -----------------------------------------------------------------

def test_pipeline_add_list_and_enums_survive(repo):
    _seed_firm_and_round(repo)
    entry = PipelineEntry(
        id="pe1", round_id="r1", firm_id="f1", stage=Stage.DILIGENCE,
        outcome=Outcome.NEXT_ROUND, is_lead=True, ticket_estimate_usd=2_000_000,
        first_contact_date=date(2026, 6, 5), next_step="Send deck", next_step_due=date(2026, 6, 9),
    )
    repo.add_pipeline_entry(entry)
    got = repo.list_pipeline("r1")
    assert len(got) == 1
    assert got[0] == entry
    assert got[0].stage is Stage.DILIGENCE and got[0].outcome is Outcome.NEXT_ROUND


def test_list_pipeline_scopes_to_round(repo):
    repo.add_firm(Firm(id="f1", name="Sequoia"))
    repo.add_round(Round(id="r1", company="Acme"))
    repo.add_round(Round(id="r2", company="Acme II"))
    repo.add_pipeline_entry(PipelineEntry(id="pe1", round_id="r1", firm_id="f1"))
    repo.add_pipeline_entry(PipelineEntry(id="pe2", round_id="r2", firm_id="f1"))
    assert {e.id for e in repo.list_pipeline("r1")} == {"pe1"}


def test_update_pipeline_entry_persists_changes(repo):
    _seed_firm_and_round(repo)
    repo.add_pipeline_entry(PipelineEntry(id="pe1", round_id="r1", firm_id="f1"))
    entry = repo.get_pipeline_entry("pe1")
    entry.stage = Stage.MEETING
    entry.last_contact_date = date(2026, 6, 20)
    repo.update_pipeline_entry(entry)
    reloaded = repo.get_pipeline_entry("pe1")
    assert reloaded.stage is Stage.MEETING
    assert reloaded.last_contact_date == date(2026, 6, 20)


def test_update_missing_pipeline_entry_raises_keyerror(repo):
    with pytest.raises(KeyError):
        repo.update_pipeline_entry(PipelineEntry(id="ghost", round_id="r1", firm_id="f1"))


# --- Intro requests -----------------------------------------------------------

def test_intro_requests_scoped_to_round(repo):
    repo.add_firm(Firm(id="f1", name="Sequoia"))
    repo.add_round(Round(id="r1", company="Acme"))
    repo.add_intro_request(IntroRequest(
        id="ir1", round_id="r1", target_firm_id="f1", asked_of="A mutual",
        channel="email", status="requested", requested_at=date(2026, 6, 10),
    ))
    got = repo.list_intro_requests("r1")
    assert len(got) == 1 and got[0].asked_of == "A mutual"
    assert repo.list_intro_requests("r2") == []


# --- Interactions -------------------------------------------------------------

def test_interaction_roundtrip_preserves_every_field(repo):
    _seed_firm_and_round(repo)
    repo.add_pipeline_entry(PipelineEntry(id="pe1", round_id="r1", firm_id="f1"))
    interaction = Interaction(
        id="in1", round_id="r1", entry_id="pe1", kind="call",
        text="Left a voicemail about the deck.", occurred_at=date(2026, 6, 12),
    )
    repo.add_interaction(interaction)
    got = repo.list_interactions("r1")
    assert len(got) == 1
    assert got[0] == interaction  # dataclass equality: kind, text, date all survive


def test_list_interactions_scopes_to_round(repo):
    # Two rounds, each with its own entry; an interaction in r1 must not show under r2.
    repo.add_firm(Firm(id="f1", name="Breakthrough Energy"))
    repo.add_round(Round(id="r1", company="Acme Climate"))
    repo.add_round(Round(id="r2", company="Acme II"))
    repo.add_pipeline_entry(PipelineEntry(id="pe1", round_id="r1", firm_id="f1"))
    repo.add_pipeline_entry(PipelineEntry(id="pe2", round_id="r2", firm_id="f1"))
    repo.add_interaction(Interaction(id="in1", round_id="r1", entry_id="pe1", kind="note", text="r1"))
    repo.add_interaction(Interaction(id="in2", round_id="r2", entry_id="pe2", kind="note", text="r2"))
    assert {i.id for i in repo.list_interactions("r1")} == {"in1"}
    assert {i.id for i in repo.list_interactions("r2")} == {"in2"}
