"""The DreamWork MCP server.

Run it with `python -m dreamwork.mcp_server`. It exposes a few tools over the seeded in-memory
store so cowork/Claude can drive DreamWork end-to-end today. As Chris's Postgres Repository and
the modules land, swap `seeded_store()` for the real repository and add tools — the tool bodies
stay thin, delegating to `core` and `modules`.
"""

from __future__ import annotations

from datetime import date

from dreamwork.core.memory_store import seeded_store
from dreamwork.core.repository import Repository
from dreamwork.modules import dashboard

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - gives newcomers a clear message
    raise SystemExit(
        "The MCP SDK isn't installed. Run:  pip install -e \".[dev]\"\n"
        f"(original error: {exc})"
    )

# In v1 the internal CRM is one founder's local data. We hold a single Repository for the
# process. Today it's the seeded in-memory store; later this becomes Chris's PostgresRepository.
repo: Repository = seeded_store()

mcp = FastMCP("dreamwork")


@mcp.tool()
def list_firms() -> list[dict]:
    """List every investor firm in the CRM."""
    return [f.__dict__ for f in repo.list_firms()]


@mcp.tool()
def round_snapshot(round_id: str = "r1") -> dict:
    """A morning snapshot of a round: counts by stage, active leads, weighted pipeline, and
    who needs a follow-up today."""
    snap = dashboard.round_snapshot(repo, round_id)
    return {
        "round_id": snap.round_id,
        "total": snap.total,
        "by_stage": snap.by_stage,
        "active_leads": snap.active_leads,
        "weighted_pipeline_usd": snap.weighted_pipeline_usd,
        "needs_follow_up": [e.id for e in snap.needs_follow_up],
    }


@mcp.tool()
def log_contact(entry_id: str, note: str = "", contact_date: str | None = None) -> dict:
    """Record that you spoke with an investor: updates last_contact_date on their pipeline entry.

    `contact_date` is ISO (YYYY-MM-DD); defaults to today.
    """
    entry = repo.get_pipeline_entry(entry_id)
    if entry is None:
        return {"error": f"no pipeline entry {entry_id!r}"}
    entry.last_contact_date = date.fromisoformat(contact_date) if contact_date else date.today()
    if note:
        entry.next_step = note
    repo.update_pipeline_entry(entry)
    return {"ok": True, "entry_id": entry.id, "last_contact_date": entry.last_contact_date.isoformat()}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
