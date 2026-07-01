"""Tests for modules/qualified_list — the qualification half of Chris's module.

Run with `pytest` from the repo root, same as test_smoke.py.
"""

from dreamwork.core.domain import Firm
from dreamwork.core.memory_store import InMemoryRepository
from dreamwork.modules.qualified_list import QualificationCriteria, filter_firms, matches, qualify


def _repo_with_firms() -> InMemoryRepository:
    repo = InMemoryRepository()
    repo.add_firm(Firm(
        id="f1", name="Breakthrough Energy", fund_size_usd=200_000_000, leads=True,
        geographies=["US", "EU"], sectors=["climate"],
        ticket_size_usd_range=(1_000_000, 5_000_000),
        extantia_portfolio_overlap=["Fervo Energy"],
    ))
    repo.add_firm(Firm(
        id="f2", name="Toyota Climate Fund", leads=False,
        geographies=["Global"], sectors=["climate", "mobility"], fund_size_usd=50_000_000,
        ticket_size_usd_range=(500_000, 2_000_000),
    ))
    repo.add_firm(Firm(
        id="f3", name="Generic Angel", leads=False,
        geographies=["US"], sectors=["saas"],
    ))
    return repo


def test_matches_is_true_with_no_criteria():
    repo = _repo_with_firms()
    firm = repo.get_firm("f3")
    assert matches(firm, QualificationCriteria())


def test_sector_filter_excludes_non_matching_firms():
    repo = _repo_with_firms()
    criteria = QualificationCriteria(sectors=["climate"])
    names = {f.name for f in filter_firms(repo, criteria)}
    assert names == {"Breakthrough Energy", "Toyota Climate Fund"}


def test_require_lead_true_excludes_follow_only_firms():
    repo = _repo_with_firms()
    criteria = QualificationCriteria(require_lead=True)
    names = {f.name for f in filter_firms(repo, criteria)}
    assert names == {"Breakthrough Energy"}


def test_ticket_size_range_must_overlap():
    repo = _repo_with_firms()
    # Round wants a $3-4M check: only f1's $1-5M range overlaps; f2's $0.5-2M does not.
    criteria = QualificationCriteria(min_ticket_usd=3_000_000, max_ticket_usd=4_000_000)
    names = {f.name for f in filter_firms(repo, criteria)}
    assert names == {"Breakthrough Energy"}


def test_ticket_size_excludes_firms_with_unknown_range():
    repo = _repo_with_firms()
    criteria = QualificationCriteria(min_ticket_usd=100_000)
    names = {f.name for f in filter_firms(repo, criteria)}
    # f3 has no ticket_size_usd_range set, so it doesn't qualify for a size-constrained search.
    assert "Generic Angel" not in names


def test_require_extantia_overlap_only_returns_firms_with_overlap():
    repo = _repo_with_firms()
    criteria = QualificationCriteria(require_extantia_overlap=True)
    names = {f.name for f in filter_firms(repo, criteria)}
    assert names == {"Breakthrough Energy"}


def test_qualify_creates_pipeline_entries_for_matching_firms():
    repo = _repo_with_firms()
    from dreamwork.core.domain import Round
    repo.add_round(Round(id="r1", company="Acme Climate"))

    criteria = QualificationCriteria(sectors=["climate"])
    created = qualify(repo, "r1", criteria)

    assert {e.firm_id for e in created} == {"f1", "f2"}
    assert all(e.round_id == "r1" for e in created)
    entries = repo.list_pipeline("r1")
    assert len(entries) == 2


def test_qualify_is_idempotent_and_never_touches_existing_entries():
    repo = _repo_with_firms()
    from dreamwork.core.domain import Round
    repo.add_round(Round(id="r1", company="Acme Climate"))

    criteria = QualificationCriteria(sectors=["climate"])
    first_run = qualify(repo, "r1", criteria)
    assert len(first_run) == 2

    # Manually advance one entry, as if a real conversation happened.
    from dreamwork.core.domain import Stage
    entry = repo.get_pipeline_entry("pe-r1-f1")
    entry.stage = Stage.MEETING
    repo.update_pipeline_entry(entry)

    # Re-running qualification with the same criteria must not create duplicates or reset stage.
    second_run = qualify(repo, "r1", criteria)
    assert second_run == []
    assert repo.get_pipeline_entry("pe-r1-f1").stage == Stage.MEETING
    assert len(repo.list_pipeline("r1")) == 2
