# Data model

This is the heart of DreamWork. The pattern, straight from the team: **a structured row with
required "tag" fields, each linked to a Markdown dossier** that holds everything freeform.

- **Structured fields → Postgres columns.** Filterable, sortable, the stuff the dashboard and
  qualification key off.
- **Freeform → Markdown dossier.** Sentiment, "what makes them tick", call-prep notes, history.
  One file per Firm/Partner, linked by `dossier_path`. See `core/dossiers.py`.

> **OWNED BY CHRIS:** the concrete storage — Postgres column types, indexes, migrations, and
> exactly how `dossier_path` is stored/generated — is Chris's call, made behind the
> `Repository` contract. The entities and fields below are the agreed *shape*; treat field
> types as guidance, not locked DDL.

## Entities

### Firm
An investor firm (fund). The firm-level record — this is the granularity the external
book-face shares.

> **PROPOSED ADDITION (Chris, for Thomas's review):** `website`, `team_members`,
> `ticket_size_usd_range`, `portfolio_companies`, and `extantia_portfolio_overlap` below are new.
> They came out of scoping the investor database: qualification only needs a handful of
> filterable tags, but the "show a founder which other investors already know their fellow
> Extantia portco CEOs" feature needs `extantia_portfolio_overlap` specifically — it's the field
> that makes cross-portfolio visibility possible. `portfolio_companies` stays a plain string list
> (most entries won't be Extantia companies and don't need their own record); only the overlap
> subset is worth naming explicitly. Open to folding this into `dossier_path` freeform content
> instead if you'd rather keep `Firm` lean — flagging for a call, not assuming the merge.

| Field              | Type            | Notes                                              |
|--------------------|-----------------|----------------------------------------------------|
| `id`               | id              |                                                    |
| `name`             | str  (required) | The one always-required tag.                       |
| `website`          | str?            | *Proposed.*                                        |
| `fund_size_usd`    | int?            | e.g. 200_000_000. Firm-level, shareable, corroborated. |
| `aum_usd`          | int?            | Softer than cap-table facts; can be inferred.      |
| `leads`            | bool?           | Does this firm lead rounds?                        |
| `geographies`      | list[str]       | Qualification filter.                              |
| `sectors`          | list[str]       | Qualification filter.                              |
| `follows_on`       | bool?           | Tends to follow on in later rounds.                |
| `team_members`     | list[str]       | *Proposed.* Freeform "Name — Title" entries.       |
| `ticket_size_usd_range` | (int?, int?)? | *Proposed.* Typical check size, (min, max).     |
| `portfolio_companies` | list[str]    | *Proposed.* Freeform, firm-reported.                |
| `extantia_portfolio_overlap` | list[str] | *Proposed.* Subset of `portfolio_companies` that are also Extantia portfolio companies — powers cross-portfolio investor visibility. |
| `dossier_path`     | str?            | → `data/dossiers/firm/<id>.md`                     |

### Partner
A person at a firm. Relationships are tracked at *this* level — "who's my closest contact at
Toyota Climate Fund" — not just firm level.

| Field           | Type            | Notes                                        |
|-----------------|-----------------|----------------------------------------------|
| `id`            | id              |                                              |
| `firm_id`       | → Firm          |                                              |
| `name`          | str (required)  |                                              |
| `role`          | str?            | e.g. "Partner", "Principal".                 |
| `influence`     | str?            | Freeform: how much power they hold in the firm. |
| `dossier_path`  | str?            | → `data/dossiers/partner/<id>.md`            |

### Round
A fundraising round *you* are running. In v1 there's typically one active round.

| Field         | Type          | Notes                                  |
|---------------|---------------|----------------------------------------|
| `id`          | id            |                                        |
| `company`     | str           | Your company.                          |
| `target_usd`  | int?          | Raise target.                          |
| `label`       | str?          | e.g. "Seed", "Series A".               |
| `opened_at`   | date?         |                                        |

### PipelineEntry  ← the center of gravity
An investor's state **within a specific round**. This is the join table the dashboard reads.
See `docs/pipeline.md` for the `stage`/`outcome` values.

| Field                 | Type            | Notes                                              |
|-----------------------|-----------------|----------------------------------------------------|
| `id`                  | id              |                                                    |
| `round_id`            | → Round         |                                                    |
| `firm_id`             | → Firm          |                                                    |
| `partner_id`          | → Partner?      | The specific person you're talking to.             |
| `stage`               | Stage           | Progression: sourced → … → closed. See pipeline.md.|
| `outcome`             | Outcome         | Orthogonal: active / snoozed / passed / next_round.|
| `is_lead`             | bool            | Are they a potential lead for this round?          |
| `ticket_estimate_usd` | int?            | Estimated check size.                              |
| `first_contact_date`  | date?           |                                                    |
| `last_contact_date`   | date?           | Drives "how long since contact" / reminders.       |
| `next_step`           | str?            | What you owe them next.                             |
| `next_step_due`       | date?           |                                                    |
| `snooze_until`        | date?           | Dashboard hides it until this date.                |

### IntroRequest  ← its own funnel
Asking a mutual to introduce you. Deliberately separate from PipelineEntry: the *same*
investor can be reached via several intro paths, and intro asks have their own lifecycle.

| Field              | Type          | Notes                                          |
|--------------------|---------------|------------------------------------------------|
| `id`               | id            |                                                |
| `round_id`         | → Round       |                                                |
| `target_firm_id`   | → Firm        | Who you want to reach.                          |
| `target_partner_id`| → Partner?    |                                                |
| `asked_of`         | str           | The mutual you're asking (name / contact).     |
| `channel`          | str?          | Suggested channel: email, WhatsApp, etc.       |
| `status`           | str           | e.g. requested / offered / made / declined.    |
| `requested_at`     | date?         |                                                |

## Cap table = source of truth
Onboarding seeds Firms/Partners from a founder's cap table: it's the authoritative source for
**firm, check size, and first-check date** (from which we infer relationship tenure — "known 5
years vs 6 months"). See `modules/onboarding`.

## External / "book face" (deferred, mocked now)
The shared graph holds **firm-level facts only** — never your company/personal data. Each
shared fact carries:
- **value** (e.g. `fund_size_usd = 200_000_000`),
- **owner** — the founder who contributed it,
- **who holds the connection** — who actually knows this firm,
- **confidence** — grows as multiple founders corroborate the same fact.

> **DEFERRED:** what exactly triggers a fact being shared (opt-in per fact vs auto-sanitize)
> is owned by the onboarding partner and built later. The `modules/external` seam models the
> *shape* (value + owner + connection + confidence) so we can wire the trigger in without
> reshaping data. Nothing internal/private crosses this boundary except through an explicit
> sanitize step.
