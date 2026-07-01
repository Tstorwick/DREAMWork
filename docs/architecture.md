# Architecture

DreamWork is a **Python core + MCP interface** today, with a TypeScript web UI deferred.
The design goal that overrides everything else: **let 3–4 people, several new to coding,
each build a self-contained piece on their own branch, and have those pieces slot together
cleanly.** We get that by funneling everything through one shared contract (`core`) and
keeping the modules ignorant of each other.

## The layers

```
                         ┌─────────────────────────────┐
        cowork / Claude ──►      mcp_server            │   ← primary interface (v1)
                         │   (thin: tools call core)    │
        (web UI later) ──►                             │
                         └───────────────┬─────────────┘
                                         │
                 ┌───────────────────────▼───────────────────────┐
                 │                     core                        │
                 │  domain.py     entities + enums                 │
                 │  repository.py the Repository CONTRACT (Protocol)│
                 │  dossiers.py   Markdown dossier read/write       │
                 └───┬───────────────┬───────────────┬────────────┘
                     │               │               │
        ┌────────────▼───┐  ┌────────▼───────┐  ┌────▼────────────┐
        │  onboarding    │  │   dashboard    │  │ qualified_list  │
        │  (Helge)       │  │   (Jamie)      │  │ (Chris)         │
        │  list→core     │  │  snapshot,     │  │ qualification + │
        │                │  │  reminders     │  │ REAL Postgres   │
        └────────────────┘  └────────────────┘  └────┬────────────┘
                                                      │ implements
                                              ┌───────▼────────┐
                                              │  Repository     │  in-memory today,
                                              │  (Postgres impl)│  Postgres tomorrow
                                              └────────────────┘

        Internal (local, private)  │  External (shared, sanitized)
        ───────────────────────────┼──────────────────────────────
                                    │   ┌──────────────────────┐
                    core ───────────┼──►│ modules/external      │
                       (opt-in,     │   │ BookFaceClient        │
                        sanitized)  │   │  • LocalMockBookFace  │ ← now
                                    │   │  • GCloud client      │ ← later
                                    │   └──────────────────────┘
```

## The two databases (and why one is mocked)

- **Internal CRM → local Postgres.** Each founder runs their own. It's private. In v1 there
  is no multi-tenancy and no auth — it's one founder's data on one machine. Until Chris wires
  Postgres up, `core/memory_store.py` stands in so everything runs.
- **External "book face" → Extantia Google Cloud (later).** Shared across the portfolio. We
  do **not** stand up cloud infra during the hackathon. Instead, `modules/external` defines a
  `BookFaceClient` interface with a **local mock** (`LocalMockBookFace`). Everything you build
  against it — publishing sanitized facts, querying who-knows-whom — keeps working unchanged
  when we later drop in the real Google Cloud client. This is the seam that lets us defer the
  cloud decision without blocking anyone.

## Rules that keep it decoupled

1. **Modules depend on `core`, never on each other.** `dashboard` doesn't import `onboarding`.
   If two modules need to share something, it belongs in `core`.
2. **All persistence is behind `Repository`.** No module opens a database connection except
   the one that *implements* `Repository` (Chris's). Everyone else receives a `Repository`
   and calls its methods.
3. **The internal→external boundary is a one-way, opt-in, sanitizing valve.** Private data
   only reaches `external` through a deliberate sanitize step (`docs/data-model.md` §External).
4. **`mcp_server` is thin.** Tools parse inputs and call `core`/modules. Business logic lives
   in `core` and the modules, so the web UI can reuse it later without going through MCP.

## Stack

- **Language:** Python 3.11+ for core/MCP/modules. TypeScript for the web UI **later**.
- **Interface:** an MCP server (the `mcp` Python SDK / FastMCP). cowork/Claude is the v1 UI.
- **Storage:** local Postgres for internal (Chris); Markdown files for dossiers; a mocked
  client for external (→ Google Cloud later).
- **Deploy:** local for the hackathon. Google Cloud (Extantia's cloud) for the shared piece
  later — ask Moritz for GCloud specifics, Oliver/Alvar for access.
