// Shared helpers used across views.

// Canonical progression stages (dreamwork/core/domain.py :: Stage) with display labels + badge colors.
const STAGE_ORDER = [
  "sourced", "intro_requested", "contacted", "meeting",
  "in_conversation", "diligence", "committed", "closed",
];

const STAGE_LABELS = {
  sourced: "Sourced", intro_requested: "Intro Requested", contacted: "Contacted",
  meeting: "Meeting", in_conversation: "In Conversation", diligence: "Diligence",
  committed: "Committed", closed: "Closed",
};

const STAGE_BADGE = {
  sourced: "badge-grey", intro_requested: "badge-grey", contacted: "badge-grey",
  meeting: "badge-blue", in_conversation: "badge-blue", diligence: "badge-amber",
  committed: "badge-purple", closed: "badge-green",
};

// Orthogonal outcome axis (dreamwork/core/domain.py :: Outcome). Independent of stage.
const OUTCOME_ORDER = ["active", "snoozed", "passed", "next_round"];
const OUTCOME_LABELS = { active: "Active", snoozed: "Snoozed", passed: "Passed", next_round: "Next Round" };
const OUTCOME_BADGE = { active: "badge-green", snoozed: "badge-grey", passed: "badge-red", next_round: "badge-blue" };

const DIRECTION_BADGE = { inbound: "badge-blue", outbound: "badge-amber" };

function stageRank(stage) {
  const r = STAGE_ORDER.indexOf(stage);
  return r === -1 ? 0 : r;
}

function fmtMoney(n) {
  if (n === null || n === undefined) return "—";
  if (Math.abs(n) >= 1000000) return "$" + (n / 1000000).toFixed(n % 1000000 === 0 ? 0 : 1) + "M";
  if (Math.abs(n) >= 1000) return "$" + Math.round(n / 1000) + "K";
  return "$" + n;
}

function fmtMoneyFull(n) {
  if (n === null || n === undefined) return "—";
  return "$" + n.toLocaleString("en-US");
}

function fmtDate(d) {
  const date = new Date(d + "T00:00:00");
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function daysAgo(d) {
  const today = new Date("2026-07-01T00:00:00");
  const date = new Date(d + "T00:00:00");
  const diff = Math.round((today - date) / (1000 * 60 * 60 * 24));
  if (diff <= 0) return "today";
  if (diff === 1) return "1 day ago";
  return diff + " days ago";
}

function getInvestorById(id) {
  return DW_DATA.investors.find((i) => i.id === id);
}

function getPeerById(id) {
  return DW_DATA.peers.find((p) => p.id === id);
}

function badgeForStage(stage) {
  return STAGE_BADGE[stage] || "badge-grey";
}

function badgeForOutcome(outcome) {
  return OUTCOME_BADGE[outcome] || "badge-grey";
}

function badgeForDirection(dir) {
  return DIRECTION_BADGE[dir] || "badge-grey";
}

// The two-axis status display: a stage badge, plus an outcome badge whenever it's not simply "active".
function statusBadges(inv) {
  let html = `<span class="badge ${badgeForStage(inv.stage)}">${STAGE_LABELS[inv.stage] || inv.stage}</span>`;
  if (inv.outcome && inv.outcome !== "active") {
    html += ` <span class="badge ${badgeForOutcome(inv.outcome)}">${OUTCOME_LABELS[inv.outcome] || inv.outcome}</span>`;
  }
  return html;
}

function leadBadge(isLead) {
  return isLead ? '<span class="badge badge-purple">Lead</span>' : '<span class="muted">—</span>';
}

function checkRange(inv) {
  const [min, max] = inv.ticketRange || [null, null];
  return `${fmtMoney(min)}–${fmtMoney(max)}`;
}

// ---------- Metrics ----------

function computeMetrics() {
  const investors = DW_DATA.investors;
  const total = investors.length;

  const atLeast = (stage) => investors.filter((i) => stageRank(i.stage) >= stageRank(stage));
  const closed = investors.filter((i) => i.stage === "closed");
  const committed = investors.filter((i) => i.stage === "committed" && i.outcome === "active");
  const passed = investors.filter((i) => i.outcome === "passed");
  const nextRound = investors.filter((i) => i.outcome === "next_round");
  const snoozed = investors.filter((i) => i.outcome === "snoozed");

  // "Active conversations" = live (outcome active) and still in flight (not yet closed).
  const active = investors.filter((i) => i.outcome === "active" && i.stage !== "closed");

  const sum = (arr) => arr.reduce((s, i) => s + (i.ticketEstimateUsd || 0), 0);
  const totalRaised = sum(closed);
  const pendingCommitted = sum(committed);
  const pipelineValue = sum(active);

  const responded = investors.filter((i) => stageRank(i.stage) > stageRank("contacted"));
  const responseRate = total ? Math.round((responded.length / total) * 100) : 0;
  const meetingRate = total ? Math.round((atLeast("meeting").length / total) * 100) : 0;
  const closeRate = total ? Math.round((closed.length / total) * 100) : 0;

  const inbound = investors.filter((i) => i.direction === "inbound");
  const outbound = investors.filter((i) => i.direction === "outbound");
  const closeRateFor = (arr) =>
    arr.length ? Math.round((arr.filter((i) => i.stage === "closed").length / arr.length) * 100) : 0;

  const avgCheck = closed.length ? Math.round(totalRaised / closed.length) : 0;

  // Funnel: how many investors reached AT LEAST each stage.
  const funnel = [
    { label: "Contacted", count: atLeast("contacted").length },
    { label: "Meeting", count: atLeast("meeting").length },
    { label: "Diligence", count: atLeast("diligence").length },
    { label: "Committed", count: atLeast("committed").length },
    { label: "Closed", count: closed.length },
  ];

  return {
    total,
    closedWon: closed.length,
    committed: committed.length,
    passed: passed.length,
    nextRound: nextRound.length,
    snoozed: snoozed.length,
    activeCount: active.length,
    totalRaised,
    pendingCommitted,
    pipelineValue,
    responseRate,
    meetingRate,
    closeRate,
    inboundCount: inbound.length,
    outboundCount: outbound.length,
    inboundCloseRate: closeRateFor(inbound),
    outboundCloseRate: closeRateFor(outbound),
    avgCheck,
    funnel,
  };
}

// Investors that overlap with peer founders — used for warm-intro suggestions.
function computeSharedNetwork() {
  return DW_DATA.investors
    .filter((i) => i.peerIds && i.peerIds.length > 0)
    .map((i) => ({
      investor: i,
      peers: i.peerIds.map(getPeerById).filter(Boolean),
    }))
    .sort((a, b) => b.peers.length - a.peers.length);
}

// ---------- UI helpers ----------

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.remove("show"), 2400);
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
