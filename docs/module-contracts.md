# Module contracts

Each module is a self-contained, branch-ownable piece. This file is the agreement between
them: **what `core` gives you, and what your module must expose.** If you keep to these, your
branch will merge into everyone else's without surprises.

The shared rule: **modules receive a `Repository` and call it. Modules never import each
other, and never open their own DB connection** (except `qualified_list`, which *provides* the
Repository implementation).

---

## `core` (owner: Thomas) — the foundation everyone uses

Provides:
- `dreamwork.core.domain` — `Firm`, `Partner`, `Round`, `PipelineEntry`, `IntroRequest`,
  and the `Stage` / `Outcome` enums.
- `dreamwork.core.repository.Repository` — the data-access **Protocol** (the contract below).
- `dreamwork.core.memory_store.InMemoryRepository` — a working implementation so the app runs
  with zero setup. Also `seeded_store()` for demo data.
- `dreamwork.core.dossiers` — `read_dossier(path)`, `write_dossier(path, body, meta)`,
  `dossier_path_for(kind, id)`.

The `Repository` contract (see `core/repository.py` for the authoritative signatures):
```python
class Repository(Protocol):
    # Firms & Partners
    def add_firm(self, firm: Firm) -> Firm: ...
    def get_firm(self, firm_id: str) -> Firm | None: ...
    def list_firms(self) -> list[Firm]: ...
    def add_partner(self, partner: Partner) -> Partner: ...
    def list_partners(self, firm_id: str | None = None) -> list[Partner]: ...
    # Rounds
    def add_round(self, round_: Round) -> Round: ...
    def get_round(self, round_id: str) -> Round | None: ...
    # Pipeline
    def add_pipeline_entry(self, entry: PipelineEntry) -> PipelineEntry: ...
    def update_pipeline_entry(self, entry: PipelineEntry) -> PipelineEntry: ...
    def list_pipeline(self, round_id: str) -> list[PipelineEntry]: ...
    # Intro requests
    def add_intro_request(self, req: IntroRequest) -> IntroRequest: ...
    def list_intro_requests(self, round_id: str) -> list[IntroRequest]: ...
```

---

## `modules/qualified_list` (owner: Chris) — qualification + the real store

Two jobs:
1. **The real Postgres `Repository`.** Implement the `Repository` Protocol backed by local
   Postgres, plus the migrations/DDL. Everything else keeps working the moment you do — no
   other module changes. You also decide how `dossier_path` is stored/generated.
2. **Qualification logic.** Turn the investor universe into "who it makes sense to talk to
   this round": filter/score by round, ticket size, geography, sector, stage. Expose e.g.
   `qualify(repo, round_id, criteria) -> list[PipelineEntry]`.

Consumes: `Repository`, domain. Exposes: a `Repository` implementation + qualification functions.

---

## `modules/dashboard` (owner: Jamie) — the morning snapshot

Read-mostly. Answer "where's my round and who needs a reply?"
- `round_snapshot(repo, round_id) -> Snapshot` — counts by stage, weighted pipeline, leads.
- `needs_follow_up(repo, round_id, today) -> list[PipelineEntry]` — active, overdue, not snoozed.
- reminders / auto-snooze helpers.

A starter `round_snapshot` + `needs_follow_up` already exist in `modules/dashboard/__init__.py`
so you have something running to build on. Consumes: `Repository`, domain, `pipeline.md`.

---

## `modules/onboarding` (owner: Helge) — get data in, painlessly

Take a founder's investor list / **cap table** and create `Firm` / `Partner` / `PipelineEntry`
rows in `core`. The design bar is **friendliness** — people must actually do it (drag-and-drop
a CSV, or the "hit record and tell me who you know at each firm" voice idea from the meeting).
- `import_captable(repo, round_id, rows) -> ImportResult`.

Consumes: `Repository`, domain. Exposes: import functions. Never talks to `external` directly.

---

## `modules/external` (owner: TBD, built later) — the book-face seam

The sanitized, portfolio-only shared graph. **Mocked locally now, Google Cloud later.**
- `BookFaceClient` — Protocol for the shared store (publish a fact, query firms/connections).
- `LocalMockBookFace` — in-process implementation for the hackathon.
- `sanitize(firm) -> list[SharedFact]` — strips everything but firm-level facts, attaches
  owner + who-holds-the-connection.

> The **trigger** for publishing is decided: **opt-in once, at onboarding** (2026-07-01).
> Onboarding wires a founder's opt-in to `sanitize` + `publish`; build the shape here.

Consumes: `core` domain (read-only). Exposes: `BookFaceClient`, `sanitize`. The internal→external
boundary lives entirely here — no other module writes to the shared store.
