// Render functions for each view. Every render* function returns an HTML string
// or writes directly into #content. State (filters, sort, search) lives in app.js
// and is passed in where needed.

let _funnelChart = null;
let _statusChart = null;

// ================= OVERVIEW =================

function renderOverview() {
  const m = computeMetrics();
  const shared = computeSharedNetwork().slice(0, 3);
  const recent = [...DW_DATA.activity].sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 6);

  document.getElementById("content").innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Overview</h1>
        <p class="view-desc">Your fundraising snapshot — pipeline health, response rates, and warm intro opportunities.</p>
      </div>
    </div>

    <div class="stat-grid">
      ${statCard("Total Raised", fmtMoney(m.totalRaised), `${fmtMoney(m.pendingCommitted)} committed, pending close`, "up")}
      ${statCard("Active Conversations", m.activeCount, `${fmtMoney(m.pipelineValue)} pipeline value`, "flat")}
      ${statCard("Close Rate", m.closeRate + "%", `${m.closedWon} of ${m.total} investors closed`, m.closeRate >= 15 ? "up" : "flat")}
      ${statCard("Response Rate", m.responseRate + "%", `${m.snoozed} snoozed · ${m.nextRound} next-round`, m.responseRate >= 70 ? "up" : "down")}
      ${statCard("Network Size", m.total, `${m.activeCount} active · ${m.passed} passed · ${m.nextRound} next-round`, "flat")}
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Fundraising Funnel</h3>
            <p class="panel-sub">How many investors reach each stage</p>
          </div>
        </div>
        <div class="chart-wrap"><canvas id="funnel-chart"></canvas></div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Pipeline by Stage</h3>
            <p class="panel-sub">Where your investors are right now</p>
          </div>
        </div>
        <div class="chart-wrap"><canvas id="status-chart"></canvas></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Recent Activity</h3>
            <p class="panel-sub">Latest updates across your network</p>
          </div>
          <button class="btn btn-ghost btn-small" data-nav="activity">View all</button>
        </div>
        ${renderTimeline(recent)}
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Warm Intro Opportunities</h3>
            <p class="panel-sub">Investors shared with founders in your network</p>
          </div>
          <button class="btn btn-ghost btn-small" data-nav="network">View all</button>
        </div>
        <div class="list">
          ${shared.map(sharedCardCompact).join("") || emptyState("No shared investors yet")}
        </div>
      </div>
    </div>
  `;

  document.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.dataset.nav));
  });

  document.querySelectorAll("[data-investor-id]").forEach((el) => {
    el.addEventListener("click", () => openInvestorDetail(el.dataset.investorId));
  });

  renderFunnelChart(m.funnel);
  renderStatusChart();
}

function statCard(label, value, delta, trend) {
  return `
    <div class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
      <div class="stat-delta ${trend}">${delta}</div>
    </div>
  `;
}

function renderFunnelChart(funnel) {
  const ctx = document.getElementById("funnel-chart");
  if (!ctx) return;
  if (_funnelChart) _funnelChart.destroy();
  _funnelChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: funnel.map((f) => f.label),
      datasets: [{
        data: funnel.map((f) => f.count),
        backgroundColor: ["#60a5fa", "#4ade80", "#fbbf24", "#c084fc", "#4ade80"],
        borderRadius: 6,
        maxBarThickness: 46,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#aab3c2" } },
        y: { beginAtZero: true, grid: { color: "#1a212c" }, ticks: { color: "#aab3c2", precision: 0 } },
      },
    },
  });
}

function renderStatusChart() {
  const ctx = document.getElementById("status-chart");
  if (!ctx) return;
  if (_statusChart) _statusChart.destroy();
  const counts = {};
  DW_DATA.investors.forEach((i) => { counts[i.stage] = (counts[i.stage] || 0) + 1; });
  const stages = STAGE_ORDER.filter((s) => counts[s]);
  const stageColor = {
    sourced: "#6b7686", intro_requested: "#6b7686", contacted: "#60a5fa", meeting: "#38bdf8",
    in_conversation: "#818cf8", diligence: "#fbbf24", committed: "#c084fc", closed: "#4ade80",
  };
  _statusChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: stages.map((s) => `${STAGE_LABELS[s]} (${counts[s]})`),
      datasets: [{
        data: stages.map((s) => counts[s]),
        backgroundColor: stages.map((s) => stageColor[s] || "#6b7686"),
        borderColor: "#131822",
        borderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { position: "bottom", labels: { color: "#aab3c2", boxWidth: 10, padding: 14, font: { size: 11.5 } } },
      },
    },
  });
}

function renderTimeline(items) {
  if (!items.length) return emptyState("No activity yet");
  const dotColor = {
    inbound: "#60a5fa", outbound: "#fbbf24", meeting: "#c084fc",
    committed: "#4ade80", closed_won: "#4ade80", passed: "#f87171",
  };
  return `<div class="timeline">${items.map((a) => {
    const inv = getInvestorById(a.investorId);
    return `
      <div class="timeline-item">
        <div class="timeline-dot" style="background:${dotColor[a.type] || "#6b7686"}"></div>
        <div class="row-main">
          <div class="timeline-text">${escapeHtml(a.text)}</div>
          <div class="timeline-date">${fmtDate(a.date)} · ${inv ? inv.firm : ""}</div>
        </div>
      </div>
    `;
  }).join("")}</div>`;
}

function sharedCardCompact(entry) {
  const inv = entry.investor;
  return `
    <div class="row-card" data-investor-id="${inv.id}">
      <div class="avatar avatar-sm" style="background:${inv.color}22;color:${inv.color}">${inv.initials}</div>
      <div class="row-main">
        <div class="row-name">${inv.name}</div>
        <div class="row-sub">${inv.firm} · shared with ${entry.peers.map((p) => p.name.split(" ")[0]).join(", ")}</div>
      </div>
      ${statusBadges(inv)}
    </div>
  `;
}

function emptyState(msg) {
  return `<div class="empty-state">${msg}</div>`;
}

// ================= INVESTORS =================

const investorsState = { search: "", direction: "all", stage: "all", sortKey: "lastActivity", sortDir: "desc" };

function renderInvestors() {
  document.getElementById("content").innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Investors</h1>
        <p class="view-desc">Every investor relationship in one place — filter, sort, and drill in for details.</p>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-spacer"></div>
      <select class="select-input" id="status-filter">
        <option value="all">All stages</option>
        ${STAGE_ORDER.map((s) => `<option value="${s}" ${investorsState.stage === s ? "selected" : ""}>${STAGE_LABELS[s]}</option>`).join("")}
      </select>
    </div>

    <div class="panel">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th data-sort="name">Investor</th>
              <th data-sort="stage">Stage</th>
              <th data-sort="ticketEstimateUsd">Est. Ticket</th>
              <th data-sort="isLead">Lead</th>
              <th data-sort="lastActivity">Last Activity</th>
            </tr>
          </thead>
          <tbody id="investors-tbody"></tbody>
        </table>
      </div>
    </div>
  `;

  document.querySelectorAll("[data-dir]").forEach((btn) => {
    btn.addEventListener("click", () => {
      investorsState.direction = btn.dataset.dir;
      renderInvestors();
    });
  });

  document.getElementById("status-filter").addEventListener("change", (e) => {
    investorsState.stage = e.target.value;
    renderInvestorsTable();
  });

  document.querySelectorAll("[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (investorsState.sortKey === key) {
        investorsState.sortDir = investorsState.sortDir === "asc" ? "desc" : "asc";
      } else {
        investorsState.sortKey = key;
        investorsState.sortDir = "desc";
      }
      renderInvestorsTable();
    });
  });

  renderInvestorsTable();
}

function getFilteredInvestors() {
  let rows = DW_DATA.investors.slice();
  const q = investorsState.search.trim().toLowerCase();
  if (q) {
    rows = rows.filter((i) =>
      i.name.toLowerCase().includes(q) || i.firm.toLowerCase().includes(q) ||
      i.sectors.join(" ").toLowerCase().includes(q)
    );
  }
  if (investorsState.direction !== "all") rows = rows.filter((i) => i.direction === investorsState.direction);
  if (investorsState.stage !== "all") rows = rows.filter((i) => i.stage === investorsState.stage);

  const { sortKey, sortDir } = investorsState;
  rows.sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey];
    if (sortKey === "name") { av = a.name; bv = b.name; }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
  return rows;
}

function renderInvestorsTable() {
  const tbody = document.getElementById("investors-tbody");
  if (!tbody) return;
  const rows = getFilteredInvestors();
  tbody.innerHTML = rows.length
    ? rows.map((inv) => `
      <tr data-investor-id="${inv.id}">
        <td>
          <div class="cell-investor">
            <div class="avatar avatar-sm" style="background:${inv.color}22;color:${inv.color}">${inv.initials}</div>
            <div>
              <div class="cell-investor-name">${inv.name}</div>
              <div class="cell-investor-firm">${inv.firm}</div>
            </div>
          </div>
        </td>
        <td>${statusBadges(inv)}</td>
        <td>${inv.ticketEstimateUsd ? fmtMoney(inv.ticketEstimateUsd) : checkRange(inv)}</td>
        <td>${leadBadge(inv.isLead)}</td>
        <td class="muted">${daysAgo(inv.lastActivity)}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="5">${emptyState("No investors match these filters")}</td></tr>`;

  tbody.querySelectorAll("[data-investor-id]").forEach((tr) => {
    tr.addEventListener("click", () => openInvestorDetail(tr.dataset.investorId));
  });
}

// ================= CONNECTIONS =================

function renderConnections() {
  const inbound = DW_DATA.investors.filter((i) => i.direction === "inbound")
    .sort((a, b) => (a.lastActivity < b.lastActivity ? 1 : -1));
  const outbound = DW_DATA.investors.filter((i) => i.direction === "outbound")
    .sort((a, b) => (a.lastActivity < b.lastActivity ? 1 : -1));

  document.getElementById("content").innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Connections</h1>
        <p class="view-desc">Who's reaching out to you, and who you're reaching out to.</p>
      </div>
    </div>

    <div class="grid-2-even">
      <div class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Inbound <span class="badge badge-blue">${inbound.length}</span></h3>
            <p class="panel-sub">Investors who contacted you first</p>
          </div>
        </div>
        <div class="list">${inbound.map(connectionRow).join("") || emptyState("No inbound connections")}</div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <h3 class="panel-title">Outbound <span class="badge badge-amber">${outbound.length}</span></h3>
            <p class="panel-sub">Investors you reached out to</p>
          </div>
        </div>
        <div class="list">${outbound.map(connectionRow).join("") || emptyState("No outbound connections")}</div>
      </div>
    </div>
  `;

  document.querySelectorAll("[data-investor-id]").forEach((el) => {
    el.addEventListener("click", () => openInvestorDetail(el.dataset.investorId));
  });
}

function connectionRow(inv) {
  return `
    <div class="row-card" data-investor-id="${inv.id}">
      <div class="avatar avatar-sm" style="background:${inv.color}22;color:${inv.color}">${inv.initials}</div>
      <div class="row-main">
        <div class="row-name">${inv.name}</div>
        <div class="row-sub">${inv.firm}${inv.introducedBy ? " · via " + inv.introducedBy : ""}</div>
      </div>
      <div class="row-meta">
        ${statusBadges(inv)}
        <div style="margin-top:5px">${daysAgo(inv.lastActivity)}</div>
      </div>
    </div>
  `;
}

// ================= PIPELINE =================

function renderPipeline() {
  document.getElementById("content").innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Pipeline</h1>
        <p class="view-desc">Drag investors between stages as deals progress.</p>
      </div>
    </div>
    <div class="kanban" id="kanban-board">
      ${STAGE_ORDER.map(pipelineColumn).join("")}
    </div>
    <p class="view-desc" style="margin-top:14px">Showing active conversations. Passed, snoozed, and next-round investors are tracked on their entries but hidden from the board.</p>
  `;

  wireKanbanDragDrop();
}

function pipelineColumn(stage) {
  // The board is the active pipeline: only outcome === "active" entries appear.
  const items = DW_DATA.investors.filter((i) => i.stage === stage && i.outcome === "active");
  return `
    <div class="kanban-col" data-stage="${stage}">
      <div class="kanban-col-header">
        <span class="kanban-col-title">${STAGE_LABELS[stage]}</span>
        <span class="kanban-count">${items.length}</span>
      </div>
      <div class="kanban-drop-zone" data-stage="${stage}">
        ${items.map(kanbanCard).join("")}
      </div>
    </div>
  `;
}

function kanbanCard(inv) {
  return `
    <div class="kanban-card" draggable="true" data-investor-id="${inv.id}">
      <div class="kanban-card-title">${inv.name}</div>
      <div class="kanban-card-sub">${inv.firm} · ${checkRange(inv)}</div>
      <div class="kanban-card-foot">
        ${inv.isLead ? '<span class="badge badge-purple">Lead</span>' : "<span></span>"}
        <span class="muted">${daysAgo(inv.lastActivity)}</span>
      </div>
    </div>
  `;
}

function wireKanbanDragDrop() {
  let draggedId = null;

  document.querySelectorAll(".kanban-card").forEach((card) => {
    card.addEventListener("dragstart", (e) => {
      draggedId = card.dataset.investorId;
      e.dataTransfer.effectAllowed = "move";
    });
    card.addEventListener("click", () => openInvestorDetail(card.dataset.investorId));
  });

  document.querySelectorAll(".kanban-col").forEach((col) => {
    col.addEventListener("dragover", (e) => {
      e.preventDefault();
      col.classList.add("drag-over");
    });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", (e) => {
      e.preventDefault();
      col.classList.remove("drag-over");
      if (!draggedId) return;
      const inv = getInvestorById(draggedId);
      const newStage = col.dataset.stage;
      if (inv && inv.stage !== newStage) {
        const oldStage = inv.stage;
        inv.stage = newStage;
        inv.lastActivity = "2026-07-01";
        DW_DATA.activity.unshift({
          id: "a" + Date.now(),
          date: "2026-07-01",
          type: newStage === "closed" ? "closed_won" : "outbound",
          investorId: inv.id,
          text: `${inv.name} moved from ${STAGE_LABELS[oldStage]} to ${STAGE_LABELS[newStage]}.`,
        });
        apiPatch("/pipeline/" + inv.entryId, { stage: inv.stage, outcome: inv.outcome }).catch(() => (typeof showToast === "function") && showToast("Save failed"));
        showToast(`Moved ${inv.name} to "${STAGE_LABELS[newStage]}"`);
        renderPipeline();
      }
    });
  });
}

// ================= NETWORK =================

function renderNetwork() {
  const shared = computeSharedNetwork();

  document.getElementById("content").innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Shared Investor Network</h1>
        <p class="view-desc">Investors you have in common with other founders — a map of warm intro paths.</p>
      </div>
    </div>

    <div class="stat-grid">
      ${statCard("Shared Investors", shared.length, `out of ${DW_DATA.investors.length} total`, "flat")}
      ${statCard("Connected Founders", DW_DATA.peers.length, "in your extended network", "flat")}
      ${statCard("Warm-Introduced Deals", DW_DATA.investors.filter(i => i.introducedBy).length, "sourced via intro", "up")}
    </div>

    <div class="panel">
      <div class="panel-header">
        <div>
          <h3 class="panel-title">Overlap Map</h3>
          <p class="panel-sub">Each card shows an investor and which peer founders share that relationship</p>
        </div>
      </div>
      ${shared.map(networkCard).join("") || emptyState("No shared investor data yet")}
    </div>
  `;

  document.querySelectorAll("[data-investor-id]").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.closest(".peer-pill")) return;
      openInvestorDetail(el.dataset.investorId);
    });
  });
}

function networkCard(entry) {
  const inv = entry.investor;
  return `
    <div class="network-card" data-investor-id="${inv.id}" style="cursor:pointer">
      <div class="network-card-head">
        <div class="cell-investor">
          <div class="avatar avatar-sm" style="background:${inv.color}22;color:${inv.color}">${inv.initials}</div>
          <div>
            <div class="cell-investor-name">${inv.name} <span class="muted">— ${inv.firm}</span></div>
            <div class="cell-investor-firm">${checkRange(inv)} · ${inv.sectors.join(", ")}</div>
          </div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">${statusBadges(inv)}</div>
      </div>
      <div class="peer-pill-row">
        ${entry.peers.map((p) => `
          <div class="peer-pill">
            <div class="avatar avatar-sm" style="width:20px;height:20px;font-size:9px;background:#2c1f4522;color:var(--purple)">${p.initials}</div>
            ${p.name} · ${p.company}
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

// ================= ACTIVITY =================

function renderActivity() {
  const items = [...DW_DATA.activity].sort((a, b) => (a.date < b.date ? 1 : -1));
  document.getElementById("content").innerHTML = `
    <div class="view-header">
      <div>
        <h1 class="view-title">Activity</h1>
        <p class="view-desc">Full chronological history of every interaction across your fundraising network.</p>
      </div>
    </div>
    <div class="panel">
      ${renderTimeline(items)}
    </div>
  `;
}

// ================= INVESTOR DETAIL SLIDEOVER =================

function openInvestorDetail(id) {
  const inv = getInvestorById(id);
  if (!inv) return;
  const peers = (inv.peerIds || []).map(getPeerById).filter(Boolean);
  const relatedActivity = DW_DATA.activity.filter((a) => a.investorId === id)
    .sort((a, b) => (a.date < b.date ? 1 : -1));

  document.getElementById("slideover-root").innerHTML = `
    <button class="close-x" id="slideover-close">✕</button>
    <div class="detail-header">
      <div class="avatar" style="background:${inv.color}22;color:${inv.color}">${inv.initials}</div>
      <div>
        <div class="detail-name">${inv.name}</div>
        <div class="detail-firm">${inv.firm} · ${inv.type}</div>
      </div>
    </div>

    <div class="detail-section">
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${statusBadges(inv)}
        ${inv.isLead ? '<span class="badge badge-purple">Lead</span>' : ""}
      </div>
    </div>

    <div class="detail-section">
      <div class="detail-section-title">Details</div>
      <div class="kv-grid">
        <div class="kv-item"><div class="kv-label">Check Size</div><div class="kv-value">${checkRange(inv)}</div></div>
        <div class="kv-item"><div class="kv-label">Location</div><div class="kv-value">${inv.location}</div></div>
        <div class="kv-item"><div class="kv-label">Stage Focus</div><div class="kv-value">${inv.stageFocus.join(", ")}</div></div>
        <div class="kv-item"><div class="kv-label">Sectors</div><div class="kv-value">${inv.sectors.join(", ")}</div></div>
        <div class="kv-item"><div class="kv-label">Lead</div><div class="kv-value">${leadBadge(inv.isLead)}</div></div>
        <div class="kv-item"><div class="kv-label">Est. Ticket</div><div class="kv-value">${inv.ticketEstimateUsd ? fmtMoneyFull(inv.ticketEstimateUsd) : "—"}</div></div>
        <div class="kv-item"><div class="kv-label">Next Step</div><div class="kv-value">${inv.nextStep ? escapeHtml(inv.nextStep) : "—"}</div></div>
        <div class="kv-item"><div class="kv-label">Last Activity</div><div class="kv-value">${daysAgo(inv.lastActivity)}</div></div>
      </div>
    </div>

    ${inv.introducedBy ? `
    <div class="detail-section">
      <div class="detail-section-title">Introduced By</div>
      <div class="note-box">${inv.introducedBy}</div>
    </div>` : ""}

    <div class="detail-section">
      <div class="detail-section-title">Notes</div>
      <div class="note-box">${escapeHtml(inv.notes)}</div>
    </div>

    ${peers.length ? `
    <div class="detail-section">
      <div class="detail-section-title">Shared With</div>
      <div class="peer-pill-row">
        ${peers.map((p) => `<div class="peer-pill"><div class="avatar avatar-sm" style="width:20px;height:20px;font-size:9px">${p.initials}</div>${p.name} · ${p.company}</div>`).join("")}
      </div>
    </div>` : ""}

    <div class="detail-section">
      <div class="detail-section-title">History</div>
      ${renderTimeline(relatedActivity)}
    </div>

    <div class="modal-actions" style="justify-content:flex-start;flex-wrap:wrap">
      <select class="select-input" id="detail-stage-select">
        ${STAGE_ORDER.map((s) => `<option value="${s}" ${s === inv.stage ? "selected" : ""}>${STAGE_LABELS[s]}</option>`).join("")}
      </select>
      <select class="select-input" id="detail-outcome-select">
        ${OUTCOME_ORDER.map((o) => `<option value="${o}" ${o === inv.outcome ? "selected" : ""}>${OUTCOME_LABELS[o]}</option>`).join("")}
      </select>
      <button class="btn btn-primary btn-small" id="detail-status-save">Update</button>
    </div>
  `;

  document.getElementById("slideover-backdrop").classList.add("open");
  document.getElementById("slideover-close").addEventListener("click", closeSlideover);
  document.getElementById("detail-status-save").addEventListener("click", () => {
    const newStage = document.getElementById("detail-stage-select").value;
    const newOutcome = document.getElementById("detail-outcome-select").value;
    if (newStage !== inv.stage || newOutcome !== inv.outcome) {
      inv.stage = newStage;
      inv.outcome = newOutcome;
      inv.lastActivity = "2026-07-01";
      DW_DATA.activity.unshift({
        id: "a" + Date.now(), date: "2026-07-01",
        type: newStage === "closed" ? "closed_won" : newOutcome === "passed" ? "passed" : "outbound",
        investorId: inv.id,
        text: `${inv.name} updated to ${STAGE_LABELS[newStage]} · ${OUTCOME_LABELS[newOutcome]}.`,
      });
      apiPatch("/pipeline/" + inv.entryId, { stage: inv.stage, outcome: inv.outcome }).catch(() => (typeof showToast === "function") && showToast("Save failed"));
      showToast(`${inv.name} updated`);
      closeSlideover();
      renderCurrentView();
    }
  });
}

function closeSlideover() {
  document.getElementById("slideover-backdrop").classList.remove("open");
}
