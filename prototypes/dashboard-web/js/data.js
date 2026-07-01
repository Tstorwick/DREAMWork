// Loads the DreamWork dashboard's data from the live API (see api.js) into a global DW_DATA.
//
// DW_DATA mirrors the REAL domain model in dreamwork/core/domain.py, materialized as the JOIN
// the views read: PipelineEntry ⋈ Firm ⋈ Partner. The API supplies the canonical fields; this
// file decorates each row with a few PROTOTYPE-ONLY display extras the views expect but the core
// model doesn't carry (initials, color, direction, introducedBy, peerIds, notes, stageFocus).
//
// Shape: { round, founder, peers, firms, partners, pipeline, investors, activity }.
// The core model has no peers list or activity feed, so those stay empty — the peers/activity
// views fall back to their existing empty states, which is the honest thing to show.

// Global (not const) so every other script sees the same object after loadData() runs.
let DW_DATA = {
  round: null, founder: null, peers: [], firms: [], partners: [],
  pipeline: [], investors: [], activity: [],
};

// First letters of the first two words, uppercased. "Grace Whitfield" -> "GW".
function initialsFor(name) {
  return String(name || "")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] || "")
    .join("")
    .toUpperCase();
}

// Deterministic avatar color: hash the id string, index into a fixed palette.
function colorFor(id) {
  const palette = ["#6ee7b7", "#93c5fd", "#fca5a5", "#fcd34d", "#a5b4fc", "#67e8f9", "#f9a8d4", "#c4b5fd", "#fdba74"];
  const s = String(id || "");
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) | 0;
  }
  return palette[Math.abs(hash) % palette.length];
}

async function loadData() {
  const rounds = await apiGet("/rounds");
  if (!rounds || !rounds.length) return; // no data yet — leave DW_DATA mostly empty.

  const round = rounds[0];

  const [investors, firms, intros] = await Promise.all([
    apiGet("/rounds/" + round.id + "/investors"),
    apiGet("/firms"),
    apiGet("/rounds/" + round.id + "/intros"),
  ]);

  // Decorate each investor row IN PLACE with prototype-only display fields the API doesn't supply.
  investors.forEach((inv) => {
    inv.initials = initialsFor(inv.name);
    inv.color = colorFor(inv.id);
    inv.direction = null;
    inv.introducedBy = null;
    inv.peerIds = [];
    inv.notes = inv.nextStep || "";
    inv.stageFocus = [round.label];
    // inv.type is left as whatever the API sent (may be null).
  });

  // "Total raised" = sum of estimated tickets for investors already closed.
  const raisedSoFar = investors
    .filter((inv) => inv.stage === "closed")
    .reduce((sum, inv) => sum + (inv.ticketEstimateUsd || 0), 0);

  const founder = {
    name: "You", company: round.company, role: "Founder & CEO",
    initials: "YOU".slice(0, 2), round: round.label,
    targetRaise: round.target_usd, raisedSoFar,
  };

  // Populate DW_DATA IN PLACE so references captured by other scripts stay valid.
  Object.assign(DW_DATA, {
    round, founder, investors, firms, intros,
    peers: [], activity: [],
  });
}
