"""PostgresRepository — the real local store behind the `Repository` contract (Chris's "job 1").

Implements `dreamwork.core.repository.Repository` against Postgres using psycopg 3 and plain SQL
(no ORM — so you can read exactly what runs). Because it satisfies the same Protocol as
`InMemoryRepository`, swapping to it changes nothing else in the codebase; the app picks it up
via `dreamwork.config.get_repository()` when `DREAMWORK_DB_URL` is set.

Schema lives in `schema.sql` and is applied idempotently on connect. Field mapping (arrays for
list fields, two columns for the ticket range, enums as TEXT) is documented in docs/data-model.md.

Needs the optional dependency:  pip install -e ".[postgres]"
"""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

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

_SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")

# Column orders, kept next to the mapping functions so they can't drift apart.
_FIRM_COLS = (
    "id", "name", "website", "fund_size_usd", "aum_usd", "leads", "geographies", "sectors",
    "follows_on", "team_members", "ticket_min_usd", "ticket_max_usd", "portfolio_companies",
    "extantia_portfolio_overlap", "still_investing", "founder_rating", "dossier_path",
)
_PARTNER_COLS = ("id", "firm_id", "name", "role", "influence", "dossier_path")
_ROUND_COLS = ("id", "company", "target_usd", "label", "opened_at")
_ENTRY_COLS = (
    "id", "round_id", "firm_id", "partner_id", "stage", "outcome", "is_lead",
    "ticket_estimate_usd", "first_contact_date", "last_contact_date", "next_step",
    "next_step_due", "snooze_until",
)
_INTRO_COLS = (
    "id", "round_id", "target_firm_id", "target_partner_id", "asked_of", "channel",
    "status", "requested_at",
)
_INTERACTION_COLS = ("id", "round_id", "entry_id", "kind", "text", "occurred_at")


def _upsert_sql(table: str, cols: tuple[str, ...]) -> str:
    """INSERT ... ON CONFLICT (id) DO UPDATE — matches the in-memory store's overwrite-by-id add."""
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
    return f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) " \
           f"ON CONFLICT (id) DO UPDATE SET {updates}"


class PostgresRepository:
    """A `Repository` backed by Postgres. One connection, autocommit — fine for one local founder."""

    def __init__(self, dsn: str) -> None:
        self.conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        self.conn.execute(_SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # --- Firms ------------------------------------------------------------
    def add_firm(self, firm: Firm) -> Firm:
        tmin, tmax = firm.ticket_size_usd_range or (None, None)
        self.conn.execute(_upsert_sql("firm", _FIRM_COLS), (
            firm.id, firm.name, firm.website, firm.fund_size_usd, firm.aum_usd, firm.leads,
            firm.geographies, firm.sectors, firm.follows_on, firm.team_members, tmin, tmax,
            firm.portfolio_companies, firm.extantia_portfolio_overlap, firm.still_investing,
            firm.founder_rating, firm.dossier_path,
        ))
        return firm

    def get_firm(self, firm_id: str) -> Firm | None:
        row = self.conn.execute("SELECT * FROM firm WHERE id = %s", (firm_id,)).fetchone()
        return _firm_from_row(row) if row else None

    def list_firms(self) -> list[Firm]:
        rows = self.conn.execute("SELECT * FROM firm ORDER BY id").fetchall()
        return [_firm_from_row(r) for r in rows]

    # --- Partners ---------------------------------------------------------
    def add_partner(self, partner: Partner) -> Partner:
        self.conn.execute(_upsert_sql("partner", _PARTNER_COLS), (
            partner.id, partner.firm_id, partner.name, partner.role, partner.influence,
            partner.dossier_path,
        ))
        return partner

    def get_partner(self, partner_id: str) -> Partner | None:
        row = self.conn.execute("SELECT * FROM partner WHERE id = %s", (partner_id,)).fetchone()
        return _partner_from_row(row) if row else None

    def list_partners(self, firm_id: str | None = None) -> list[Partner]:
        if firm_id is None:
            rows = self.conn.execute("SELECT * FROM partner ORDER BY id").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM partner WHERE firm_id = %s ORDER BY id", (firm_id,)
            ).fetchall()
        return [_partner_from_row(r) for r in rows]

    # --- Rounds -----------------------------------------------------------
    def add_round(self, round_: Round) -> Round:
        self.conn.execute(_upsert_sql("round", _ROUND_COLS), (
            round_.id, round_.company, round_.target_usd, round_.label, round_.opened_at,
        ))
        return round_

    def get_round(self, round_id: str) -> Round | None:
        row = self.conn.execute("SELECT * FROM round WHERE id = %s", (round_id,)).fetchone()
        return _round_from_row(row) if row else None

    def list_rounds(self) -> list[Round]:
        rows = self.conn.execute("SELECT * FROM round ORDER BY id").fetchall()
        return [_round_from_row(r) for r in rows]

    # --- Pipeline ---------------------------------------------------------
    def add_pipeline_entry(self, entry: PipelineEntry) -> PipelineEntry:
        self.conn.execute(_upsert_sql("pipeline_entry", _ENTRY_COLS), _entry_params(entry))
        return entry

    def update_pipeline_entry(self, entry: PipelineEntry) -> PipelineEntry:
        cols = [c for c in _ENTRY_COLS if c != "id"]
        assignments = ", ".join(f"{c} = %s" for c in cols)
        params = _entry_params(entry)[1:] + (entry.id,)  # drop id from SET, use it in WHERE
        cur = self.conn.execute(
            f"UPDATE pipeline_entry SET {assignments} WHERE id = %s", params
        )
        if cur.rowcount == 0:
            raise KeyError(f"no pipeline entry {entry.id!r}")
        return entry

    def get_pipeline_entry(self, entry_id: str) -> PipelineEntry | None:
        row = self.conn.execute(
            "SELECT * FROM pipeline_entry WHERE id = %s", (entry_id,)
        ).fetchone()
        return _entry_from_row(row) if row else None

    def list_pipeline(self, round_id: str) -> list[PipelineEntry]:
        rows = self.conn.execute(
            "SELECT * FROM pipeline_entry WHERE round_id = %s ORDER BY id", (round_id,)
        ).fetchall()
        return [_entry_from_row(r) for r in rows]

    # --- Intro requests ---------------------------------------------------
    def add_intro_request(self, req: IntroRequest) -> IntroRequest:
        self.conn.execute(_upsert_sql("intro_request", _INTRO_COLS), (
            req.id, req.round_id, req.target_firm_id, req.target_partner_id, req.asked_of,
            req.channel, req.status, req.requested_at,
        ))
        return req

    def list_intro_requests(self, round_id: str) -> list[IntroRequest]:
        rows = self.conn.execute(
            "SELECT * FROM intro_request WHERE round_id = %s ORDER BY id", (round_id,)
        ).fetchall()
        return [_intro_from_row(r) for r in rows]

    # --- Interactions -----------------------------------------------------
    def add_interaction(self, interaction: Interaction) -> Interaction:
        self.conn.execute(_upsert_sql("interaction", _INTERACTION_COLS), (
            interaction.id, interaction.round_id, interaction.entry_id, interaction.kind,
            interaction.text, interaction.occurred_at,
        ))
        return interaction

    def list_interactions(self, round_id: str) -> list[Interaction]:
        rows = self.conn.execute(
            "SELECT * FROM interaction WHERE round_id = %s ORDER BY id", (round_id,)
        ).fetchall()
        return [_interaction_from_row(r) for r in rows]

    # --- Test support -----------------------------------------------------
    def _truncate_all(self) -> None:
        """Wipe every table — used by the contract tests to start from a clean slate."""
        self.conn.execute(
            "TRUNCATE interaction, intro_request, pipeline_entry, partner, round, firm "
            "RESTART IDENTITY CASCADE"
        )


# --- row <-> dataclass mapping ------------------------------------------------

def _firm_from_row(r: dict) -> Firm:
    rng = None
    if r["ticket_min_usd"] is not None or r["ticket_max_usd"] is not None:
        rng = (r["ticket_min_usd"], r["ticket_max_usd"])
    return Firm(
        id=r["id"], name=r["name"], website=r["website"], fund_size_usd=r["fund_size_usd"],
        aum_usd=r["aum_usd"], leads=r["leads"], geographies=list(r["geographies"]),
        sectors=list(r["sectors"]), follows_on=r["follows_on"],
        team_members=list(r["team_members"]), ticket_size_usd_range=rng,
        portfolio_companies=list(r["portfolio_companies"]),
        extantia_portfolio_overlap=list(r["extantia_portfolio_overlap"]),
        still_investing=r["still_investing"], founder_rating=r["founder_rating"],
        dossier_path=r["dossier_path"],
    )


def _partner_from_row(r: dict) -> Partner:
    return Partner(id=r["id"], firm_id=r["firm_id"], name=r["name"], role=r["role"],
                   influence=r["influence"], dossier_path=r["dossier_path"])


def _round_from_row(r: dict) -> Round:
    return Round(id=r["id"], company=r["company"], target_usd=r["target_usd"],
                 label=r["label"], opened_at=r["opened_at"])


def _entry_params(e: PipelineEntry) -> tuple:
    return (
        e.id, e.round_id, e.firm_id, e.partner_id, e.stage.value, e.outcome.value, e.is_lead,
        e.ticket_estimate_usd, e.first_contact_date, e.last_contact_date, e.next_step,
        e.next_step_due, e.snooze_until,
    )


def _entry_from_row(r: dict) -> PipelineEntry:
    return PipelineEntry(
        id=r["id"], round_id=r["round_id"], firm_id=r["firm_id"], partner_id=r["partner_id"],
        stage=Stage(r["stage"]), outcome=Outcome(r["outcome"]), is_lead=r["is_lead"],
        ticket_estimate_usd=r["ticket_estimate_usd"], first_contact_date=r["first_contact_date"],
        last_contact_date=r["last_contact_date"], next_step=r["next_step"],
        next_step_due=r["next_step_due"], snooze_until=r["snooze_until"],
    )


def _intro_from_row(r: dict) -> IntroRequest:
    return IntroRequest(
        id=r["id"], round_id=r["round_id"], target_firm_id=r["target_firm_id"],
        target_partner_id=r["target_partner_id"], asked_of=r["asked_of"], channel=r["channel"],
        status=r["status"], requested_at=r["requested_at"],
    )


def _interaction_from_row(r: dict) -> Interaction:
    return Interaction(
        id=r["id"], round_id=r["round_id"], entry_id=r["entry_id"], kind=r["kind"],
        text=r["text"], occurred_at=r["occurred_at"],
    )
