"""Tests for the onboarding importer: coercion, mapping, parsing, and merge/dedupe.

Run `pytest` from the repo root. These cover the pure logic — no network, no accounts. The
Notion importer's own tests live in test_onboarding_notion.py.
"""

import pytest

from dreamwork.core.domain import Round, Stage
from dreamwork.core.memory_store import InMemoryRepository, seeded_store
from dreamwork.modules import onboarding
from dreamwork.modules.onboarding import coerce
from dreamwork.modules.onboarding.mapping import auto_map
from dreamwork.modules.onboarding.provenance import Provenanced, Source, prefer
from dreamwork.modules.onboarding.sources.tabular import parse_table


@pytest.fixture(autouse=True)
def _tmp_cwd(tmp_path, monkeypatch):
    """Dossiers write to data/dossiers/ relative to cwd — keep tests out of the real repo tree."""
    monkeypatch.chdir(tmp_path)


def _repo_with_round():
    repo = InMemoryRepository()
    repo.add_round(Round(id="r1", company="Acme Climate", label="Seed"))
    return repo


# --- coercion ---------------------------------------------------------------
def test_money_parsing():
    assert coerce.money_to_int("$2M") == 2_000_000
    assert coerce.money_to_int("2,000,000") == 2_000_000
    assert coerce.money_to_int("500k") == 500_000
    assert coerce.money_to_int("garbage") is None


def test_stage_from_free_text():
    assert coerce.to_stage("in convo") == Stage.IN_CONVERSATION
    assert coerce.to_stage("Term Sheet") == Stage.COMMITTED
    assert coerce.to_stage("") is None


def test_list_and_bool():
    assert coerce.to_list("climate, mobility") == ["climate", "mobility"]
    assert coerce.to_bool("yes") is True
    assert coerce.to_bool("no") is False


# --- provenance -------------------------------------------------------------
def test_human_confirmed_outranks_inferred():
    inferred = Provenanced("A", Source.PASTE)
    confirmed = Provenanced("B", Source.HUMAN_CONFIRMED)
    assert prefer(inferred, confirmed).value == "B"
    assert prefer(confirmed, inferred).value == "B"  # confirmed stays even when it arrives first


def test_higher_confidence_wins():
    weak = Provenanced("A", Source.PASTE)      # 0.5
    strong = Provenanced("B", Source.CALENDAR)  # 0.9
    assert prefer(weak, strong).value == "B"


# --- mapping ----------------------------------------------------------------
def test_auto_map_picks_the_obvious_columns():
    m = auto_map(["Firm", "Lead Partner", "Check Size", "Status", "Random"])
    assert m.mapping["Firm"] == "firm_name"
    assert m.mapping["Lead Partner"] == "partner_name"
    assert m.mapping["Check Size"] == "ticket_estimate_usd"
    assert m.mapping["Status"] == "stage"
    assert "Random" in m.unmapped


# --- parsing ----------------------------------------------------------------
def test_parse_csv_and_markdown_agree():
    csv_text = "Firm,Partner\nSequoia,Roelof\n"
    md_text = "| Firm | Partner |\n|------|---------|\n| Sequoia | Roelof |\n"
    assert parse_table(csv_text).headers == ["Firm", "Partner"]
    assert parse_table(md_text).headers == ["Firm", "Partner"]
    assert parse_table(md_text).rows == [["Sequoia", "Roelof"]]


# --- end-to-end import ------------------------------------------------------
def test_import_captable_creates_rows():
    repo = _repo_with_round()
    rows = [
        {"Firm": "Sequoia", "Partner": "Roelof", "Check": "$2M", "Status": "in conversation"},
        {"Firm": "Benchmark", "Partner": "Sarah", "Check": "1,500,000"},
    ]
    result = onboarding.import_captable(repo, "r1", rows)
    assert result.firms_created == 2
    assert result.partners_created == 2
    assert result.entries_created == 2

    firms = {f.name for f in repo.list_firms()}
    assert firms == {"Sequoia", "Benchmark"}
    entries = repo.list_pipeline("r1")
    seq = next(e for e in entries if repo.get_firm(e.firm_id).name == "Sequoia")
    assert seq.ticket_estimate_usd == 2_000_000
    assert seq.stage == Stage.IN_CONVERSATION


def test_reimport_merges_and_does_not_duplicate():
    repo = _repo_with_round()
    onboarding.import_captable(repo, "r1", [{"Firm": "Sequoia", "Partner": "Roelof"}])
    # Re-import the same firm (different case/punctuation) with a new fact and a fillable blank.
    result = onboarding.import_captable(repo, "r1", [{"Firm": "SEQUOIA!", "Fund Size": "$8B"}])
    assert len(repo.list_firms()) == 1  # matched despite case/punctuation differences
    assert result.firms_merged >= 1
    assert repo.list_firms()[0].fund_size_usd == 8_000_000_000  # blank got filled


def test_inferred_import_does_not_clobber_existing_value():
    repo = _repo_with_round()
    onboarding.import_captable(repo, "r1", [{"Firm": "Sequoia", "Fund Size": "$8B"}])
    onboarding.import_captable(repo, "r1", [{"Firm": "Sequoia", "Fund Size": "$1B"}])
    # An inferred re-import must not overwrite a value that's already set.
    assert repo.list_firms()[0].fund_size_usd == 8_000_000_000


def test_paste_a_markdown_table():
    repo = _repo_with_round()
    text = "| Firm | Partner | Stage |\n|---|---|---|\n| Accel | Rich | met |\n"
    result = onboarding.import_tabular(repo, "r1", text)
    assert result.firms_created == 1
    assert repo.list_pipeline("r1")[0].stage == Stage.MEETING


def test_no_investors_discovered_warns_not_crashes():
    repo = _repo_with_round()
    result = onboarding.import_tabular(repo, "r1", "just some prose with no columns")
    assert result.firms_created == 0
    assert any("No investors" in w for w in result.warnings)


def test_dossier_gets_source_chip():
    repo = _repo_with_round()
    onboarding.import_captable(repo, "r1", [{"Firm": "Sequoia", "Check": "$2M"}])
    firm = repo.list_firms()[0]
    assert firm.dossier_path is not None
    from dreamwork.core.dossiers import read_dossier

    body = read_dossier(firm.dossier_path)
    assert "From CSV" in body


def test_import_into_seeded_store_merges_with_existing_firm():
    repo = seeded_store()  # already has "Breakthrough Energy"
    before = len(repo.list_firms())
    result = onboarding.import_captable(repo, "r1", [{"Firm": "Breakthrough Energy", "Partner": "New Person"}])
    assert len(repo.list_firms()) == before  # merged, not added
    assert result.firms_merged >= 0 and result.partners_created == 1
