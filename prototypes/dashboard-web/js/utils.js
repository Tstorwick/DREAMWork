// Shared helpers used across views.

const STATUS_ORDER = [
  "Contacted",
  "Meeting Scheduled",
  "In Diligence",
  "Term Sheet",
  "Closed - Won",
  "Passed",
  "No Response",
];

const STATUS_BADGE = {
  "Contacted": "badge-grey",
  "Meeting Scheduled": "badge-blue",
  "In Diligence": "badge-amber",
  "Term Sheet": "badge-purple",
  "Closed - Won": "badge-green",
  "Passed": "badge-red",
  "No Response": "badge-grey",
};

const DIRECTION_BADGE = {
  inbound: "badge-blue",
  outbound: "badge-amber",
};

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

function badgeForStatus(status) {
  return STATUS_BADGE[status] || "badge-grey";
}

function badgeForDirection(dir) {
  return DIRECTION_BADGE[dir] || "badge-grey";
}

function warmthDots(warmth) {
  let html = '<span class="warmth-dots">';
  for (let i = 1; i <= 5; i++) {
    html += `<span class="warmth-dot ${i <= warmth ? "on" : ""}"></span>`;
  }
  html += "</span>";
  return html;
}

function checkRange(inv) {
  return `${fmtMoney(inv.checkMin)}–${fmtMoney(inv.checkMax)}`;
}

// ---------- Metrics ----------

function computeMetrics() {
  const investors = DW_DATA.investors;
  const total = investors.length;
  const closedWon = investors.filter((i) => i.status === "Closed - Won");
  const termSheet = investors.filter((i) => i.status === "Term Sheet");
  const passed = investors.filter((i) => i.status === "Passed");
  const noResponse = investors.filter((i) => i.status === "No Response");
  const meetingsPlus = investors.filter((i) =>
    ["Meeting Scheduled", "In Diligence", "Term Sheet", "Closed - Won"].includes(i.status)
  );
  const responded = investors.filter((i) => i.status !== "No Response");

  const totalRaised = closedWon.reduce((sum, i) => sum + (i.amount || 0), 0);
  const pendingCommitted = termSheet.reduce((sum, i) => sum + (i.amount || 0), 0);

  const activeStatuses = ["Contacted", "Meeting Scheduled", "In Diligence", "Term Sheet"];
  const activeInvestors = investors.filter((i) => activeStatuses.includes(i.status));
  const pipelineValue = activeInvestors.reduce(
    (sum, i) => sum + (i.checkMin + i.checkMax) / 2,
    0
  );

  const responseRate = total ? Math.round((responded.length / total) * 100) : 0;
  const meetingRate = total ? Math.round((meetingsPlus.length / total) * 100) : 0;
  const closeRate = total ? Math.round((closedWon.length / total) * 100) : 0;

  const inbound = investors.filter((i) => i.direction === "inbound");
  const outbound = investors.filter((i) => i.direction === "outbound");
  const inboundCloseRate = inbound.length
    ? Math.round((inbound.filter((i) => i.status === "Closed - Won").length / inbound.length) * 100)
    : 0;
  const outboundCloseRate = outbound.length
    ? Math.round((outbound.filter((i) => i.status === "Closed - Won").length / outbound.length) * 100)
    : 0;

  const avgCheck = closedWon.length
    ? Math.round(closedWon.reduce((s, i) => s + (i.amount || 0), 0) / closedWon.length)
    : 0;

  // Funnel counts (each stage = investors that reached AT LEAST that stage)
  const funnel = [
    { label: "Contacted", count: total },
    { label: "Meeting", count: meetingsPlus.length },
    { label: "Diligence", count: investors.filter((i) => ["In Diligence", "Term Sheet", "Closed - Won"].includes(i.status)).length },
    { label: "Term Sheet", count: investors.filter((i) => ["Term Sheet", "Closed - Won"].includes(i.status)).length },
    { label: "Closed", count: closedWon.length },
  ];

  return {
    total,
    closedWon: closedWon.length,
    termSheet: termSheet.length,
    passed: passed.length,
    noResponse: noResponse.length,
    totalRaised,
    pendingCommitted,
    pipelineValue,
    responseRate,
    meetingRate,
    closeRate,
    inboundCount: inbound.length,
    outboundCount: outbound.length,
    inboundCloseRate,
    outboundCloseRate,
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
