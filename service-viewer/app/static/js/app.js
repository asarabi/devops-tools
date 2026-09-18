// Service Viewer Frontend Logic
let allServices = [];
let currentFilter = "all";
let currentSearch = "";
let activeLogService = null;
let logRefreshTimer = null;
let activeEditService = null;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadServices();
  // Periodic background refresh every 10 seconds
  setInterval(() => {
    if (!document.querySelector(".modal-overlay.show")) {
      loadServices(true);
    }
  }, 10000);
});

function initEventListeners() {
  // Global Refresh
  document.getElementById("btn-refresh").addEventListener("click", () => loadServices());

  // Search input
  document.getElementById("service-search").addEventListener("input", (e) => {
    currentSearch = e.target.value.toLowerCase().trim();
    renderServices();
  });

  // Filter pills
  document.querySelectorAll(".pill").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentFilter = pill.dataset.filter;
      renderServices();
    });
  });

  // KPI card clicks as filters
  document.querySelectorAll(".kpi-card").forEach(card => {
    card.addEventListener("click", () => {
      const filter = card.dataset.filter;
      const targetPill = document.querySelector(`.pill[data-filter="${filter}"]`);
      if (targetPill) targetPill.click();
    });
  });

  // Modal open: New Service
  document.getElementById("btn-new-service").addEventListener("click", () => {
    openModal("modal-new-service");
    updatePreview();
  });

  // Modal close buttons
  document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modalId = btn.dataset.close;
      closeModal(modalId);
    });
  });

  // Close modal on background click
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

  // Tab navigation in New Service Modal
  document.querySelectorAll(".tab-btn").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });

  // Preview form changes
  const previewInputs = ["svc-name", "svc-desc", "svc-exec", "svc-workdir", "svc-user", "svc-restart", "svc-env"];
  previewInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", debounce(updatePreview, 300));
  });

  document.getElementById("btn-refresh-preview").addEventListener("click", (e) => {
    e.preventDefault();
    updatePreview();
  });

  // Submit New Service
  document.getElementById("btn-submit-new-service").addEventListener("click", handleCreateService);

  // Log Modal controls
  document.getElementById("log-lines").addEventListener("change", () => {
    if (activeLogService) loadServiceLogs(activeLogService);
  });

  document.getElementById("btn-refresh-logs").addEventListener("click", () => {
    if (activeLogService) loadServiceLogs(activeLogService);
  });

  document.getElementById("btn-copy-logs").addEventListener("click", () => {
    const logText = document.getElementById("log-terminal").innerText;
    navigator.clipboard.writeText(logText).then(() => {
      showToast("로그가 클립보드에 복사되었습니다.", "success");
    });
  });

  document.getElementById("log-auto-refresh").addEventListener("change", (e) => {
    if (e.target.checked) {
      logRefreshTimer = setInterval(() => {
        if (activeLogService) loadServiceLogs(activeLogService, true);
      }, 3000);
    } else {
      clearInterval(logRefreshTimer);
      logRefreshTimer = null;
    }
  });

  // Save Unit File
  document.getElementById("btn-save-unit").addEventListener("click", handleSaveUnit);
}

// Fetch and render services
async function loadServices(silent = false) {
  const btnRefresh = document.getElementById("btn-refresh");
  if (!silent) btnRefresh.classList.add("btn-loading");

  try {
    const res = await fetch("/api/services");
    if (!res.ok) throw new Error("서비스 목록을 불러오지 못했습니다.");
    const data = await res.json();

    allServices = data.services || [];
    updateKPIs(data.stats || {});
    renderServices();
  } catch (err) {
    if (!silent) showToast(err.message, "error");
  } finally {
    btnRefresh.classList.remove("btn-loading");
  }
}

// Update KPI Header Numbers
function updateKPIs(stats) {
  document.getElementById("kpi-total").innerText = stats.total || 0;
  document.getElementById("kpi-running").innerText = stats.running || 0;
  document.getElementById("kpi-stopped").innerText = stats.stopped || 0;
  document.getElementById("kpi-failed").innerText = stats.failed || 0;
  document.getElementById("kpi-enabled").innerText = stats.enabled || 0;
}

// Render cards
function renderServices() {
  const grid = document.getElementById("services-grid");
  const emptyState = document.getElementById("empty-state");

  let filtered = allServices.filter(svc => {
    // Text search
    if (currentSearch) {
      const matchName = svc.name.toLowerCase().includes(currentSearch);
      const matchDesc = (svc.description || "").toLowerCase().includes(currentSearch);
      const matchCat = (svc.category || "").toLowerCase().includes(currentSearch);
      if (!matchName && !matchDesc && !matchCat) return false;
    }

    // Pill filter
    if (currentFilter === "running") return svc.is_running;
    if (currentFilter === "stopped") return !svc.is_running && !svc.is_failed;
    if (currentFilter === "failed") return svc.is_failed;
    if (currentFilter === "enabled") return svc.is_enabled;
    return true;
  });

  if (filtered.length === 0) {
    grid.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  grid.innerHTML = filtered.map(svc => createServiceCardHTML(svc)).join("");

  // Attach card event listeners
  attachCardEvents();
}

function createServiceCardHTML(svc) {
  const isRunning = svc.is_running;
  const isFailed = svc.is_failed;
  const cardClass = isRunning ? "running" : (isFailed ? "failed" : "stopped");
  
  let statusBadge = "";
  if (isRunning) {
    statusBadge = `<span class="status-badge active"><span class="status-pulse"></span> Running</span>`;
  } else if (isFailed) {
    statusBadge = `<span class="status-badge failed">Failed</span>`;
  } else {
    statusBadge = `<span class="status-badge inactive">Stopped</span>`;
  }

  const activeSince = svc.active_since ? formatDate(svc.active_since) : "-";
  const pidDisplay = svc.pid > 0 ? svc.pid : "-";
  const enableBtnLabel = svc.is_enabled ? "⚡ 자동실행 켬" : "⚪ 수동실행";
  const enableBtnClass = svc.is_enabled ? "btn-secondary" : "btn-ghost";

  return `
    <div class="service-card ${cardClass}" data-name="${svc.name}">
      <div class="card-header">
        <div class="service-title-area">
          <div class="service-name">
            <span>${escapeHTML(svc.name)}</span>
            <span class="category-tag">${escapeHTML(svc.category || "Custom")}</span>
          </div>
          <div class="service-desc">${escapeHTML(svc.description || "등록된 설명이 없습니다.")}</div>
        </div>
        ${statusBadge}
      </div>

      <div class="card-metrics">
        <div class="metric-item">
          <span class="metric-label">PID</span>
          <span class="metric-val font-mono">${pidDisplay}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">메모리</span>
          <span class="metric-val font-mono">${svc.memory_formatted}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">시작 시각</span>
          <span class="metric-val">${activeSince}</span>
        </div>
      </div>

      <div class="card-actions">
        <div class="action-group-left">
          ${isRunning ? `
            <button class="btn btn-sm btn-secondary btn-action" data-action="restart" data-name="${svc.name}" title="서비스 재시작">
              🔄 재시작
            </button>
            <button class="btn btn-sm btn-secondary btn-action" data-action="stop" data-name="${svc.name}" title="서비스 중지">
              ⏹️ 중지
            </button>
          ` : `
            <button class="btn btn-sm btn-primary btn-action" data-action="start" data-name="${svc.name}" title="서비스 시작">
              ▶️ 시작
            </button>
          `}
          <button class="btn btn-sm ${enableBtnClass} btn-toggle-enable" data-enabled="${svc.is_enabled}" data-name="${svc.name}" title="부팅 시 자동실행 설정 토글">
            ${enableBtnLabel}
          </button>
        </div>
        <div class="action-group-right">
          <button class="btn btn-sm btn-secondary btn-view-logs" data-name="${svc.name}" title="실시간 journalctl 로그 보기">
            📜 로그
          </button>
          <button class="btn btn-sm btn-secondary btn-edit-unit" data-name="${svc.name}" title="Unit 파일 직접 편집">
            ✏️ 편집
          </button>
          <button class="btn btn-sm btn-danger btn-delete-service" data-name="${svc.name}" title="서비스 삭제">
            🗑️
          </button>
        </div>
      </div>
    </div>
  `;
}

function attachCardEvents() {
  // Start / Stop / Restart actions
  document.querySelectorAll(".btn-action").forEach(btn => {
    btn.addEventListener("click", async () => {
      const name = btn.dataset.name;
      const action = btn.dataset.action;
      await controlService(name, action, btn);
    });
  });

  // Toggle enable/disable
  document.querySelectorAll(".btn-toggle-enable").forEach(btn => {
    btn.addEventListener("click", async () => {
      const name = btn.dataset.name;
      const isCurrentlyEnabled = btn.dataset.enabled === "true";
      const action = isCurrentlyEnabled ? "disable" : "enable";
      await controlService(name, action, btn);
    });
  });

  // Open Log Modal
  document.querySelectorAll(".btn-view-logs").forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.name;
      openLogModal(name);
    });
  });

  // Open Edit Unit Modal
  document.querySelectorAll(".btn-edit-unit").forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.name;
      openEditModal(name);
    });
  });

  // Delete Service
  document.querySelectorAll(".btn-delete-service").forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.name;
      confirmDeleteService(name);
    });
  });
}

// Service Action Handler
async function controlService(name, action, btnEl) {
  if (btnEl) btnEl.disabled = true;
  showToast(`${name} ${action} 요청 중...`, "info");

  try {
    const res = await fetch(`/api/services/${name}/${action}`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "작업에 실패했습니다.");

    showToast(`${name} ${action} 성공`, "success");
    await loadServices(true);
  } catch (err) {
    showToast(`오류: ${err.message}`, "error");
  } finally {
    if (btnEl) btnEl.disabled = false;
  }
}

// Open Logs Modal
function openLogModal(name) {
  activeLogService = name;
  document.getElementById("log-modal-title").innerText = `실시간 로그: ${name}`;
  document.getElementById("log-terminal").innerText = "로그를 불러오는 중입니다...";
  openModal("modal-logs");
  loadServiceLogs(name);
}

// Load Logs
async function loadServiceLogs(name, silent = false) {
  const lines = document.getElementById("log-lines").value;
  try {
    const res = await fetch(`/api/services/${name}/logs?lines=${lines}`);
    if (!res.ok) throw new Error("로그를 가져올 수 없습니다.");
    const data = await res.json();

    const terminal = document.getElementById("log-terminal");
    terminal.innerText = data.logs || "(로그 출력이 없습니다)";
    // Scroll to bottom
    terminal.scrollTop = terminal.scrollHeight;
  } catch (err) {
    if (!silent) showToast(err.message, "error");
  }
}

// Open Edit Unit Modal
async function openEditModal(name) {
  activeEditService = name;
  document.getElementById("edit-modal-title").innerText = `Unit 파일 편집: ${name}`;
  document.getElementById("edit-unit-path").innerText = `/etc/systemd/system/${name}`;
  const editor = document.getElementById("edit-unit-content");
  editor.value = "내용을 불러오는 중...";
  openModal("modal-edit-unit");

  try {
    const res = await fetch(`/api/services/${name}`);
    if (!res.ok) throw new Error("Unit 파일을 불러오지 못했습니다.");
    const data = await res.json();
    editor.value = data.unit_content || "";
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Save Unit File
async function handleSaveUnit() {
  if (!activeEditService) return;
  const content = document.getElementById("edit-unit-content").value;
  const restartAfter = document.getElementById("edit-restart-after").checked;
  const btn = document.getElementById("btn-save-unit");

  btn.disabled = true;
  try {
    const res = await fetch(`/api/services/${activeEditService}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, restart_after_save: restartAfter })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "저장에 실패했습니다.");

    showToast(`${activeEditService} 저장 및 적용 완료`, "success");
    closeModal("modal-edit-unit");
    loadServices(true);
  } catch (err) {
    showToast(`저장 오류: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
  }
}

// Confirm and Delete Service
async function confirmDeleteService(name) {
  if (!confirm(`정말로 서비스 '${name}'을(를) 삭제하시겠습니까?\n\n- 서비스가 중지 및 비활성화됩니다.\n- /etc/systemd/system/${name} 파일이 삭제됩니다.`)) {
    return;
  }

  showToast(`${name} 삭제 처리 중...`, "info");
  try {
    const res = await fetch(`/api/services/${name}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "삭제에 실패했습니다.");

    showToast(`${name} 삭제 완료`, "success");
    loadServices();
  } catch (err) {
    showToast(`삭제 오류: ${err.message}`, "error");
  }
}

// Update New Service Template Preview
async function updatePreview() {
  const name = document.getElementById("svc-name").value || "my-service";
  const desc = document.getElementById("svc-desc").value || "";
  const exec = document.getElementById("svc-exec").value || "/path/to/executable";
  const workdir = document.getElementById("svc-workdir").value || "";
  const user = document.getElementById("svc-user").value || "ck21im";
  const restart = document.getElementById("svc-restart").value || "always";
  const envRaw = document.getElementById("svc-env").value || "";
  const envs = envRaw.split(",").map(s => s.trim()).filter(Boolean);

  try {
    const res = await fetch("/api/services/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        description: desc,
        exec_start: exec,
        working_directory: workdir,
        user,
        restart,
        environment: envs
      })
    });
    if (res.ok) {
      const data = await res.json();
      document.getElementById("preview-content").innerText = data.content;
    }
  } catch (err) {
    // Ignore preview error
  }
}

// Create New Service
async function handleCreateService() {
  const isRawTab = document.getElementById("tab-raw").classList.contains("active");
  const btn = document.getElementById("btn-submit-new-service");

  let payload = {};

  if (isRawTab) {
    const name = document.getElementById("raw-svc-name").value.trim();
    const content = document.getElementById("raw-content").value.trim();
    const enableNow = document.getElementById("raw-enable-now").checked;

    if (!name || !content) {
      showToast("서비스 이름과 Unit 내용을 모두 입력하세요.", "error");
      return;
    }
    payload = {
      name,
      exec_start: "raw",
      raw_content: content,
      enable_now: enableNow,
      category: "Custom"
    };
  } else {
    const name = document.getElementById("svc-name").value.trim();
    const desc = document.getElementById("svc-desc").value.trim();
    const exec = document.getElementById("svc-exec").value.trim();
    const workdir = document.getElementById("svc-workdir").value.trim();
    const user = document.getElementById("svc-user").value.trim();
    const restart = document.getElementById("svc-restart").value;
    const envRaw = document.getElementById("svc-env").value.trim();
    const category = document.getElementById("svc-category").value.trim() || "Custom";
    const enableNow = document.getElementById("svc-enable-now").checked;

    if (!name || !exec) {
      showToast("서비스 이름과 실행 명령어(ExecStart)는 필수입니다.", "error");
      return;
    }

    const envs = envRaw ? envRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

    payload = {
      name,
      description: desc,
      exec_start: exec,
      working_directory: workdir,
      user,
      restart,
      environment: envs,
      category,
      enable_now: enableNow
    };
  }

  btn.disabled = true;
  showToast("서비스 등록 중...", "info");

  try {
    const res = await fetch("/api/services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "서비스 등록 실패");

    showToast("새 서비스가 성공적으로 등록되었습니다!", "success");
    closeModal("modal-new-service");
    loadServices();
  } catch (err) {
    showToast(`등록 실패: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
  }
}

// Modal Helpers
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("show");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("show");
  if (id === "modal-logs" && logRefreshTimer) {
    clearInterval(logRefreshTimer);
    logRefreshTimer = null;
    document.getElementById("log-auto-refresh").checked = false;
  }
}

// Toast Helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icon = type === "success" ? "✅" : (type === "error" ? "❌" : "ℹ️");
  toast.innerHTML = `<span>${icon}</span> <span>${escapeHTML(message)}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

// Date helper
function formatDate(dateStr) {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr.split(" ")[1] || dateStr;
    return d.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return dateStr;
  }
}

function escapeHTML(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
