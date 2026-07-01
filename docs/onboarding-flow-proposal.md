# Onboarding flow — proposal for Helge's review

> **PROPOSED — not built, not ratified.** Written by Chris after scoping `qualified_list`;
> `modules/onboarding` is entirely Helge's call per `CLAUDE.md`. This maps a concrete 6-step
> flow onto the existing domain model, flags what fits today, and calls out what needs new
> fields or a decision from Helge (and in two cases, Thomas). Treat this as a starting point
> to argue with, not a spec to implement as-is.

## The flow

1. Extantia emails all portco CEOs and asks them to opt in.
2. Opted-in CEOs share a current cap table (fund name, date of investment, amount invested,
   total round amount — all standard cap-table-export fields).
3. The tool extracts those values into the database.
4. The tool does background research to enrich each firm (sector focus, etc.) and resolves
   duplicates (e.g. "Extantia" vs. "Extantia Capital").
5. CEOs review the extracted summary, confirm it, name their closest contact at each firm
   (typed or dictated), and optionally rate each investor 1–4 stars and flag current status
   (e.g. "no longer investing," even if they invested before).
6. Tool cleans up. Founder is fully onboarded and searchable in the database.

## Step-by-step against the current model

**Step 1 (opt-in email)** isn't code, but it resolves something `docs/data-model.md` explicitly
leaves open: *"what exactly triggers a fact being shared (opt-in per fact vs. auto-sanitize) is
deferred to the onboarding owner."* This flow answers it — opt-in happens **once, at onboarding**,
not fact-by-fact later. Worth Helge stating that explicitly in `data-model.md` once he's decided,
since it un-defers a named open question.

**Step 2 (cap table minimum fields)** maps onto existing entities without new fields:
- `fund name` → `Firm.name` (resolved/deduped — see step 4).
- `date of investment` → `PipelineEntry.first_contact_date`. This is literally the "first check
  date" from the original hackathon scoping doc — good sign the model already has a home for it.
- `total amount invested` → `PipelineEntry.ticket_estimate_usd`. Slight semantic stretch: today
  that field means "estimate for the *current* round." For a cap-table import it means "actual
  historical amount." Same field, different meaning depending on whether the `Round` it's
  attached to is closed. Worth a one-line doc clarification in `data-model.md`, not a new field.
- `total round amount` → `Round.target_usd`, on a `Round` created to represent that historical
  round (label inferred from the cap table if present, e.g. "Seed", "Series A").
- Net: `import_captable(repo, round_id, rows)`, per the sketch already in
  `onboarding/__init__.py`, likely needs to create the historical `Round` itself (not just take
  a `round_id`), since a cap table spans multiple past rounds, not just the active one.

**Step 3 (extraction)** is `import_captable` itself — parse rows, `dedupe`, write `Firm` /
`PipelineEntry` (and `Round` per above).

**Step 4 (enrichment + dedupe)** is the biggest net-new piece, and it's the one that makes the
`website`, `sectors`, `geographies`, `team_members`, and `portfolio_companies` fields (Chris's PR
#1, now accepted) actually get *filled in* rather than sitting empty. Two sub-problems worth
separating:
- **Dedupe/resolution** — "Extantia" vs "Extantia Capital" needs a `resolve_firm(repo,
  candidate_name) -> Firm | None` step *before* creating a new `Firm`, or the qualified list
  fills up with duplicates that silently split a firm's history across two rows.
- **Enrichment** — filling `website`/`sectors`/`team_members`/`portfolio_companies` from
  research. Suggest defining this as its own small interface (e.g. `FirmEnricher` Protocol)
  rather than hardcoding a specific research method inside onboarding — same pattern `core`
  already uses for `Repository` and `BookFaceClient`, and it means the research method (web
  search, an LLM call, a manual lookup) can change without touching the import flow.

**Step 5 (review + contact + rating + status)** needs **two new fields not in the model today**,
and one clean mapping:
- **Closest contact → `Partner`.** This is exactly the roster-to-engaged-contact promotion
  Thomas just wrote into `data-model.md` — the CEO naming a "closest contact" during review *is*
  the moment a `Firm.team_members` string gets promoted to a real `Partner` record.
- **Rating (1–4 stars) — new field, not yet proposed.** This is a founder's private opinion, not
  a fact, so it must live on `Firm` (which is per-founder/local already) but **must never be
  added to `SHAREABLE_FIRM_FIELDS`** in `modules/external/client.py` — that allowlist is the only
  thing standing between "my private opinion of a fund" and "everyone in the portfolio sees my
  opinion of a fund." Flagging this explicitly since it's the kind of thing that's easy to add
  correctly and then accidentally leak in a later refactor.
- **"No longer investing" — new field, not yet proposed.** A `still_investing: bool | None` on
  `Firm` would let `qualified_list.matches()` exclude inactive firms automatically, which is
  qualification logic that doesn't exist yet either way.
- Dictation-vs-typing for the contact/rating step is the same "hit record and tell me who you
  know at each firm" idea already sketched in `onboarding/__init__.py` — this proposal doesn't
  add anything new there, just confirms it's still the right idea.

**Step 6 (cleanup)** is just "the above ran without errors" — no new concept.

## Summary of asks, by owner

| Ask | Owner | Notes |
|---|---|---|
| Decide the opt-in trigger is "once, at onboarding" | Helge | Un-defers a named open question in `data-model.md` |
| `resolve_firm` dedupe step | Helge | Blocks step 4; needed before any real cap-table import |
| `FirmEnricher` interface | Helge | Keeps research method swappable, matches existing `core` patterns |
| `founder_rating` field on `Firm` | Thomas (propose) | Must be excluded from `SHAREABLE_FIRM_FIELDS` — flag this in the PR |
| `still_investing` field on `Firm` | Thomas (propose) | Also useful for `qualified_list.matches()` |
| Doc clarification: `ticket_estimate_usd` means "actual" once `Round`/`PipelineEntry` is closed | Helge or Thomas | One line in `data-model.md`, no code change |
