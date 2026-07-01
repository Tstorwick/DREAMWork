"""Composition root — decides which Repository the app runs against.

This lives at the package root (not in `core`) on purpose: it's the one place allowed to know
about a *concrete* store, so `core` can keep depending on nothing. Entry points (the MCP server,
later the web app) call `get_repository()` and receive a `Repository` — they never know or care
whether it's in-memory or Postgres.

    no  DREAMWORK_DB_URL  ->  in-memory store (zero setup, for dev/demo/tests)
    set DREAMWORK_DB_URL  ->  PostgresRepository against that DSN (the real local CRM)

Example:
    DREAMWORK_DB_URL=postgresql://localhost/dreamwork python -m dreamwork.mcp_server
"""

from __future__ import annotations

import os

from dreamwork.core.repository import Repository

DB_URL_ENV = "DREAMWORK_DB_URL"


def get_repository(*, seed_if_memory: bool = False) -> Repository:
    """Return the configured Repository.

    `seed_if_memory` loads a little demo data when falling back to the in-memory store — handy
    for the MCP server so a fresh run shows something. Ignored when a real database is configured.
    """
    url = os.environ.get(DB_URL_ENV)
    if url:
        # Imported lazily so psycopg is only required when a database is actually configured.
        from dreamwork.modules.qualified_list.store import PostgresRepository

        return PostgresRepository(url)

    from dreamwork.core.memory_store import InMemoryRepository, seeded_store

    return seeded_store() if seed_if_memory else InMemoryRepository()
