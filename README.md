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
# 1. Install (Python 3.11+)
pip install -e ".[dev]"

# 2. Run the MCP server against the in-memory store (no Postgres needed yet)
python -m dreamwork.mcp_server

# 3. Or poke the domain directly
python -c "from dreamwork.core.memory_store import seeded_store; print(seeded_store().list_firms())"
```

You don't need Postgres to start — `memory_store` makes everything work end-to-end. Chris's
module swaps in the real database behind the same `Repository` contract, and nothing else changes.

## Picking up your piece

1. Fork `main`, make a branch (`git checkout -b dashboard-jamie`).
2. Open `docs/module-contracts.md` and find your module. It tells you exactly what `core`
   gives you and what your module must expose.
3. Tell your Claude: *"Read CLAUDE.md and docs/, then help me build the `<your module>` module."*
4. Commit every hour or two, open a PR into `main` when it works.

New to any of this? See **[CLAUDE.md](CLAUDE.md)** — it's written so your Claude can lead you.
