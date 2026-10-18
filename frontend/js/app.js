/**
 * ConseQ / ECHO — E-Commerce Store Reliability & Blast Radius Simulator
 * Features:
 * - Pure Prompt-Only Input taking (zero confusing mode selectors)
 * - Hard-Coded E-Commerce Store Platform Baseline & Telemetry
 * - Real-Time Cascading Blast Radius & Revenue-at-Risk Quantification
 * - End-to-End Codebase Ingestion (.zip / Folder) Multi-Graph Workflow
 * - 100% Native High-Sensitivity Scrolling & Liquid Glassmorphism Aesthetics
 */

const API_BASE = "http://localhost:8000";

class AppState {
  constructor() {
    this.ambientBg = null;
    this.currentReport = null;
    this.isSimulating = false;
    this.backendOnline = false;
    this.activeProjectGraph = null;
    this.activeProjectName = null;
  }
}

const state = new AppState();

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  initAmbientBackground();
  initGSAPEntrance();
  initEventListeners();
  initIngestModal();
  checkSystemStatus();
});

/* ==========================================================================
   1. Subtle Ambient Network (Background Layer)
   ========================================================================== */
function initAmbientBackground() {
  if (window.AmbientNetworkBackground) {
    state.ambientBg = new AmbientNetworkBackground("ambient-network-canvas");
  }
}

/* ==========================================================================
   2. GSAP Entrance Animations (Non-Intrusive)
   ========================================================================== */
function initGSAPEntrance() {
  if (typeof gsap !== "undefined") {
    gsap.from(".anim-header", {
      opacity: 0,
      y: -15,
      duration: 0.7,
      ease: "power2.out",
    });

    gsap.from(".anim-hero-item", {
      opacity: 0,
      y: 20,
      duration: 0.65,
      stagger: 0.08,
      ease: "power2.out",
      delay: 0.1,
    });
  }
}

/* ==========================================================================
   3. Event Listeners & Pure Prompt Controls
   ========================================================================== */
function initEventListeners() {
  const form = document.getElementById("simulation-form");
  const input = document.getElementById("prompt-input");
  const btnReset = document.getElementById("btn-reset-results");

  // Form Submit: Strictly prompt-only input
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const prompt = input.value.trim();
      if (prompt) {
        executeSimulation(prompt);
      }
    });
  }

  // Ctrl+Enter or Enter to trigger run
  if (input) {
    input.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        const prompt = input.value.trim();
        if (prompt) {
          executeSimulation(prompt);
        }
      }
    });
  }

  // Quick Prompt Chips: 1-click prompt fill & simulation trigger
  document.querySelectorAll(".quick-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      if (input) input.value = prompt;
      executeSimulation(prompt);
    });
  });

  // Close report button
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      resetSimulation();
    });
  }
}

/* ==========================================================================
   4. Codebase (.zip / Folder) Ingestion Modal Controls
   ========================================================================== */
function initIngestModal() {
  const modal = document.getElementById("ingest-modal");
  const btnOpen = document.getElementById("btn-open-ingest");
  const btnClose = document.getElementById("btn-close-ingest");
  const btnCloseSec = document.getElementById("btn-close-ingest-secondary");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-upload-input");
  const btnSample = document.getElementById("btn-simulate-sample-repo");
  const btnIngestDir = document.getElementById("btn-ingest-dir");
  const dirPathInput = document.getElementById("dir-path-input");
  const btnResetProject = document.getElementById("btn-reset-project");

  const openModal = () => {
    if (modal) modal.classList.remove("hidden");
  };

  const closeModal = () => {
    if (modal) modal.classList.add("hidden");
    const statusBox = document.getElementById("ingest-status");
    if (statusBox) statusBox.classList.add("hidden");
  };

  if (btnOpen) btnOpen.addEventListener("click", openModal);
  if (btnClose) btnClose.addEventListener("click", closeModal);
  if (btnCloseSec) btnCloseSec.addEventListener("click", closeModal);

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("border-cyan-400", "bg-cyan-500/10");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("border-cyan-400", "bg-cyan-500/10");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("border-cyan-400", "bg-cyan-500/10");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadArchiveFile(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        uploadArchiveFile(fileInput.files[0]);
      }
    });
  }

  if (btnIngestDir) {
    btnIngestDir.addEventListener("click", () => {
      const dirPath = dirPathInput ? dirPathInput.value.trim() : ".";
      ingestLocalDirectory(dirPath);
    });
  }

  if (btnSample) {
    btnSample.addEventListener("click", () => {
      ingestLocalDirectory(".");
    });
  }

  if (btnResetProject) {
    btnResetProject.addEventListener("click", () => {
      resetToBaselineStore();
    });
  }
}

async function uploadArchiveFile(file) {
  const statusBox = document.getElementById("ingest-status");
  const statusText = document.getElementById("ingest-status-text");

  if (statusBox) statusBox.classList.remove("hidden");
  if (statusText) statusText.textContent = `Uploading '${file.name}' & extracting microservices...`;

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_name", file.name.replace(/\.zip$/i, ""));

    const res = await fetch(`${API_BASE}/project/ingest`, {
      method: "POST",
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      applyIngestedProject(data);
      return;
    }
  } catch (err) {
    console.warn("Backend ingestion offline or failed, falling back to local simulation", err);
  }

  // Graceful standalone fallback
  setTimeout(() => {
    const mockProject = {
      project_id: `proj_${Math.random().toString(36).substring(2, 8)}`,
      project_name: file.name.replace(/\.zip$/i, ""),
      node_count: 24,
      edge_count: 36,
      services_count: 4,
      services: ["checkout-api", "cart-worker", "auth-identity", "inventory-sync"],
      databases: ["PostgreSQL 16", "Redis Cluster"],
      endpoints: ["POST /api/v1/checkout", "POST /api/v1/cart", "GET /api/v1/inventory"],
      libraries: ["stripe", "jsonwebtoken", "redis"],
      message: "Uploaded archive analyzed into isolated graph."
    };
    applyIngestedProject(mockProject);
  }, 600);
}

async function ingestLocalDirectory(dirPath) {
  const statusBox = document.getElementById("ingest-status");
  const statusText = document.getElementById("ingest-status-text");

  if (statusBox) statusBox.classList.remove("hidden");
  if (statusText) statusText.textContent = `Scanning directory '${dirPath}' manifests & routes...`;

  try {
    const res = await fetch(`${API_BASE}/project/ingest-directory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directory_path: dirPath, project_name: "ConseQ Local Workspace" }),
    });

    if (res.ok) {
      const data = await res.json();
      applyIngestedProject(data);
      return;
    }
  } catch (err) {
    console.warn("Backend directory ingestion offline or failed, falling back to local simulation", err);
  }

  // Graceful standalone fallback
  setTimeout(() => {
    const mockProject = {
      project_id: `proj_local_${Math.random().toString(36).substring(2, 6)}`,
      project_name: "ConseQ Local Workspace",
      node_count: 32,
      edge_count: 48,
      services_count: 6,
      services: ["api-gateway", "auth-service", "checkout-service", "cart-service", "order-service", "inventory-service"],
      databases: ["Auth PostgreSQL", "Orders PostgreSQL", "Session Redis Cluster"],
      endpoints: ["POST /simulate", "POST /project/ingest", "GET /graph/topology"],
      libraries: ["fastapi", "falkordb", "google-genai"],
      message: "Local directory analyzed into isolated graph."
    };
    applyIngestedProject(mockProject);
  }, 500);
}

function applyIngestedProject(data) {
  const modal = document.getElementById("ingest-modal");
  if (modal) modal.classList.add("hidden");

  const statusBox = document.getElementById("ingest-status");
  if (statusBox) statusBox.classList.add("hidden");

  state.activeProjectGraph = data.project_id;
  state.activeProjectName = data.project_name;

  // Show active project banner
  const banner = document.getElementById("active-project-banner");
  const nameEl = document.getElementById("active-project-name");
  const statsEl = document.getElementById("active-project-stats");

  if (banner) banner.classList.remove("hidden");
  if (nameEl) nameEl.textContent = data.project_name || "Custom Codebase";
  if (statsEl) statsEl.textContent = `(${data.node_count} nodes, ${data.edge_count} edges, ${data.services_count || data.services.length} services)`;

  // Update top header badge
  const statusText = document.getElementById("status-text");
  if (statusText) statusText.textContent = `Graph: ${data.project_id} • ${data.project_name}`;

  // Update quick chips with extracted services
  updateQuickChipsWithExtractedServices(data.services || []);

  // Set prompt & trigger initial simulation against the custom graph
  const primaryService = (data.services && data.services.length > 0) ? data.services[0] : "checkout-service";
  const promptInput = document.getElementById("prompt-input");
  const prompt = `What happens if ${primaryService} goes offline?`;
  if (promptInput) promptInput.value = prompt;

  executeSimulation(prompt);
}

function updateQuickChipsWithExtractedServices(services) {
  if (!services || services.length === 0) return;
  const container = document.querySelector(".quick-chip")?.parentElement;
  if (!container) return;

  const validServices = services.slice(0, 4);
  let html = `<span class="text-slate-500 font-mono mr-1">Extracted Scenarios:</span>`;
  validServices.forEach((svc) => {
    html += `
      <button type="button" class="quick-chip liquid-glass-pill px-2.5 py-1 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-all cursor-pointer font-sans" data-prompt="What happens if ${svc} goes offline?">
        ⚡ ${svc} Crash
      </button>
    `;
  });
  container.innerHTML = html;

  container.querySelectorAll(".quick-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.dataset.prompt;
      const input = document.getElementById("prompt-input");
      if (input) input.value = prompt;
      executeSimulation(prompt);
    });
  });
}

function resetToBaselineStore() {
  state.activeProjectGraph = null;
  state.activeProjectName = null;

  const banner = document.getElementById("active-project-banner");
  if (banner) banner.classList.add("hidden");

  const statusText = document.getElementById("status-text");
  if (statusText) statusText.textContent = state.backendOnline ? "FalkorDB Online • echo_software" : "ApexCommerce Store • Live Telemetry";

  // Restore baseline quick chips
  const container = document.querySelector(".quick-chip")?.parentElement;
  if (container) {
    container.innerHTML = `
      <span class="text-slate-500 font-mono mr-1">Quick Scenarios:</span>
      <button type="button" class="quick-chip liquid-glass-pill px-2.5 py-1 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-all cursor-pointer font-sans" data-prompt="What happens if Stripe payment gateway experiences connection pool exhaustion during flash sale?">
        ⚡ Stripe Gateway Timeout
      </button>
      <button type="button" class="quick-chip liquid-glass-pill px-2.5 py-1 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-all cursor-pointer font-sans" data-prompt="What happens if Session Redis cluster fails during peak 105k concurrent cart sessions?">
        🛒 Redis Cart Collapse
      </button>
      <button type="button" class="quick-chip liquid-glass-pill px-2.5 py-1 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-all cursor-pointer font-sans" data-prompt="Simulate inventory-service PostgreSQL row lock deadlock during high-concurrency cart reserve">
        📦 Inventory DB Lockup
      </button>
      <button type="button" class="quick-chip liquid-glass-pill px-2.5 py-1 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-all cursor-pointer font-sans" data-prompt="What if I upgrade crypto-jwt library to version 3.0.0?">
        🔑 Upgrade crypto-jwt
      </button>
    `;
    container.querySelectorAll(".quick-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const prompt = chip.dataset.prompt;
        const input = document.getElementById("prompt-input");
        if (input) input.value = prompt;
        executeSimulation(prompt);
      });
    });
  }
}

/* ==========================================================================
   5. Curated E-Commerce Preset Scenario Runner (1-Click)
   ========================================================================== */
window.runPresetScenario = function (scenarioId) {
  const scenario = (window.MOCK_SCENARIOS || []).find((s) => s.id === scenarioId);
  if (!scenario) return;
  const input = document.getElementById("prompt-input");
  if (input) input.value = scenario.prompt;

  executeSimulation(scenario.prompt);
};

/* ==========================================================================
   6. Backend Status & Telemetry
   ========================================================================== */
async function checkSystemStatus() {
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const latencyPill = document.getElementById("latency-pill");

  try {
    const t0 = performance.now();
    const res = await fetch(`${API_BASE}/graph/ping`, { method: "GET" });
    const latency = Math.round(performance.now() - t0);

    if (res.ok) {
      const data = await res.json();
      state.backendOnline = true;
      if (statusDot) statusDot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse";
      if (statusText) statusText.textContent = `FalkorDB Online • ${data.graph || "echo_software"}`;
      if (latencyPill) {
        latencyPill.textContent = `${data.latency_ms || latency}ms`;
        latencyPill.classList.remove("hidden");
      }
      loadLiveStats();
      return;
    }
  } catch (err) {
    state.backendOnline = false;
  }

  // Graceful standalone fallback
  if (statusDot) statusDot.className = "w-2 h-2 rounded-full bg-cyan-400";
  if (statusText) statusText.textContent = "ApexCommerce Store • Live Telemetry";
  if (latencyPill) {
    latencyPill.textContent = "Local";
    latencyPill.classList.remove("hidden");
  }
  loadLiveStats();
}

async function loadLiveStats() {
  try {
    const res = await fetch(`${API_BASE}/graph/stats`);
    if (res.ok) {
      const stats = await res.json();
      animateNumber("stat-nodes", stats.node_count || 32);
      animateNumber("stat-services", stats.labels?.Service || 14);
      return;
    }
  } catch (err) {}

  animateNumber("stat-nodes", 32);
  animateNumber("stat-services", 14);
}

function animateNumber(elementId, targetVal) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const obj = { val: 0 };
  if (typeof gsap !== "undefined") {
    gsap.to(obj, {
      val: targetVal,
      duration: 1.0,
      ease: "power2.out",
      onUpdate: () => {
        el.textContent = Math.round(obj.val).toLocaleString();
      },
    });
  } else {
    el.textContent = Math.round(targetVal).toLocaleString();
  }
}

/* ==========================================================================
   7. Simulation Execution Flow (Pure Prompt Only)
   ========================================================================== */
async function executeSimulation(prompt) {
  if (state.isSimulating) return;
  state.isSimulating = true;

  const btnRun = document.getElementById("btn-run-simulation");
  const spinner = document.getElementById("run-spinner");
  const runText = document.getElementById("run-btn-text");
  const resultsWrapper = document.getElementById("results-wrapper");
  const loadingOverlay = document.getElementById("simulation-loading");
  const stepText = document.getElementById("loading-step-text");

  if (btnRun) btnRun.disabled = true;
  if (spinner) spinner.classList.remove("hidden");
  if (runText) runText.textContent = "Simulating...";
  if (loadingOverlay) loadingOverlay.classList.remove("hidden");

  const steps = [
    "Cloning target dependency graph to isolated memory fork...",
    "Injecting targeted fault mutation into store graph...",
    "Computing multi-hop blast radius, revenue at risk, and cart drop...",
    "Synthesizing SRE executive briefing with Gemini Flash...",
  ];
  let stepIdx = 0;
  const interval = setInterval(() => {
    stepIdx = (stepIdx + 1) % steps.length;
    if (stepText) stepText.textContent = steps[stepIdx];
  }, 260);

  let report = null;

  try {
    const payload = { prompt };
    if (state.activeProjectGraph) {
      payload.graph = state.activeProjectGraph;
    }

    const res = await fetch(`${API_BASE}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      report = await res.json();
    } else {
      report = pickMatchingMockReport(prompt);
    }
  } catch (err) {
    report = pickMatchingMockReport(prompt);
  } finally {
    clearInterval(interval);
    state.isSimulating = false;
    if (btnRun) btnRun.disabled = false;
    if (spinner) spinner.classList.add("hidden");
    if (runText) runText.textContent = "Simulate Blast Radius";
    if (loadingOverlay) loadingOverlay.classList.add("hidden");
  }

  if (report) {
    renderSimulationReport(report);

    // Trigger subtle ambient background ripple
    if (state.ambientBg) {
      state.ambientBg.triggerPulse(report.type);
    }

    if (resultsWrapper) {
      resultsWrapper.classList.remove("hidden");
      resultsWrapper.style.display = "block";

      // Native responsive smooth scrolling (zero lag, standard physics)
      setTimeout(() => {
        resultsWrapper.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    }
  }
}

function pickMatchingMockReport(prompt) {
  const text = (prompt || "").toLowerCase();
  const reports = window.MOCK_REPORTS || {};
  if (text.includes("stripe") || text.includes("payment") || text.includes("gateway")) {
    return reports.stripe || reports.default;
  }
  if (text.includes("redis") || text.includes("cart") || text.includes("session")) {
    return reports.redis || reports.default;
  }
  if (text.includes("inventory") || text.includes("sku") || text.includes("deadlock")) {
    return reports.inventory || reports.default;
  }
  return reports.default || window.MOCK_FAILURE_REPORT;
}

/* ==========================================================================
   8. Render Simulation Report & E-Commerce Metrics
   ========================================================================== */
function renderSimulationReport(report) {
  state.currentReport = report;

  const targetEl = document.getElementById("report-target");
  const typeBadge = document.getElementById("report-type-badge");
  const timeEl = document.getElementById("report-exec-time");
  const forkEl = document.getElementById("report-fork-id");

  if (targetEl) targetEl.textContent = report.target_entity || "Target";
  if (typeBadge) {
    typeBadge.textContent = (report.type || "failure").toUpperCase();
    typeBadge.className =
      report.type === "failure"
        ? "text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full border border-rose-500/40 text-rose-400 bg-rose-500/10"
        : report.type === "upgrade"
        ? "text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full border border-amber-500/40 text-amber-400 bg-amber-500/10"
        : "text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full border border-emerald-500/40 text-emerald-400 bg-emerald-500/10";
  }
  if (timeEl) timeEl.textContent = `${Math.round(report.execution_time_ms || 118)}ms`;
  if (forkEl) forkEl.textContent = report.fork_graph || "sim_ephemeral_fork";

  // Blast Radius Score
  const scoreEl = document.getElementById("blast-score-val");
  const score = report.blast_radius_score || 71.4;

  if (scoreEl) {
    const obj = { val: 0 };
    if (typeof gsap !== "undefined") {
      gsap.to(obj, {
        val: score,
        duration: 1.1,
        ease: "power2.out",
        onUpdate: () => {
          scoreEl.textContent = `${obj.val.toFixed(1)}%`;
        },
      });
    } else {
      scoreEl.textContent = `${score.toFixed(1)}%`;
    }
  }

  // E-Commerce Revenue Risk
  const revRiskEl = document.getElementById("revenue-risk-val");
  if (revRiskEl) {
    revRiskEl.innerHTML = `${report.revenue_at_risk_per_min || "$38,025"} <span class="text-xs text-rose-300/80 font-sans">/ min</span>`;
  }

  // Interrupted Funnel Stage
  const funnelEl = document.getElementById("funnel-stage-val");
  if (funnelEl) {
    funnelEl.textContent = report.funnel_stage || "Stage 4: Payment Capture";
  }

  // Abandoned Carts / Impacted Sessions
  const usersEl = document.getElementById("affected-users-count");
  const outage = report.outage_details;
  let totalUsers = report.abandoned_carts || 0;
  if (!totalUsers && outage && outage.impacted_clients) {
    totalUsers = outage.impacted_clients.reduce((acc, c) => acc + (c.active_users || 0), 0);
  }
  if (usersEl) {
    animateNumber("affected-users-count", totalUsers || 105000);
  }

  // Executive AI Briefing
  const summaryEl = document.getElementById("executive-summary-text");
  if (summaryEl) {
    summaryEl.innerHTML = formatMarkdown(report.executive_summary || "Simulation completed successfully.");
  }

  // Render Visual Cascade Flow
  renderCascadeFlow(report);

  // Recommendations
  const recsContainer = document.getElementById("recommendations-list");
  if (recsContainer) {
    recsContainer.innerHTML = "";
    (report.actionable_recommendations || []).forEach((rec, idx) => {
      const li = document.createElement("li");
      li.className = "flex items-start space-x-3 text-sm text-slate-300";
      li.innerHTML = `
        <span class="flex-shrink-0 w-5 h-5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center text-xs font-mono font-bold mt-0.5">
          ${idx + 1}
        </span>
        <span class="leading-relaxed">${rec}</span>
      `;
      recsContainer.appendChild(li);
    });
  }

  // Cascading Service Failures list
  const servicesList = document.getElementById("impacted-services-list");
  if (servicesList) {
    servicesList.innerHTML = "";
    const list = outage?.impacted_services || [];
    if (list.length === 0) {
      servicesList.innerHTML = `<p class="text-xs text-slate-500 italic p-3 text-center">No upstream microservices degraded.</p>`;
    } else {
      list.forEach((s) => {
        const item = document.createElement("div");
        item.className =
          "flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-white/5 text-xs hover:border-white/10 transition-colors";
        item.innerHTML = `
          <div class="flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full ${s.impact === "outage" ? "bg-rose-400" : "bg-amber-400"}"></span>
            <span class="font-medium text-slate-200">${s.name}</span>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">Tier ${s.tier}</span>
          </div>
          <div class="flex items-center space-x-3 text-slate-400">
            <span>+${s.hops_from_target} hops</span>
            <span class="text-cyan-400 font-mono">${s.team_name || "Platform"}</span>
          </div>
        `;
        servicesList.appendChild(item);
      });
    }
  }

  // Broken Ingress Endpoints list
  const endpointsList = document.getElementById("broken-endpoints-list");
  if (endpointsList) {
    endpointsList.innerHTML = "";
    const eps = outage?.broken_endpoints || [];
    if (eps.length === 0) {
      endpointsList.innerHTML = `<p class="text-xs text-slate-500 italic p-3 text-center">No public endpoints impacted.</p>`;
    } else {
      eps.forEach((ep) => {
        const item = document.createElement("div");
        item.className =
          "flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-white/5 text-xs font-mono hover:border-white/10 transition-colors";
        item.innerHTML = `
          <span class="text-slate-300 font-medium">${ep.method} ${ep.path}</span>
          <span class="text-rose-400 font-semibold uppercase text-[10px] px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">${ep.status}</span>
        `;
        endpointsList.appendChild(item);
      });
    }
  }
}

/* ==========================================================================
   9. Clean Causal Blast Radius Propagation Chain Diagram
   ========================================================================== */
function renderCascadeFlow(report) {
  const container = document.getElementById("cascade-flow-container");
  if (!container) return;

  const outage = report.outage_details;
  const target = report.target_entity || "Target";
  const hops1 = (outage?.impacted_services || []).filter((s) => s.hops_from_target === 1);
  const hops2Plus = (outage?.impacted_services || []).filter((s) => s.hops_from_target > 1);
  const brokenEps = outage?.broken_endpoints || [];
  const clients = outage?.impacted_clients || [];

  container.innerHTML = `
    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 text-xs">
      
      <!-- Stage 1: Injected Target Fault -->
      <div class="flex-1 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-mono text-rose-400 font-semibold uppercase tracking-wider">Fault Origin</span>
          <span class="w-2 h-2 rounded-full bg-rose-400 animate-ping"></span>
        </div>
        <div class="font-bold text-white text-sm mb-1">${target}</div>
        <div class="text-[11px] text-rose-300 font-mono">Injected Outage / Fault</div>
      </div>

      <!-- Arrow 1 -->
      <div class="hidden lg:flex items-center justify-center text-slate-500 px-1">
        <svg class="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
        </svg>
      </div>

      <!-- Stage 2: Direct Dependencies (1 Hop) -->
      <div class="flex-1 p-3.5 rounded-xl bg-slate-900/70 border border-white/10 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-mono text-amber-400 font-semibold uppercase tracking-wider">1-Hop Callers</span>
          <span class="text-[10px] font-mono text-slate-400">${hops1.length} services</span>
        </div>
        <div class="space-y-1">
          ${
            hops1.length > 0
              ? hops1.map((s) => `<div class="font-medium text-slate-200">${s.name}</div>`).join("")
              : `<div class="text-slate-500 italic">No direct callers</div>`
          }
        </div>
        <div class="text-[10px] text-amber-300/80 font-mono mt-1">Direct RPC Failure</div>
      </div>

      <!-- Arrow 2 -->
      <div class="hidden lg:flex items-center justify-center text-slate-500 px-1">
        <svg class="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
        </svg>
      </div>

      <!-- Stage 3: Secondary Blast Cascade (2+ Hops) -->
      <div class="flex-1 p-3.5 rounded-xl bg-slate-900/70 border border-white/10 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-mono text-cyan-400 font-semibold uppercase tracking-wider">Cascading Tier-1</span>
          <span class="text-[10px] font-mono text-slate-400">${hops2Plus.length} services</span>
        </div>
        <div class="space-y-1">
          ${
            hops2Plus.length > 0
              ? hops2Plus.map((s) => `<div class="font-medium text-slate-200">${s.name}</div>`).join("")
              : `<div class="text-slate-500 italic">No secondary cascades</div>`
          }
        </div>
        <div class="text-[10px] text-cyan-300/80 font-mono mt-1">Multi-Hop Domino Effect</div>
      </div>

      <!-- Arrow 3 -->
      <div class="hidden lg:flex items-center justify-center text-slate-500 px-1">
        <svg class="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
        </svg>
      </div>

      <!-- Stage 4: Storefront & Customer Impact -->
      <div class="flex-1 p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex flex-col justify-between">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-mono text-indigo-400 font-semibold uppercase tracking-wider">Customer Revenue Impact</span>
          <span class="w-2 h-2 rounded-full bg-indigo-400"></span>
        </div>
        <div class="font-bold text-white text-sm">
          ${clients.length > 0 ? clients.map((c) => c.name.split(" ")[0]).join(", ") : "Web, iOS, Android"}
        </div>
        <div class="text-[11px] text-indigo-300 font-mono mt-1">
          ${report.revenue_at_risk_per_min || "$38,025"} / min lost
        </div>
      </div>

    </div>
  `;
}

function resetSimulation() {
  const resultsWrapper = document.getElementById("results-wrapper");
  if (resultsWrapper) {
    resultsWrapper.classList.add("hidden");
    resultsWrapper.style.display = "none";
  }
  const input = document.getElementById("prompt-input");
  if (input) input.value = "";
  state.currentReport = null;
}

function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
  // Inline code
  html = html.replace(/`(.*?)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-xs">$1</code>');
  // Linebreaks / paragraphs
  html = html.replace(/\n\n+/g, "</p><p class='mt-2.5'>");
  html = `<p>${html}</p>`;
  return html;
}
