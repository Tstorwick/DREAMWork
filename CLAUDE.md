# CLAUDE.md — context for Claude working in DreamWork

You are helping build **DreamWork**, a fundraising CRM for founders in the **Extantia**
venture portfolio. Many of the people you'll work with are **new to coding and to Claude
Code** — part of your job is to *lead*: explain what you're doing, keep changes small, and
never assume the person already knows Git, Python, or Postgres. When in doubt, teach.

## What DreamWork is (the one-paragraph version)

A founder running a fundraise needs to know, each morning, *what to do next*: who to follow
up with, who's gone cold, who to ask for an intro. DreamWork is the CRM that tracks that.
Separately, because all these founders are in the same portfolio, DreamWork lets them share
**sanitized, firm-level facts** with each other ("this fund is ~$200M and tends to lead")
so the whole portfolio fundraises smarter. The product's real value is **trusted
information** from a **closed** group — keep that boundary sacred.

Read these next, in order:
- `docs/architecture.md` — how the pieces fit and the rules that keep them decoupled.
- `docs/data-model.md` — the entities and fields. This is the heart of the project.
- `docs/pipeline.md` — the canonical stages/outcomes a conversation moves through.
- `docs/module-contracts.md` — the exact interface your module implements or consumes.

## Architecture in five rules

1. **Everything goes through `core`.** Modules (`onboarding`, `dashboard`, etc.) call
   `core`'s `Repository` and domain objects. Modules must **never** import each other. This
   is what lets each person work on their own branch without collisions.
2. **`Repository` is a contract, not a database.** It's a Python `Protocol` in
   `core/repository.py`. `memory_store.py` implements it in memory so the app runs *today*.
   Chris's `qualified_list` module will provide the real **Postgres** implementation behind
   the same contract. Write code against the `Repository` type, never against a specific store.
3. **Structured facts live in Postgres; freeform notes live in Markdown.** Each `Firm`/`Partner`
   row has a `dossier_path` pointing at a Markdown file in `data/dossiers/`. Required "tag"
   fields go in columns; everything else (sentiment, "what makes them tick", call prep) goes
   in the dossier. `core/dossiers.py` is the only thing that reads/writes those files.
4. **Internal is local and private. External is shared, sanitized, and mocked for now.**
   The internal CRM is *this* founder's data on *this* machine. The external "book face" is
   reached only through `modules/external` (a `BookFaceClient`), which today is a **local
   mock** and later points at Extantia's Google Cloud. Data crosses that boundary only after
   an explicit sanitize + attribute step. Never write internal/private data straight to it.
5. **The human stays in the loop for anything outbound.** DreamWork drafts and suggests
   (emails, intro asks, schedules); it does not send. Don't build "auto-send."

## Working norms

- **Small, verifiable steps.** Change one thing, run it, show it working, then continue.
- **Run it, don't just write it.** `python -m dreamwork.mcp_server` and the snippets in
  `README.md` work with zero setup (in-memory store). Use them to check your work.
- **Match the surrounding code.** Same style, same naming, same comment density.
- **Git for newcomers:** you (Claude) run the Git commands; explain each in one line. Branch
  off `main`, commit every hour or two with a clear message, open a PR when it works.
- **Don't invent scope.** Some decisions are deliberately deferred to a specific owner (see
  the "OWNED BY / DEFERRED" notes in the docs). If a task needs one of those, flag it rather
  than guessing.

## Who owns what

| Module              | Owner  | What it does                                              |
|---------------------|--------|----------------------------------------------------------|
| `core`              | Thomas | Domain model, repository contract, dossiers, the scaffold |
| `modules/qualified_list` | Chris  | Qualification rules **and the real Postgres store**  |
| `modules/dashboard` | Jamie  | Round snapshot, who-needs-a-reply, reminders, auto-snooze |
| `modules/onboarding`| Helge  | Import an investor list / cap table into `core`          |
| `modules/external`  | (TBD)  | Book-face sanitize + attribute + confidence; built later |
