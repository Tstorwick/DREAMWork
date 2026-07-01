// App shell: navigation, header, modals, and wiring between views.

const VIEWS = {
  overview: renderOverview,
  investors: renderInvestors,
  connections: renderConnections,
  pipeline: renderPipeline,
  network: renderNetwork,
  activity: renderActivity,
};

let currentView = "overview";

function setView(view) {
  if (!VIEWS[view]) return;
  currentView = view;
  document.querySelectorAll(".nav-item, .mobile-nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
  VIEWS[view]();
}

function renderCurrentView() {
  VIEWS[currentView]();
}

function initHeader() {
  const f = DW_DATA.founder;
  document.getElementById("founder-avatar").textContent = f.initials;
  document.getElementById("founder-name").textContent = f.name;
  document.getElementById("founder-company").textContent = `${f.company} · ${f.role}`;

  const pct = Math.min(100, Math.round((f.raisedSoFar / f.targetRaise) * 100));
  document.getElementById("raise-current").textContent = fmtMoney(f.raisedSoFar);
  document.getElementById("raise-target").textContent = fmtMoney(f.targetRaise);
  document.getElementById("raise-fill").style.width = pct + "%";
  document.getElementById("raise-pct").textContent = `${pct}% to target`;
}

function initNav() {
  document.querySelectorAll(".nav-item[data-view], .mobile-nav-item[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.dataset.view));
  });
}

function initSearch() {
  const input = document.getElementById("global-search");
  input.addEventListener("input", () => {
    investorsState.search = input.value;
    if (currentView !== "investors") {
      setView("investors");
    } else {
      renderInvestorsTable();
    }
  });
}

// ---------- Modals ----------

function openModal(html) {
  document.getElementById("modal-root").innerHTML = html;
  document.getElementById("modal-backdrop").classList.add("open");
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.remove("open");
}

function openAddInvestorModal() {
  openModal(`
    <button class="close-x" id="modal-close">✕</button>
    <h3 class="modal-title">Add Investor</h3>
    <div class="form-group">
      <label class="form-label">Name</label>
      <input class="form-input" id="f-name" placeholder="e.g. Jordan Blake" />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">Firm</label>
        <input class="form-input" id="f-firm" placeholder="e.g. Fairwind Capital" />
      </div>
      <div class="form-group">
        <label class="form-label">Type</label>
        <select class="form-select" id="f-type">
          <option>VC</option><option>Angel</option><option>Corporate VC</option><option>Family Office</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">Direction</label>
        <select class="form-select" id="f-direction">
          <option value="outbound">Outbound (we contacted them)</option>
          <option value="inbound">Inbound (they contacted us)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Stage</label>
        <select class="form-select" id="f-stage">
          ${STAGE_ORDER.map((s) => `<option value="${s}">${STAGE_LABELS[s]}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">Check Min ($)</label>
        <input class="form-input" id="f-checkmin" type="number" placeholder="50000" />
      </div>
      <div class="form-group">
        <label class="form-label">Check Max ($)</label>
        <input class="form-input" id="f-checkmax" type="number" placeholder="250000" />
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Notes</label>
      <textarea class="form-textarea" id="f-notes" placeholder="Context, how you connected, next steps…"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" id="modal-cancel">Cancel</button>
      <button class="btn btn-primary" id="modal-save">Add Investor</button>
    </div>
  `);

  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-cancel").addEventListener("click", closeModal);
  document.getElementById("modal-save").addEventListener("click", async () => {
    const name = document.getElementById("f-name").value.trim();
    const firm = document.getElementById("f-firm").value.trim();
    if (!firm) { showToast("Firm is required"); return; }
    const min = Number(document.getElementById("f-checkmin").value) || null;
    const max = Number(document.getElementById("f-checkmax").value) || null;
    try {
      await apiPost("/rounds/" + DW_DATA.round.id + "/investors", { name, firm, stage: document.getElementById("f-stage").value, ticketMinUsd: min, ticketMaxUsd: max, notes: document.getElementById("f-notes").value.trim() });
      await loadData(); closeModal(); showToast("Added " + (name || firm)); renderCurrentView();
    } catch (e) { console.error(e); showToast("Could not add investor"); }
  });
}

function openLogActivityModal() {
  const investors = DW_DATA.investors;
  openModal(`
    <button class="close-x" id="modal-close">✕</button>
    <h3 class="modal-title">Log Activity</h3>
    <div class="form-group">
      <label class="form-label">Investor</label>
      <select class="form-select" id="f-investor">
        ${investors.map((i) => `<option value="${i.id}">${i.name} — ${i.firm}</option>`).join("")}
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Type</label>
      <select class="form-select" id="f-act-type">
        <option value="outbound">Outbound touch</option>
        <option value="inbound">Inbound touch</option>
        <option value="meeting">Meeting</option>
        <option value="term_sheet">Term sheet</option>
        <option value="closed_won">Closed — won</option>
        <option value="passed">Passed</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Note</label>
      <textarea class="form-textarea" id="f-act-text" placeholder="What happened?"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" id="modal-cancel">Cancel</button>
      <button class="btn btn-primary" id="modal-save">Log Activity</button>
    </div>
  `);

  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-cancel").addEventListener("click", closeModal);
  document.getElementById("modal-save").addEventListener("click", async () => {
    const entryId = document.getElementById("f-investor").value;
    const kind = document.getElementById("f-act-type").value;
    const text = document.getElementById("f-act-text").value.trim();
    if (!text) { showToast("Please add a note"); return; }
    try {
      await apiPost("/rounds/" + DW_DATA.round.id + "/activity", { entryId, kind, text });
      await loadData(); closeModal(); showToast("Activity logged"); renderCurrentView();
    } catch (e) { console.error(e); showToast("Could not log activity"); }
  });
}

// ---------- Init ----------

function initGlobalDismiss() {
  document.getElementById("modal-backdrop").addEventListener("click", (e) => {
    if (e.target.id === "modal-backdrop") closeModal();
  });
  document.getElementById("slideover-backdrop").addEventListener("click", (e) => {
    if (e.target.id === "slideover-backdrop") closeSlideover();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
      closeSlideover();
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  initNav();
  initSearch();
  initGlobalDismiss();

  document.getElementById("btn-add-investor").addEventListener("click", openAddInvestorModal);
  document.getElementById("btn-log-activity").addEventListener("click", openLogActivityModal);

  // Load live data before the first render — initHeader/setView read DW_DATA.
  try {
    await loadData();
  } catch (err) {
    console.error(err);
    if (typeof showToast === "function") showToast("Could not load data");
  }

  initHeader();
  setView("overview");
});
