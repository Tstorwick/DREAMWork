# Dashboard web prototype

A static HTML/CSS/JS mockup of a possible **web view** for the `dashboard` module (see the
"(later) an email digest or web view" note in `dreamwork/modules/dashboard/__init__.py`).

**This is a visual reference only.** It runs entirely on hardcoded mock data in `js/data.js`
and does not talk to `Repository`, `core.domain`, or the MCP server. Its data shape (a flat
"Investor" with `direction`/`warmth`/`peerIds`) is a rough analog for `Firm` + `Partner` +
`PipelineEntry`, not a match — treat it as a starting point for layout/UX, not a spec.

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
