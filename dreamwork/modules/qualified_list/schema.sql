-- DreamWork Postgres schema. Mirrors dreamwork/core/domain.py.
-- Applied idempotently by PostgresRepository on startup (CREATE ... IF NOT EXISTS), so it's safe
-- to run every time. Schema-mapping choices are documented in docs/data-model.md.

CREATE TABLE IF NOT EXISTS firm (
    id                          TEXT PRIMARY KEY,
    name                        TEXT NOT NULL,
    website                     TEXT,
    fund_size_usd               BIGINT,               -- BIGINT: funds exceed int4's ~2.1B max
    aum_usd                     BIGINT,
    leads                       BOOLEAN,
    geographies                 TEXT[] NOT NULL DEFAULT '{}',
    sectors                     TEXT[] NOT NULL DEFAULT '{}',
    follows_on                  BOOLEAN,
    team_members                TEXT[] NOT NULL DEFAULT '{}',
    ticket_min_usd              BIGINT,               -- ticket_size_usd_range split into two cols
    ticket_max_usd              BIGINT,
    portfolio_companies         TEXT[] NOT NULL DEFAULT '{}',
    extantia_portfolio_overlap  TEXT[] NOT NULL DEFAULT '{}',
    still_investing             BOOLEAN,
    founder_rating              INTEGER,              -- PRIVATE: never leaves the local CRM
    dossier_path                TEXT
);

CREATE TABLE IF NOT EXISTS partner (
    id           TEXT PRIMARY KEY,
    firm_id      TEXT NOT NULL REFERENCES firm(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    role         TEXT,
    influence    TEXT,
    dossier_path TEXT
);
CREATE INDEX IF NOT EXISTS partner_firm_id_idx ON partner (firm_id);

CREATE TABLE IF NOT EXISTS round (
    id         TEXT PRIMARY KEY,
    company    TEXT NOT NULL,
    target_usd BIGINT,
    label      TEXT,
    opened_at  DATE
);

CREATE TABLE IF NOT EXISTS pipeline_entry (
    id                  TEXT PRIMARY KEY,
    round_id            TEXT NOT NULL REFERENCES round(id) ON DELETE CASCADE,
    firm_id             TEXT NOT NULL REFERENCES firm(id) ON DELETE CASCADE,
    partner_id          TEXT REFERENCES partner(id) ON DELETE SET NULL,
    stage               TEXT NOT NULL CHECK (stage IN
                          ('sourced','intro_requested','contacted','meeting',
                           'in_conversation','diligence','committed','closed')),
    outcome             TEXT NOT NULL CHECK (outcome IN ('active','snoozed','passed','next_round')),
    is_lead             BOOLEAN NOT NULL DEFAULT FALSE,
    ticket_estimate_usd BIGINT,
    first_contact_date  DATE,
    last_contact_date   DATE,
    next_step           TEXT,
    next_step_due       DATE,
    snooze_until        DATE
);
CREATE INDEX IF NOT EXISTS pipeline_round_id_idx ON pipeline_entry (round_id);
CREATE INDEX IF NOT EXISTS pipeline_firm_id_idx ON pipeline_entry (firm_id);

CREATE TABLE IF NOT EXISTS intro_request (
    id                TEXT PRIMARY KEY,
    round_id          TEXT NOT NULL REFERENCES round(id) ON DELETE CASCADE,
    target_firm_id    TEXT NOT NULL REFERENCES firm(id) ON DELETE CASCADE,
    target_partner_id TEXT REFERENCES partner(id) ON DELETE SET NULL,
    asked_of          TEXT NOT NULL,
    channel           TEXT,
    status            TEXT NOT NULL DEFAULT 'requested',
    requested_at      DATE
);
CREATE INDEX IF NOT EXISTS intro_round_id_idx ON intro_request (round_id);

CREATE TABLE IF NOT EXISTS interaction (
    id          TEXT PRIMARY KEY,
    round_id    TEXT NOT NULL REFERENCES round(id) ON DELETE CASCADE,
    entry_id    TEXT NOT NULL REFERENCES pipeline_entry(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    text        TEXT NOT NULL,
    occurred_at DATE
);
CREATE INDEX IF NOT EXISTS interaction_round_id_idx ON interaction (round_id);
