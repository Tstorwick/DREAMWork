"""Notion database importer — the common real case (spec §4.5.1).

A pasted Notion link is usually a *private* database view: `app.notion.com/p/<id>?v=<view-id>`.
Two facts drive this code:

  1. **It's private and OAuth-gated.** The link can't be read from the URL alone. The user must
     authorize the integration *and* share the specific page/database with it. When they haven't,
     Notion returns an object-not-found/permission response — we detect that and surface the exact
     "share this page with DreamWork" recovery (spec §6), rather than a dead end.
  2. **The `?v=` is a view; the API reads the database.** A view's filters/sorts are not exposed
     via the API, so *every* row returns. We resolve the database id from the link, query the
     database, and paginate `has_more` / `next_cursor` (100/page) until complete.

The network client is injected (`NotionClient` Protocol), so all parsing/mapping/pagination logic
is testable with fixtures — no token, no network. `build_notion_client()` wires the real SDK.
"""

from __future__ import annotations

import re
from typing import Protocol

from dreamwork.modules.onboarding.build import record_from_mapped
from dreamwork.modules.onboarding.mapping import auto_map
from dreamwork.modules.onboarding.provenance import Source
from dreamwork.modules.onboarding.records import InvestorRecord
from dreamwork.modules.onboarding.sources import ImportPreview

# A Notion id is 32 hex chars, sometimes dash-formatted as a UUID.
_ID_RE = re.compile(r"([0-9a-fA-F]{32}|[0-9a-fA-F-]{36})")
# Notion API error codes that all mean "the integration can't see this page".
_PERMISSION_CODES = {"object_not_found", "unauthorized", "restricted_resource"}


class NotionLinkError(ValueError):
    """The pasted text isn't a resolvable Notion database link."""


class NotionAPIError(Exception):
    """A structured error from the Notion API (carries the API `code`)."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class NotionPermissionError(Exception):
    """The database exists but wasn't shared with the integration — the top connect failure.

    Carries a plain-language recovery and (where possible) a deep link to the share dialog.
    """

    def __init__(self, database_id: str) -> None:
        self.database_id = database_id
        self.recovery = (
            "DreamWork can't see that database yet. In Notion, open the page, click the ••• menu, "
            "choose 'Connections' → 'Connect to' → DreamWork, then import again."
        )
        self.share_url = f"https://www.notion.so/{database_id.replace('-', '')}"
        super().__init__(self.recovery)


class NotionClient(Protocol):
    """The slice of the Notion API we use. `query` raises NotionAPIError on API errors."""

    def query(self, database_id: str, start_cursor: str | None = None) -> dict: ...


def extract_database_id(link: str) -> str:
    """Pull the database/page id out of a pasted Notion link (ignores the `?v=` view id)."""
    text = link.strip()
    # Prefer the path segment; the ?v= view id must never be mistaken for the database id.
    path = text.split("?", 1)[0]
    match = _ID_RE.search(path)
    if not match:
        # Fall back to a `?p=<id>` param if the path had none.
        pmatch = re.search(r"[?&]p=([0-9a-fA-F-]{32,36})", text)
        if pmatch:
            return _dash(pmatch.group(1))
        raise NotionLinkError(f"Couldn't find a Notion database id in {link!r}.")
    return _dash(match.group(1))


def _dash(raw: str) -> str:
    """Normalise a 32-char id to dashed UUID form (what the API expects)."""
    h = raw.replace("-", "")
    if len(h) != 32:
        return raw
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def property_to_value(prop: dict) -> object | None:
    """Extract a plain Python value from one Notion property object, by its `type` (spec §4.5.1)."""
    kind = prop.get("type")
    data = prop.get(kind)
    if data is None:
        return None
    if kind in ("title", "rich_text"):
        text = "".join(part.get("plain_text", "") for part in data).strip()
        return text or None
    if kind in ("select", "status"):
        return data.get("name")
    if kind == "multi_select":
        return [item["name"] for item in data] or None
    if kind == "people":
        names = [p.get("name") for p in data if p.get("name")]
        return ", ".join(names) or None
    if kind == "date":
        return data.get("start")
    if kind in ("number", "url", "email", "phone_number", "checkbox"):
        return data
    if kind == "formula":
        return data.get(data.get("type"))
    if kind == "rollup":
        inner = data.get(data.get("type"))
        return inner if isinstance(inner, (int, float, str)) else None
    # relation and anything unrecognised: no plain value we can safely use.
    return None


class NotionImporter:
    """Reads a shared Notion database and produces InvestorRecords (behind SourceImporter)."""

    def __init__(self, link: str, client: NotionClient) -> None:
        self._database_id = extract_database_id(link)
        self._client = client

    @property
    def database_id(self) -> str:
        return self._database_id

    def _fetch_pages(self) -> list[dict]:
        """Query the database, following pagination until has_more is false."""
        pages: list[dict] = []
        cursor: str | None = None
        while True:
            try:
                response = self._client.query(self._database_id, cursor)
            except NotionAPIError as exc:
                if exc.code in _PERMISSION_CODES:
                    raise NotionPermissionError(self._database_id) from exc
                raise
            pages.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
            if not cursor:  # defensive: has_more but no cursor — stop rather than loop forever.
                break
        return pages

    def preview(self) -> ImportPreview:
        pages = self._fetch_pages()
        if not pages:
            return ImportPreview(
                warnings=["The database is empty, or no rows were returned."]
            )

        property_names = list(pages[0].get("properties", {}).keys())
        mapping = auto_map(property_names)
        records = [self._record(page, mapping) for page in pages]
        records = [r for r in records if r]

        preview = ImportPreview(records=records, mapping=mapping)
        if not records:
            preview.warnings.append(
                "No investors discovered — is there a title column with the firm name?"
            )
        for name in mapping.unmapped:
            preview.low_confidence.append(f"Property {name!r} wasn't mapped — kept as a note.")
        # The view's filters don't carry over: warn that every row imported (spec §4.5.1).
        preview.warnings.append(
            f"Imported all {len(pages)} rows — a Notion view's filters aren't applied by the API."
        )
        return preview

    def _record(self, page: dict, mapping) -> InvestorRecord | None:
        mapped: dict[str, object] = {}
        notes: list[str] = []
        for name, prop in page.get("properties", {}).items():
            value = property_to_value(prop)
            if value in (None, "", []):
                continue
            canonical = mapping.canonical_for(name)
            if canonical:
                mapped[canonical] = value
            else:
                notes.append(f"{name}: {value}")
        return record_from_mapped(mapped, Source.NOTION, notes=notes)


def build_notion_client(token: str | None = None) -> NotionClient:
    """Wire the real Notion SDK. Token comes from the arg or the NOTION_TOKEN env var.

    Kept out of the import path so tests never need the SDK or a token.
    """
    import os

    token = token or os.environ.get("NOTION_TOKEN")
    if not token:
        raise NotionLinkError(
            "No Notion token. Set NOTION_TOKEN (create an integration at "
            "https://www.notion.so/my-integrations) and share your database with it."
        )
    try:
        from notion_client import Client
        from notion_client.errors import APIResponseError
    except ImportError as exc:  # pragma: no cover - clear message for newcomers
        raise NotionLinkError(
            "The Notion SDK isn't installed. Run:  pip install notion-client"
        ) from exc

    sdk = Client(auth=token)

    class _HttpNotionClient:
        def query(self, database_id: str, start_cursor: str | None = None) -> dict:
            kwargs = {"database_id": database_id, "page_size": 100}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor
            try:
                return sdk.databases.query(**kwargs)
            except APIResponseError as exc:  # pragma: no cover - needs live API
                raise NotionAPIError(code=exc.code, message=str(exc)) from exc

    return _HttpNotionClient()
