document.addEventListener('DOMContentLoaded', () => {
  let currentDryRunResults = null;
  let activeFilter = 'ALL';
  let searchTerm = '';

  const rawInput = document.getElementById('rawInput');
  const lineCountBadge = document.getElementById('lineCountBadge');
  const validLineBadge = document.getElementById('validLineBadge');
  const btnDryRun = document.getElementById('btnDryRun');
  const btnLoadSample = document.getElementById('btnLoadSample');
  const btnClear = document.getElementById('btnClear');
  const btnUploadFile = document.getElementById('btnUploadFile');
  const fileInput = document.getElementById('fileInput');

  const resultsTableBody = document.getElementById('resultsTableBody');
  const tableSearchInput = document.getElementById('tableSearchInput');
  const statTotal = document.getElementById('statTotal');
  const statReady = document.getElementById('statReady');
  const statWarning = document.getElementById('statWarning');
  const statError = document.getElementById('statError');

  const dockTargetSummary = document.getElementById('dockTargetSummary');
  const chkSkipErrors = document.getElementById('chkSkipErrors');
  const chkAllowOverwrite = document.getElementById('chkAllowOverwrite');
  const btnExecuteTrigger = document.getElementById('btnExecuteTrigger');

  const executeConfirmModal = new bootstrap.Modal(document.getElementById('executeConfirmModal'));
  const executionResultModal = new bootstrap.Modal(document.getElementById('executionResultModal'));
  const historyModal = new bootstrap.Modal(document.getElementById('historyModal'));
  const btnConfirmExecute = document.getElementById('btnConfirmExecute');
  const btnViewHistory = document.getElementById('btnViewHistory');
  const historyListContainer = document.getElementById('historyListContainer');

  const SAMPLE_DATA = `# 형식: from-repo from-branch to-repo to-branch
backend/auth-service main backend/auth-service-v2 main
mobile/android-app release/2.4 mobile/android-app release/2.4
infra/k8s-manifests dev infra/k8s-manifests staging
# 아래는 주의/오류 시뮬레이션 데이터입니다
legacy/old-gateway main legacy/old-gateway overwrite-test
legacy/notfound-repo main infra/new-repo main
frontend/portal-web missing frontend/portal-web feature/new`;

  initBackendStatus();
  updateInputStats();

  rawInput.addEventListener('input', updateInputStats);

  btnLoadSample.addEventListener('click', () => {
    rawInput.value = SAMPLE_DATA;
    updateInputStats();
  });

  btnClear.addEventListener('click', () => {
    rawInput.value = '';
    updateInputStats();
    currentDryRunResults = null;
    statTotal.textContent = '0';
    statReady.textContent = '0';
    statWarning.textContent = '0';
    statError.textContent = '0';
    dockTargetSummary.textContent = '0개';
    btnExecuteTrigger.disabled = true;
    resultsTableBody.innerHTML = `
      <tr><td colspan="7">
        <div class="empty-state">
          <i class="bi bi-arrow-repeat"></i>
          <p>상단에 대상 목록을 입력한 뒤 <strong>Dry-Run 검증</strong> 버튼을 눌러주세요.</p>
        </div>
      </td></tr>`;
  });

  btnUploadFile.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      const reader = new FileReader();
      reader.onload = (ev) => { rawInput.value = ev.target.result; updateInputStats(); };
      reader.readAsText(e.target.files[0]);
    }
  });

  function updateInputStats() {
    const text = rawInput.value.trim();
    if (!text) {
      lineCountBadge.textContent = '0 lines';
      validLineBadge.textContent = '0개 항목 인식됨';
      btnDryRun.disabled = true;
      return;
    }
    const lines = text.split('\n');
    let validCount = 0, totalLines = 0;
    for (const line of lines) {
      const t = line.trim();
      if (!t || t.startsWith('#')) continue;
      totalLines++;
      if (t.split(/[\s,]+/).length === 4) validCount++;
    }
    lineCountBadge.textContent = `${lines.length} lines (${totalLines} active)`;
    validLineBadge.textContent = `${validCount}개 항목 인식됨`;
    btnDryRun.disabled = validCount === 0;
  }

  btnDryRun.addEventListener('click', async () => {
    const text = rawInput.value.trim();
    if (!text) return;
    btnDryRun.disabled = true;
    btnDryRun.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 검증 중...';
    try {
      const resp = await fetch('/api/dry-run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: text }),
      });
      if (!resp.ok) { const err = await resp.json(); throw new Error(err.detail || '검증 실패'); }
      currentDryRunResults = await resp.json();
      renderDryRunResults(currentDryRunResults);
    } catch (err) {
      alert('Dry-Run 오류: ' + err.message);
    } finally {
      btnDryRun.disabled = false;
      btnDryRun.innerHTML = '<i class="bi bi-play-fill"></i> Dry-Run 검증';
    }
  });

  function renderDryRunResults(data) {
    statTotal.textContent = data.total;
    statReady.textContent = data.summary.ready;
    statWarning.textContent = data.summary.warning;
    statError.textContent = data.summary.error;

    document.querySelectorAll('.kpi-chip').forEach(c => c.classList.remove('active'));
    document.querySelector('.kpi-chip[data-filter="ALL"]').classList.add('active');
    activeFilter = 'ALL';

    updateDockCount();
    renderTable();
  }

  function updateDockCount() {
    if (!currentDryRunResults) return;
    const count = currentDryRunResults.summary.ready + (chkAllowOverwrite.checked ? currentDryRunResults.summary.warning : 0);
    dockTargetSummary.textContent = `${count}개`;
    btnExecuteTrigger.disabled = count === 0;
  }

  document.querySelectorAll('.kpi-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.kpi-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeFilter = chip.dataset.filter;
      renderTable();
    });
  });

  tableSearchInput.addEventListener('input', (e) => { searchTerm = e.target.value.toLowerCase(); renderTable(); });
  chkAllowOverwrite.addEventListener('change', updateDockCount);

  function renderTable() {
    if (!currentDryRunResults || !currentDryRunResults.results) return;
    const filtered = currentDryRunResults.results.filter(item => {
      if (activeFilter !== 'ALL' && item.status !== activeFilter) return false;
      if (searchTerm) {
        return `${item.from_repo} ${item.from_branch} ${item.to_repo} ${item.to_branch} ${item.message}`.toLowerCase().includes(searchTerm);
      }
      return true;
    });
    resultsTableBody.innerHTML = '';
    if (filtered.length === 0) {
      resultsTableBody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><i class="bi bi-inbox"></i><p>조건에 맞는 항목이 없습니다.</p></div></td></tr>`;
      return;
    }
    filtered.forEach(item => {
      const tr = document.createElement('tr');
      let badge = '';
      if (item.status === 'READY') badge = '<span class="status-badge ready"><i class="bi bi-check-circle-fill"></i> Ready</span>';
      else if (item.status === 'WARNING') badge = '<span class="status-badge warn"><i class="bi bi-exclamation-triangle-fill"></i> Warning</span>';
      else badge = '<span class="status-badge err"><i class="bi bi-x-circle-fill"></i> Error</span>';
      tr.innerHTML = `
        <td class="text-muted text-center">${item.line_num || '-'}</td>
        <td>
          <span class="code-label">${esc(item.from_repo||'')}</span>
          <span class="code-label branch ms-1">${esc(item.from_branch||'')}</span>
        </td>
        <td class="text-center text-muted"><i class="bi bi-arrow-right"></i></td>
        <td>
          <span class="code-label">${esc(item.to_repo||'')}</span>
          <span class="code-label branch ms-1">${esc(item.to_branch||'')}</span>
        </td>
        <td><span class="action-label">${item.action||'SYNC'}</span></td>
        <td>${badge}</td>
        <td class="text-muted" style="font-size:12px;">${esc(item.message||'')}</td>
      `;
      resultsTableBody.appendChild(tr);
    });
  }

  btnExecuteTrigger.addEventListener('click', () => {
    if (!currentDryRunResults) return;
    document.getElementById('modalReadyCount').textContent = currentDryRunResults.summary.ready;
    document.getElementById('modalWarningCount').textContent = currentDryRunResults.summary.warning;
    document.getElementById('modalOverwriteWarning').style.display = currentDryRunResults.summary.warning > 0 ? 'block' : 'none';
    executeConfirmModal.show();
  });

  btnConfirmExecute.addEventListener('click', async () => {
    if (!currentDryRunResults) return;
    btnConfirmExecute.disabled = true;
    btnConfirmExecute.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 전송 중...';
    try {
      const resp = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: currentDryRunResults.results,
          options: { skip_errors: chkSkipErrors.checked, allow_overwrite: chkAllowOverwrite.checked },
        }),
      });
      if (!resp.ok) { const err = await resp.json(); throw new Error(err.detail || '실행 실패'); }
      const result = await resp.json();
      executeConfirmModal.hide();

      document.getElementById('execResultId').textContent = result.id;
      document.getElementById('execResultTimestamp').textContent = result.timestamp;
      document.getElementById('execResultExecutedCount').textContent = result.executed_items;
      document.getElementById('execResultStatus').textContent = result.status;
      const link = document.getElementById('execResultJenkinsLink');
      if (result.build_url) { link.href = result.build_url; link.style.display = 'inline-flex'; }
      else link.style.display = 'none';
      executionResultModal.show();
    } catch (err) { alert('실행 오류: ' + err.message); }
    finally {
      btnConfirmExecute.disabled = false;
      btnConfirmExecute.innerHTML = '<i class="bi bi-play-fill"></i> 실행 확인';
    }
  });

  btnViewHistory.addEventListener('click', async () => {
    historyModal.show();
    historyListContainer.innerHTML = '<div class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-1"></span> 로딩 중...</div>';
    try {
      const resp = await fetch('/api/history');
      const data = await resp.json();
      if (!data.history || data.history.length === 0) {
        historyListContainer.innerHTML = '<div class="text-center py-4 text-muted">아직 실행 이력이 없습니다.</div>';
        return;
      }
      historyListContainer.innerHTML = '';
      data.history.forEach(item => {
        const d = document.createElement('div');
        d.className = 'p-3 mb-2 bg-light rounded border';
        d.style.fontSize = '13px';
        d.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-1">
            <strong>${esc(item.job_name)} #${esc(String(item.build_number))}</strong>
            <span class="badge bg-success">${esc(item.status)}</span>
          </div>
          <div class="text-muted small mb-2">
            ${esc(item.timestamp)} · 실행: ${item.executed_items}건 · 제외: ${item.skipped_items}건
          </div>
          <div class="d-flex justify-content-between align-items-center">
            <span class="text-secondary small">${esc(item.note||'')}</span>
            <a href="${esc(item.build_url||'#')}" target="_blank" class="btn-app sm primary"><i class="bi bi-box-arrow-up-right"></i> Jenkins</a>
          </div>
        `;
        historyListContainer.appendChild(d);
      });
    } catch (err) {
      historyListContainer.innerHTML = `<div class="text-danger p-3">${esc(err.message)}</div>`;
    }
  });

  async function initBackendStatus() {
    try {
      const resp = await fetch('/api/jenkins/config');
      if (!resp.ok) return;
      const info = await resp.json();
      const jp = document.getElementById('jenkinsPill');
      const rp = document.getElementById('repoScopePill');
      if (jp && info.jenkins) jp.innerHTML = `<span class="status-dot"></span><span>Jenkins: ${info.jenkins.job_name}</span>`;
      if (rp) {
        if (info.repo_scope.configured) rp.innerHTML = '<span class="status-dot"></span><span>Backend: repo-scope</span>';
        else rp.innerHTML = '<span class="status-dot offline"></span><span>Backend: Simulator</span>';
      }
    } catch(e) {}
  }

  function esc(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  }
});
