"""Tests for the Notion importer — link parsing, property mapping, pagination, permissions.

No token and no network: a FakeNotionClient returns canned API responses, so the pure parsing
and pagination logic is exercised exactly as against the real API.
"""

import pytest

from dreamwork.core.domain import Round, Stage
from dreamwork.core.memory_store import InMemoryRepository
from dreamwork.modules import onboarding
from dreamwork.modules.onboarding.sources.notion import (
    NotionAPIError,
    NotionImporter,
    NotionLinkError,
    NotionPermissionError,
    extract_database_id,
    property_to_value,
)


@pytest.fixture(autouse=True)
def _tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


# --- helpers to build Notion API objects -----------------------------------
def _title(text):
    return {"type": "title", "title": [{"plain_text": text}]}


def _select(name):
    return {"type": "select", "select": {"name": name}}


def _number(n):
    return {"type": "number", "number": n}


def _people(*names):
    return {"type": "people", "people": [{"name": n} for n in names]}


def _multi(*names):
    return {"type": "multi_select", "multi_select": [{"name": n} for n in names]}


def _page(**props):
    return {"object": "page", "properties": props}


class FakeNotionClient:
    """Returns canned responses, splitting rows across pages to exercise pagination."""

    def __init__(self, pages, *, per_page=1, error_code=None):
        self._pages = pages
        self._per_page = per_page
        self._error_code = error_code

    def query(self, database_id, start_cursor=None):
        if self._error_code:
            raise NotionAPIError(code=self._error_code)
        start = int(start_cursor) if start_cursor else 0
        chunk = self._pages[start : start + self._per_page]
        end = start + self._per_page
        has_more = end < len(self._pages)
        return {
            "results": chunk,
            "has_more": has_more,
            "next_cursor": str(end) if has_more else None,
        }


# --- link parsing -----------------------------------------------------------
def test_extract_database_id_ignores_view_id():
    dbid = "11112222333344445555666677778888"
    link = f"https://www.notion.so/workspace/My-Investors-{dbid}?v=99998888"
    assert extract_database_id(link) == "11112222-3333-4444-5555-666677778888"


def test_extract_database_id_from_app_link():
    dbid = "aaaabbbbccccddddeeeeffff00001111"
    assert extract_database_id(f"https://app.notion.com/p/{dbid}?v=zzzz").replace("-", "") == dbid


def test_bad_link_raises():
    with pytest.raises(NotionLinkError):
        extract_database_id("https://example.com/not-notion")


# --- property extraction ----------------------------------------------------
def test_property_to_value_covers_the_common_types():
    assert property_to_value(_title("Sequoia")) == "Sequoia"
    assert property_to_value(_select("Diligence")) == "Diligence"
    assert property_to_value(_number(2_000_000)) == 2_000_000
    assert property_to_value(_people("Roelof Botha")) == "Roelof Botha"
    assert property_to_value(_multi("climate", "mobility")) == ["climate", "mobility"]
    assert property_to_value({"type": "select", "select": None}) is None


# --- pagination + end to end ------------------------------------------------
def _repo():
    repo = InMemoryRepository()
    repo.add_round(Round(id="r1", company="Acme", label="Seed"))
    return repo


def test_pagination_collects_every_row():
    pages = [
        _page(Firm=_title("Sequoia"), Partner=_people("Roelof"), Status=_select("in conversation")),
        _page(Firm=_title("Benchmark"), Partner=_people("Sarah"), **{"Check Size": _number(1_500_000)}),
        _page(Firm=_title("Accel"), Focus=_multi("saas", "fintech")),
    ]
    client = FakeNotionClient(pages, per_page=1)  # force 3 separate API pages
    importer = NotionImporter("https://app.notion.com/p/" + "a" * 32 + "?v=x", client)
    preview = importer.preview()
    assert len(preview.records) == 3
    assert any("Imported all 3 rows" in w for w in preview.warnings)


def test_import_notion_into_core():
    pages = [
        _page(Firm=_title("Sequoia"), Partner=_people("Roelof Botha"),
              Status=_select("in conversation"), **{"Check Size": _number(2_000_000)},
              Focus=_multi("climate")),
    ]
    repo = _repo()
    client = FakeNotionClient(pages)
    result = onboarding.import_notion(repo, "r1", "notion.so/x-" + "b" * 32 + "?v=y", client)
    assert result.firms_created == 1
    assert result.partners_created == 1
    entry = repo.list_pipeline("r1")[0]
    assert entry.stage == Stage.IN_CONVERSATION
    assert entry.ticket_estimate_usd == 2_000_000
    assert repo.list_firms()[0].sectors == ["climate"]


def test_unshared_database_raises_permission_error_with_recovery():
    client = FakeNotionClient([], error_code="object_not_found")
    importer = NotionImporter("https://app.notion.com/p/" + "c" * 32, client)
    with pytest.raises(NotionPermissionError) as exc:
        importer.preview()
    assert "share" in exc.value.recovery.lower() or "connect" in exc.value.recovery.lower()
    assert exc.value.share_url.startswith("https://www.notion.so/")


def test_empty_database_warns():
    importer = NotionImporter("https://app.notion.com/p/" + "d" * 32, FakeNotionClient([]))
    preview = importer.preview()
    assert preview.records == []
    assert any("empty" in w.lower() for w in preview.warnings)
