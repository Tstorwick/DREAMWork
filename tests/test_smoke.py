"""A smoke test — proves the shell runs end-to-end on the in-memory store.

New to this? Run `pytest` from the repo root. Green means the scaffold works and you can build
on it. This is also a template for how to test your own module.
"""

from datetime import date

from dreamwork.core.domain import Firm, Outcome, PipelineEntry, Stage
from dreamwork.core.memory_store import InMemoryRepository, seeded_store
from dreamwork.modules import dashboard
from dreamwork.modules.external import LocalMockBookFace, sanitize


def test_seeded_store_has_a_round_and_firms():
    repo = seeded_store()
    assert repo.get_round("r1") is not None
    assert len(repo.list_firms()) == 2


def test_round_snapshot_counts_and_follow_ups():
    repo = seeded_store()
    snap = dashboard.round_snapshot(repo, "r1", today=date(2026, 6, 26))
    assert snap.total == 2
    assert snap.active_leads == 1
    assert snap.weighted_pipeline_usd == 2_000_000
    # pe1's next step was due 2026-06-25; pe2 is SOURCED, never contacted -> both need follow-up.
    assert len(snap.needs_follow_up) == 2


def test_snoozed_entry_is_hidden_until_its_date():
    repo = InMemoryRepository()
    repo.add_pipeline_entry(PipelineEntry(
        id="x", round_id="r1", firm_id="f1", stage=Stage.CONTACTED,
        outcome=Outcome.ACTIVE, next_step_due=date(2026, 1, 1),
        snooze_until=date(2026, 12, 31),
    ))
    assert dashboard.needs_follow_up(repo, "r1", today=date(2026, 6, 1)) == []


def test_sanitize_only_shares_firm_level_facts():
    firm = Firm(id="f1", name="Breakthrough Energy", fund_size_usd=200_000_000, leads=True)
    facts = sanitize(firm, owner="Chris", connection="Chris")
    fields = {f.field for f in facts}
    assert fields == {"fund_size_usd", "leads"}  # name/id/geos are never emitted as facts


def test_never_share_founder_rating():
    """founder_rating is a private opinion — it must never sanitize into a shareable fact (PR #3)."""
    from dreamwork.modules.external.client import SHAREABLE_FIRM_FIELDS

    assert "founder_rating" not in SHAREABLE_FIRM_FIELDS
    firm = Firm(id="f1", name="Breakthrough Energy", fund_size_usd=200_000_000, founder_rating=4)
    facts = sanitize(firm, owner="Chris", connection="Chris")
    assert "founder_rating" not in {f.field for f in facts}


def test_bookface_corroboration_raises_confidence():
    book = LocalMockBookFace()
    firm = Firm(id="f1", name="Breakthrough Energy", fund_size_usd=200_000_000)
    for owner in ("Chris", "Jamie"):
        for fact in sanitize(firm, owner=owner, connection=owner):
            book.publish(fact)
    facts = book.facts_for_firm("Breakthrough Energy")
    assert len(facts) == 1  # corroborated, not duplicated
    assert facts[0].confidence > 0.5
