"""dashboard (owner: Jamie) — the morning snapshot of your round.

Answers "where's my round, and who needs a reply?" Read-mostly: it queries the Repository and
summarizes. The two functions below are a working starting point — extend them, add reminders
and auto-snooze, and (later) an email digest or web view.

Depends only on `core`. See docs/module-contracts.md and docs/pipeline.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from dreamwork.core.domain import Outcome, PipelineEntry, Stage
from dreamwork.core.repository import Repository

# How long since last contact before an active entry is considered "gone cold".
STALE_AFTER = timedelta(days=14)


@dataclass
class Snapshot:
    """A summary of a round at a glance."""

    round_id: str
    total: int
    by_stage: dict[str, int]
    active_leads: int
    weighted_pipeline_usd: int  # sum of ticket estimates for active entries
    needs_follow_up: list[PipelineEntry] = field(default_factory=list)


def needs_follow_up(repo: Repository, round_id: str, today: date | None = None) -> list[PipelineEntry]:
    """Active entries that are overdue or have gone cold — and aren't snoozed past today."""
    today = today or date.today()
    out: list[PipelineEntry] = []
    for e in repo.list_pipeline(round_id):
        if e.outcome != Outcome.ACTIVE:
            continue
        if e.snooze_until and e.snooze_until > today:
            continue
        overdue = e.next_step_due is not None and e.next_step_due <= today
        cold = e.last_contact_date is not None and (today - e.last_contact_date) >= STALE_AFTER
        never_contacted = e.stage == Stage.SOURCED and e.last_contact_date is None
        if overdue or cold or never_contacted:
            out.append(e)
    return out


def round_snapshot(repo: Repository, round_id: str, today: date | None = None) -> Snapshot:
    """Counts by stage, active leads, weighted pipeline, and the follow-up list."""
    entries = repo.list_pipeline(round_id)
    by_stage: dict[str, int] = {}
    for e in entries:
        by_stage[e.stage.value] = by_stage.get(e.stage.value, 0) + 1

    active = [e for e in entries if e.outcome == Outcome.ACTIVE]
    weighted = sum(e.ticket_estimate_usd or 0 for e in active)
    active_leads = sum(1 for e in active if e.is_lead)

    return Snapshot(
        round_id=round_id,
        total=len(entries),
        by_stage=by_stage,
        active_leads=active_leads,
        weighted_pipeline_usd=weighted,
        needs_follow_up=needs_follow_up(repo, round_id, today),
    )
