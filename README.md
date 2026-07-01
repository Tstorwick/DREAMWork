# DreamWork

> Teamwork makes the dream work.

DreamWork is a lightweight fundraising CRM for Extantia portfolio founders — and a way
for the portfolio to leverage each other's investor relationships.

It has two halves:

- **Internal (the real product):** your private "raise builder." A CRM that holds every
  investor you're talking to, a dossier on each, where the conversation stands, what the
  next step is, and how long it's been since you last spoke. This runs **locally** against
  your own Postgres database. Nobody else sees it.
- **External ("book face"):** a *sanitized, opt-in, attributed* projection of firm-level
  facts (fund size, typical ticket, does-it-lead) from your internal CRM into a shared,
  **portfolio-only** graph, so founders can corroborate facts and make warm intros to each
  other. This will live on Extantia's Google Cloud. **For now it's mocked locally** behind
  an adapter — nothing you build against it changes when we move it to the cloud.

The edge is the **information**: Extantia curates its portfolio, so the sources are trusted.
The goal is *daily process guidance* — "what should I do next in my raise" — not a fully
autonomous agent. You stay in the loop for anything that gets sent.

## The shape of the code

```
dreamwork/
  core/              # THE shared foundation. Everything talks to core, never to each other.
    domain.py        #   Entities: Firm, Partner, Round, PipelineEntry, IntroRequest (+ enums)
    repository.py    #   The data-access CONTRACT (a Protocol). Storage plugs in behind this.
    memory_store.py  #   An in-memory implementation so the whole thing RUNS TODAY, no DB needed.
    dossiers.py      #   Reads/writes the Markdown dossier linked to each row.
  mcp_server/        # The MCP server — the primary interface. cowork/Claude drives DreamWork through this.
  modules/           # One self-contained, branch-ownable piece per teammate:
    onboarding/      #   Import a founder's investor list / cap table into core.        (owner: Helge)
    qualified_list/  #   Qualification rules + the real Postgres store.                 (owner: Chris)
    dashboard/       #   Round snapshot, follow-up reminders, auto-snooze.              (owner: Jamie)
    external/        #   The book-face adapter: sanitize + attribute + confidence.      (built later)
docs/                # Read these. They're how your Claude learns what's going on.
data/dossiers/       # The Markdown dossier files, git-tracked.
```

## Quickstart

```bash
# 1. Install (Python 3.11+) into a project venv
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# 2. Run the MCP server against the in-memory store (no Postgres needed yet)
python -m dreamwork.mcp_server

# 3. Or poke the domain directly
python -c "from dreamwork.core.memory_store import seeded_store; print(seeded_store().list_firms())"
```

You don't need Postgres to start — `memory_store` makes everything work end-to-end.

### Running against the real Postgres store

The real store (`modules/qualified_list/store.py`) is available behind the same `Repository`
contract — set `DREAMWORK_DB_URL` and it's used automatically; unset, you get the in-memory store.

```bash
# 1. Install the optional driver
.venv/bin/pip install -e ".[postgres]"

# 2. Bring up a local Postgres (Docker)
docker run --rm -d --name dreamwork-pg -e POSTGRES_PASSWORD=x -p 5432:5432 postgres:16

# 3. Point DreamWork at it — the schema is created automatically on first connect
export DREAMWORK_DB_URL=postgresql://postgres:x@localhost:5432/postgres
python -m dreamwork.mcp_server
```

`tests/test_repository_contract.py` runs the same assertions against both stores; point
`DREAMWORK_TEST_DB_URL` at a throwaway database to include Postgres in the run.

## Onboarding: get your investor list in (owner: Helge)

The onboarding module imports a founder's investor list / cap table into `core`, deduping and
merging so re-importing never creates duplicates. Every imported value carries where it came from
(a source chip) and a confidence; a value you confirm by hand always outranks an inferred one.

```python
from dreamwork.core.memory_store import seeded_store
from dreamwork.modules import onboarding

repo = seeded_store()

# 1. Paste anything: CSV, a tab/pipe-separated table, or a Markdown table.
onboarding.import_tabular(repo, "r1", """
Firm, Lead Partner, Check Size, Status, Focus
Sequoia, Roelof Botha, $2M, in conversation, climate; mobility
Accel, Rich Wong, 1.5M, met, saas
""")

# 2. Or a cap table as dict rows (the module contract).
onboarding.import_captable(repo, "r1", [{"Firm": "Benchmark", "Partner": "Sarah", "Check": "$1.5M"}])
```

Columns are auto-mapped (`Firm`→firm, `Check Size`→ticket, `Status`→stage, `Focus`→sectors); call
`onboarding.preview_tabular(text)` first to see the mapping before writing anything.

### Import a Notion database

A pasted Notion link (`app.notion.com/p/<id>?v=<view>`) is a **private** database. Two steps are
required — the link alone can't be read:

1. **Create an integration** at <https://www.notion.so/my-integrations>, copy its token, and set
   it in your environment: `export NOTION_TOKEN=secret_xxx` (never commit it — `.env` is gitignored).
2. **Share the database with the integration:** in Notion, open the page → `•••` menu →
   *Connections* → *Connect to* → your integration. Notion only exposes pages you explicitly share.

```bash
pip install -e ".[notion]"    # installs the Notion SDK
```

```python
from dreamwork.modules import onboarding
from dreamwork.modules.onboarding.sources.notion import build_notion_client

client = build_notion_client()          # reads NOTION_TOKEN
onboarding.import_notion(repo, "r1", "https://app.notion.com/p/<id>?v=<view>", client)
```

Notes: the API reads the **database**, not the view — a view's filters/sorts don't apply, so every
row imports. If you haven't shared the page, you get a clear "share this page with DreamWork" message
with a deep link instead of an error.

### Through the MCP server / Claude

The same imports are exposed as MCP tools (`preview_import`, `import_investors`,
`import_notion_database`), so you can drive onboarding by talking to Claude once the server is running.

## Picking up your piece

1. Fork `main`, make a branch (`git checkout -b dashboard-jamie`).
2. Open `docs/module-contracts.md` and find your module. It tells you exactly what `core`
   gives you and what your module must expose.
3. Tell your Claude: *"Read CLAUDE.md and docs/, then help me build the `<your module>` module."*
4. Commit every hour or two, open a PR into `main` when it works.

New to any of this? See **[CLAUDE.md](CLAUDE.md)** — it's written so your Claude can lead you.
