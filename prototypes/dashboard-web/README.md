# Dashboard web prototype

A static HTML/CSS/JS mockup of a possible **web view** for the `dashboard` module (see the
"(later) an email digest or web view" note in `dreamwork/modules/dashboard/__init__.py`).

**This is a visual reference only.** It runs entirely on hardcoded mock data in `js/data.js`
and does not talk to `Repository`, `core.domain`, or the MCP server.

Its data model, however, **mirrors the real domain** (`dreamwork/core/domain.py`): `js/data.js`
defines normalized `firms`, `partners`, and `pipeline` (`PipelineEntry`) entities and exposes
`investors` as an explicit `PipelineEntry ⋈ Firm ⋈ Partner` join — exactly what the real
dashboard reads. Investor state uses the two canonical axes:

- **`stage`** (progression): `sourced → intro_requested → contacted → meeting → in_conversation
  → diligence → committed → closed`
- **`outcome`** (live status, independent of stage): `active · snoozed · passed · next_round`

plus `is_lead`, `ticket_estimate_usd`, `first/last_contact_date`, `next_step`, and `snooze_until`
— see `docs/pipeline.md`. `direction`, `peerIds`, and `introducedBy` are prototype-only display
extras, not core fields. When this gets wired to a backend, swap `js/data.js` for calls into the
MCP server / `Repository`; the entity shapes already line up.

## Run it

```bash
python3 -m http.server 5173 --directory prototypes/dashboard-web
```

Then open `http://localhost:5173`.

## Views

Overview, Investors, Connections (inbound/outbound), Pipeline (kanban), Shared Network
(cross-founder investor overlap — a rough stand-in for `extantia_portfolio_overlap`), and
Activity.

## Turning this into the real thing

To wire this to the actual module, the data layer (`js/data.js`) would need to be replaced
with calls into a real backend (e.g. the MCP server or a small API in front of `Repository`),
and the schema aligned to `Firm` / `Partner` / `Round` / `PipelineEntry` / `IntroRequest` from
`docs/data-model.md`.
