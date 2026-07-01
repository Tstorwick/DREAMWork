"""onboarding (owner: Helge) — get a founder's investor data in, painlessly.

Take an investor list or a **cap table** and create Firm / Partner / PipelineEntry rows in
`core`. The cap table is the source of truth for firm, check size, and first-check date (which
gives relationship tenure). The design bar is *friendliness* — people must actually do it:
drag-and-drop a CSV, or the meeting's favorite idea, "hit record and tell me who you know at
each firm" (voice -> transcription -> extraction).

Depends only on `core`; never talks to `modules/external` directly. See docs/module-contracts.md.

Nothing here is built yet. A starting shape:

    from dataclasses import dataclass
    from dreamwork.core.repository import Repository

    @dataclass
    class ImportResult:
        firms_created: int
        partners_created: int
        entries_created: int
        warnings: list[str]

    def import_captable(repo: Repository, round_id: str, rows: list[dict]) -> ImportResult:
        ...  # map each row to Firm/Partner/PipelineEntry, dedupe, return a summary

Ask your Claude: "Read CLAUDE.md and docs/, then help me build import_captable, starting from a
simple CSV of firm,partner,check_size,date."

See `docs/onboarding-flow-proposal.md` for Chris's proposed end-to-end flow (opt-in email → cap
table → extraction → enrichment/dedupe → CEO review+rating → done) mapped against the current
domain model. It's a starting point to react to, not a spec — flags two new Firm fields that'd
need Thomas's sign-off (a private rating, an is-still-investing flag) and a couple of open
decisions that are yours to make (the opt-in trigger, firm dedupe).
"""
