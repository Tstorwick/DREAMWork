"""Domain entities and enums — the shape of DreamWork's data.

These are plain dataclasses on purpose: they carry no persistence logic (that lives behind
`Repository`) and no business rules (those live in the modules). They are the common vocabulary
every part of the system shares.

Field-by-field documentation lives in docs/data-model.md; the stage/outcome values in
docs/pipeline.md. Keep this file and those docs in sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Stage(str, Enum):
    """How far a conversation has progressed. See docs/pipeline.md (Axis 1)."""

    SOURCED = "sourced"
    INTRO_REQUESTED = "intro_requested"
    CONTACTED = "contacted"
    MEETING = "meeting"
    IN_CONVERSATION = "in_conversation"
    DILIGENCE = "diligence"
    COMMITTED = "committed"
    CLOSED = "closed"


class Outcome(str, Enum):
    """The live status of the relationship, independent of Stage. See docs/pipeline.md (Axis 2)."""

    ACTIVE = "active"
    SNOOZED = "snoozed"
    PASSED = "passed"          # said no this round — kept, never deleted
    NEXT_ROUND = "next_round"  # not now, strong fit for a future round


@dataclass
class Firm:
    """An investor firm (fund). This is the granularity the external book-face shares."""

    id: str
    name: str  # the one always-required "tag"
    website: str | None = None
    fund_size_usd: int | None = None
    aum_usd: int | None = None
    leads: bool | None = None
    geographies: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    follows_on: bool | None = None
    team_members: list[str] = field(default_factory=list)  # lightweight roster: "Name — Title"
    ticket_size_usd_range: tuple[int | None, int | None] | None = None  # (min, max) typical check
    portfolio_companies: list[str] = field(default_factory=list)  # freeform, firm-reported
    # Subset of portfolio_companies that are also Extantia portcos — powers "who already knows
    # this fund" cross-portfolio visibility.
    extantia_portfolio_overlap: list[str] = field(default_factory=list)
    still_investing: bool | None = None  # False = deploying paused/fund closed; qualification skips these
    # The founder's PRIVATE 1-4 star opinion of this fund. NOT a fact — must NEVER be added to
    # modules/external/client.py::SHAREABLE_FIRM_FIELDS. Stays local to this founder. (PR #3)
    founder_rating: int | None = None
    dossier_path: str | None = None  # -> data/dossiers/firm/<id>.md


@dataclass
class Partner:
    """A person at a firm. Relationships are tracked at this level, not just firm level."""

    id: str
    firm_id: str
    name: str
    role: str | None = None
    influence: str | None = None  # freeform: how much power they hold in the firm
    dossier_path: str | None = None  # -> data/dossiers/partner/<id>.md


@dataclass
class Round:
    """A fundraising round you are running. In v1 there's typically one active round."""

    id: str
    company: str
    target_usd: int | None = None
    label: str | None = None  # "Seed", "Series A", ...
    opened_at: date | None = None


@dataclass
class PipelineEntry:
    """An investor's state within a specific round — the center of gravity of the model.

    Two independent axes: `stage` (progression) and `outcome` (live status). See pipeline.md.
    """

    id: str
    round_id: str
    firm_id: str
    partner_id: str | None = None
    stage: Stage = Stage.SOURCED
    outcome: Outcome = Outcome.ACTIVE
    is_lead: bool = False
    ticket_estimate_usd: int | None = None  # estimate on an open round; actual amount on a closed one
    first_contact_date: date | None = None
    last_contact_date: date | None = None
    next_step: str | None = None
    next_step_due: date | None = None
    snooze_until: date | None = None


@dataclass
class IntroRequest:
    """Asking a mutual to introduce you — deliberately its own funnel, separate from the pipeline."""

    id: str
    round_id: str
    target_firm_id: str
    asked_of: str  # the mutual you're asking
    target_partner_id: str | None = None
    channel: str | None = None  # suggested channel: email, WhatsApp, ...
    status: str = "requested"  # requested / offered / made / declined
    requested_at: date | None = None
