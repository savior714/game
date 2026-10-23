/**
 * @fileoverview 보호자 관리 — 보상 획득·사용 감사(Audit) 및 전체 초기화 컨트롤러
 *
 * 제공 기능:
 * 1. 무결성 검증 배너 & 현재 Epoch 기준점 시각 표시
 * 2. 항목별 수식 검증 카드(초기 0 + 누적 획득 − 누적 사용/교환 = 현재 보유량 일치 검증)
 * 3. 구분(획득/사용/교환/조정·초기화) · 항목 · 기간 · 키워드 실시간 필터링
 * 4. 초 단위 발생 시각, 전후 잔액(`변경 전 → 변경 후`), 상세 사유, 과목/출처, 화면, 기기, 영수증 ID 타임라인
 * 5. 중복 지급 방지 영수증(`claimed_receipts`) 조회
 * 6. JSON / CSV(UTF-8 BOM, 엑셀 호환) 감사 리포트 다운로드
 * 7. 보호자 메모 포함 전체 보상 0 초기화(`reset_epoch + 1`, 부속 세션·플래그 정리 및 클라우드 즉시 동기화)
 */
(function initGuardianAuditModule(global) {
  'use strict';

  const auditFilterState = {
    type: 'all',
    key: 'all',
    period: 'all',
    query: '',
  };

  function escHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getLedger() {
    return typeof RewardLedger !== 'undefined' && RewardLedger ? RewardLedger : null;
  }

  function readCanonicalRewardState() {
    const L = getLedger();
    let parsed = null;
    try {
      const raw = localStorage.getItem('study_rewards');
      if (raw) parsed = JSON.parse(raw);
    } catch (_e) {
      parsed = null;
    }
    if (L) {
      let base = parsed || {};
      try {
        const jRaw = localStorage.getItem('study_rewards_ledger_v1');
        if (jRaw) {
          const journal = JSON.parse(jRaw);
          if (journal && typeof journal === 'object' && Number(journal.v) === 1) {
            base = { ...base, reward_ledger: L.mergeLedgers(journal, base.reward_ledger) };
          }
        }
      } catch (_e) {}
      return L.normalizeState(base, { adoptFields: true });
    }
    return parsed || {
      gems: 0,
      youtube_minutes: 0,
      snacks: 0,
      marble_plays: 0,
      bubble_plays: 0,
      custom_inventory: {},
      shop_items: [],
    };
  }

  function computeSinceTimestamp(period) {
    const now = Date.now();
    if (period === 'today') {
      const d = new Date(now);
      d.setHours(0, 0, 0, 0);
      return d.getTime();
    }
    if (period === '7d') return now - 7 * 24 * 60 * 60 * 1000;
    if (period === '30d') return now - 30 * 24 * 60 * 60 * 1000;
    return 0;
  }

  function currentFilterPayload() {
    return {
      type: auditFilterState.type,
      key: auditFilterState.key,
      since: computeSinceTimestamp(auditFilterState.period),
      query: auditFilterState.query,
    };
  }

  function typeBadgeStyle(type) {
    if (type === 'grant') return 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40';
    if (type === 'consume') return 'bg-rose-500/20 text-rose-300 border-rose-400/40';
    if (type === 'exchange') return 'bg-violet-500/20 text-violet-300 border-violet-400/40';
    if (type === 'reset') return 'bg-sky-500/20 text-sky-300 border-sky-400/40';
    return 'bg-amber-500/20 text-amber-300 border-amber-400/40';
  }

  function pillClass(active) {
    return active
      ? 'px-3 py-1.5 rounded-lg text-xs font-black bg-[#d7ff00] text-black border border-[#d7ff00] cursor-pointer transition-all'
      : 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 text-slate-300 border border-white/10 hover:bg-white/10 cursor-pointer transition-all';
  }

  function formatPreviousBalancesSummary(prev) {
    if (!prev || typeof prev !== 'object') return '이전 잔액 없음 (0)';
    const parts = [];
    if (Number(prev.gems) > 0) parts.push(`💎 보석 ${prev.gems}개`);
    if (Number(prev.youtube_minutes) > 0) parts.push(`📺 자유시간 ${prev.youtube_minutes}분`);
    if (Number(prev.snacks) > 0) parts.push(`🍪 간식 ${prev.snacks}개`);
    if (Number(prev.marble_plays) > 0) parts.push(`🔮 마블 ${prev.marble_plays}회`);
    if (Number(prev.bubble_plays) > 0) parts.push(`🫧 버블 ${prev.bubble_plays}회`);
    if (prev.custom_inventory && typeof prev.custom_inventory === 'object') {
      for (const [id, cnt] of Object.entries(prev.custom_inventory)) {
        if (Number(cnt) > 0) parts.push(`🎁 ${id} ${cnt}개`);
      }
    }
    return parts.length > 0 ? `${parts.join(' · ')} → 0으로 정리됨` : '모든 항목 0 상태에서 새 기준점 시작';
  }

  function renderAuditPanel() {
    const container = document.getElementById('audit-panel-body');
    if (!container) return;
    const L = getLedger();
    if (!L || typeof L.auditReport !== 'function') {
      container.innerHTML = '<div class="text-sm text-rose-300 p-4">보상 감사 원장 모듈을 불러오지 못했습니다.</div>';
      return;
    }

    const rawStored = (() => {
      try {
        const s = localStorage.getItem('study_rewards');
        return s ? JSON.parse(s) : null;
      } catch (_e) {
        return null;
      }
    })();
    const canonical = readCanonicalRewardState();
    const stateToInspect = rawStored && L.getEpoch(rawStored) >= L.BASELINE_RESET_EPOCH ? rawStored : canonical;
    const report = L.auditReport(stateToInspect, currentFilterPayload());

    const resetTimeStr = report.resetAt > 0
      ? L.formatLocalTimestamp(report.resetAt)
      : '최초 감사 기준점 적용됨';

    const visibleSummaries = report.summaries.filter((s) => (
      s.key === 'gems'
      || s.key === 'youtube_minutes'
      || s.key === 'snacks'
      || s.expected > 0
      || s.actual > 0
      || s.eventCount > 0
      || L.isCustomKey(s.key)
    ));

    const summaryCardsHtml = visibleSummaries.map((item) => {
      const totalPlus = item.earned + item.exchangedIn + (item.adjusted > 0 ? item.adjusted : 0);
      const totalMinus = item.consumed + item.exchangedOut + (item.adjusted < 0 ? Math.abs(item.adjusted) : 0);
      return `
        <div class="bg-black/35 border ${item.matches ? 'border-white/10' : 'border-rose-500/50'} rounded-xl p-4 space-y-2">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-extrabold text-white truncate">${escHtml(item.label)}</span>
            <span class="text-[11px] px-2 py-0.5 rounded-full font-bold border ${
              item.matches
                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
            }">${item.matches ? '일치 ✓' : `불일치 (${item.actual} vs ${item.expected})`}</span>
          </div>
          <div class="text-2xl font-black font-mono text-[#d7ff00]">${item.actual}<span class="text-xs font-bold text-slate-400 ml-1">${escHtml(item.unit)}</span></div>
          <div class="grid grid-cols-3 gap-1.5 pt-2 border-t border-white/10 text-[11px]">
            <div>
              <div class="text-slate-400">총 획득(+)</div>
              <div class="font-mono font-bold text-emerald-300">+${totalPlus}${escHtml(item.unit)}</div>
            </div>
            <div>
              <div class="text-slate-400">총 사용(−)</div>
              <div class="font-mono font-bold text-rose-300">−${totalMinus}${escHtml(item.unit)}</div>
            </div>
            <div>
              <div class="text-slate-400">기록 건수</div>
              <div class="font-mono font-bold text-slate-200">${item.eventCount}건</div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    const entriesHtml = report.entries.length === 0
      ? `
        <div class="text-center py-10 px-4 bg-black/25 rounded-xl border border-white/10 space-y-2">
          <div class="text-3xl">🧾</div>
          <div class="text-sm font-bold text-white">조건에 해당하는 보상 획득·사용 내역이 없습니다</div>
          <p class="text-xs text-slate-400">초기화 이후 아이가 학습으로 보석·자유시간을 획득하거나 상점 교환·사용을 하면 정확한 시각(초 단위)과 사유가 즉시 기록됩니다.</p>
        </div>
      `
      : report.entries.map((entry) => {
        const timeStr = L.formatLocalTimestamp(entry.at);
        const isoStr = entry.at > 0 ? new Date(entry.at).toISOString() : '';
        if (entry.type === 'reset') {
          return `
            <div class="bg-sky-950/35 border border-sky-500/30 rounded-xl p-4 space-y-2">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded-md text-[11px] font-black border ${typeBadgeStyle('reset')}">초기화 기준점</span>
                  <span class="font-bold text-sm text-sky-200">${escHtml(entry.detail)}</span>
                </div>
                <span class="font-mono text-xs text-slate-300" title="${escHtml(isoStr)}">${escHtml(timeStr)}</span>
              </div>
              <div class="text-xs text-slate-300 bg-black/30 rounded-lg px-3 py-2 border border-white/5">
                정리 내역: <span class="font-semibold text-white">${escHtml(formatPreviousBalancesSummary(entry.previousBalances))}</span>
              </div>
              <div class="flex flex-wrap gap-2 text-[11px] text-slate-400 font-mono">
                <span>주체: ${escHtml(entry.sourceLabel || entry.actor || 'system')}</span>
                ${entry.surfaceLabel ? `<span>· 화면: ${escHtml(entry.surfaceLabel)}</span>` : ''}
                ${entry.client ? `<span>· 기기: ${escHtml(entry.client)}</span>` : ''}
              </div>
            </div>
          `;
        }

        const isPlus = entry.delta > 0;
        const deltaStr = `${isPlus ? '+' : '−'}${Math.abs(entry.delta)}${entry.unit}`;
        const deltaColor = isPlus ? 'text-emerald-300' : 'text-rose-300';
        const metaChips = [];
        if (entry.sourceLabel) metaChips.push(`출처: ${entry.sourceLabel}`);
        if (entry.surfaceLabel) metaChips.push(`화면: ${entry.surfaceLabel}`);
        if (entry.client) metaChips.push(`기기: ${entry.client}`);
        if (entry.reason) metaChips.push(`코드: ${entry.reason}`);
        if (entry.receipt) metaChips.push(`영수증: ${entry.receipt}`);

        return `
          <div class="bg-black/35 hover:bg-black/50 transition-colors border border-white/10 rounded-xl p-4 space-y-2">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div class="space-y-1 min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="px-2 py-0.5 rounded-md text-[11px] font-black border ${typeBadgeStyle(entry.type)}">${escHtml(entry.typeLabel)}</span>
                  <span class="text-sm font-extrabold text-white">${escHtml(entry.keyLabel)}</span>
                  <span class="font-mono text-sm font-black ${deltaColor}">${escHtml(deltaStr)}</span>
                  <span class="text-xs font-mono text-slate-300 bg-white/5 px-2 py-0.5 rounded border border-white/10">
                    잔액 ${entry.balanceBefore}${escHtml(entry.unit)} → <strong class="text-white">${entry.balanceAfter}${escHtml(entry.unit)}</strong>
                  </span>
                </div>
                <p class="text-xs text-slate-200 font-medium break-words">${escHtml(entry.detail)}</p>
              </div>
              <div class="text-right shrink-0">
                <div class="font-mono text-xs font-bold text-slate-200" title="${escHtml(isoStr)}">${escHtml(timeStr)}</div>
              </div>
            </div>
            <div class="flex flex-wrap gap-x-3 gap-y-1 pt-1 border-t border-white/5 text-[11px] text-slate-400 font-mono">
              ${metaChips.map((chip) => `<span>${escHtml(chip)}</span>`).join('')}
            </div>
          </div>
        `;
      }).join('');

    const receiptsHtml = report.receipts.length === 0
      ? '<p class="text-xs text-slate-500 italic py-2">현재 Epoch에서 발급된 일회성 보상 영수증이 아직 없습니다.</p>'
      : report.receipts.slice(0, 30).map((r) => {
        const grantsText = Array.isArray(r.grants)
          ? r.grants.map((g) => `${g.type} +${g.amount}`).join(', ')
          : '';
        return `
          <div class="flex flex-wrap items-center justify-between gap-2 bg-black/30 px-3 py-2 rounded-lg border border-white/5 text-xs">
            <div class="min-w-0 flex-1">
              <div class="font-mono text-slate-200 truncate">${escHtml(r.receiptId)}</div>
              ${r.detail ? `<div class="text-[11px] text-slate-400 truncate">${escHtml(r.detail)}</div>` : ''}
            </div>
            <div class="text-right font-mono shrink-0">
              <span class="text-emerald-300 font-bold">${escHtml(grantsText)}</span>
              <span class="text-slate-400 ml-2">${escHtml(L.formatLocalTimestamp(r.grantedAt))}</span>
            </div>
          </div>
        `;
      }).join('');

    container.innerHTML = `
      <!-- 1. 무결성 검증 & 기준점 배너 -->
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-6 shadow-2xl border ${report.ok ? 'border-emerald-500/30' : 'border-rose-500/40'} mb-6 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="px-2.5 py-1 rounded-full text-xs font-black border ${
                report.ok
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
              }">
                ${report.ok ? '✅ 원장 무결성 검증 통과 (합계 100% 일치)' : '⚠️ 원장 잔액 불일치 감지'}
              </span>
              <span class="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-white/10 text-[#d7ff00] border border-[#d7ff00]/30">
                Epoch #${report.epoch}
              </span>
            </div>
            <p class="text-xs text-slate-300 pt-1">
              기준 시각: <span class="font-mono font-semibold text-white">${escHtml(resetTimeStr)}</span>
              · 기록된 원장 이벤트 <span class="font-mono font-bold text-[#d7ff00]">${report.totalEvents}건</span>
              ${report.foldedCount > 0 ? ` (압축 보관 ${report.foldedCount}건 포함)` : ''}
            </p>
          </div>
          <div class="flex flex-wrap gap-2 shrink-0">
            <button type="button" data-action="export-audit-csv" class="px-3.5 py-2 rounded-xl text-xs font-bold bg-white/10 hover:bg-white/20 text-white border border-white/15 cursor-pointer transition-all">
              📥 CSV 내보내기
            </button>
            <button type="button" data-action="export-audit-json" class="px-3.5 py-2 rounded-xl text-xs font-bold bg-white/10 hover:bg-white/20 text-white border border-white/15 cursor-pointer transition-all">
              📥 JSON 내보내기
            </button>
            <button type="button" data-action="open-reward-reset-modal" class="px-3.5 py-2 rounded-xl text-xs font-black bg-rose-500/20 hover:bg-rose-500/35 text-rose-200 border border-rose-400/40 cursor-pointer transition-all">
              🔄 모든 보상 초기화
            </button>
          </div>
        </div>

        <!-- 항목별 수식 검증 카드 -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          ${summaryCardsHtml}
        </div>
      </div>

      <!-- 2. 필터 & 시간순 감사 타임라인 -->
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-6 shadow-2xl border border-white/10 mb-6 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h4 class="text-sm font-extrabold text-white flex items-center gap-2">
            <span>🕒</span> 시간순 획득·사용 상세 감사 로그
          </h4>
          <span class="text-xs font-mono text-slate-400">조회 결과 ${report.entries.length}건</span>
        </div>

        <!-- 구분 필터 -->
        <div class="space-y-2.5 bg-white/5 p-3.5 rounded-xl border border-white/10">
          <div class="flex flex-wrap gap-1.5" role="group" aria-label="감사 구분 필터">
            <button type="button" data-action="audit-filter-type" data-filter-value="all" class="${pillClass(auditFilterState.type === 'all')}">전체 구분</button>
            <button type="button" data-action="audit-filter-type" data-filter-value="grant" class="${pillClass(auditFilterState.type === 'grant')}">🟢 획득 (+)</button>
            <button type="button" data-action="audit-filter-type" data-filter-value="consume" class="${pillClass(auditFilterState.type === 'consume')}">🔴 사용 (−)</button>
            <button type="button" data-action="audit-filter-type" data-filter-value="exchange" class="${pillClass(auditFilterState.type === 'exchange')}">🟣 상점 교환</button>
            <button type="button" data-action="audit-filter-type" data-filter-value="system" class="${pillClass(auditFilterState.type === 'system')}">🔵 초기화·조정</button>
          </div>
          <div class="flex flex-wrap gap-1.5" role="group" aria-label="보상 항목 필터">
            <button type="button" data-action="audit-filter-key" data-filter-value="all" class="${pillClass(auditFilterState.key === 'all')}">전체 항목</button>
            <button type="button" data-action="audit-filter-key" data-filter-value="gems" class="${pillClass(auditFilterState.key === 'gems')}">💎 보석</button>
            <button type="button" data-action="audit-filter-key" data-filter-value="youtube_minutes" class="${pillClass(auditFilterState.key === 'youtube_minutes')}">📺 자유시간</button>
            <button type="button" data-action="audit-filter-key" data-filter-value="snacks" class="${pillClass(auditFilterState.key === 'snacks')}">🍪 간식</button>
            <button type="button" data-action="audit-filter-key" data-filter-value="custom" class="${pillClass(auditFilterState.key === 'custom')}">🎁 커스텀 보상</button>
          </div>
          <div class="flex flex-col sm:flex-row gap-2 pt-1">
            <div class="flex flex-wrap gap-1.5 shrink-0" role="group" aria-label="조회 기간 필터">
              <button type="button" data-action="audit-filter-period" data-filter-value="all" class="${pillClass(auditFilterState.period === 'all')}">전체 기간</button>
              <button type="button" data-action="audit-filter-period" data-filter-value="today" class="${pillClass(auditFilterState.period === 'today')}">오늘</button>
              <button type="button" data-action="audit-filter-period" data-filter-value="7d" class="${pillClass(auditFilterState.period === '7d')}">최근 7일</button>
              <button type="button" data-action="audit-filter-period" data-filter-value="30d" class="${pillClass(auditFilterState.period === '30d')}">최근 30일</button>
            </div>
            <input
              type="search"
              id="audit-search-input"
              value="${escHtml(auditFilterState.query)}"
              placeholder="사유·과목·기기·영수증 ID 검색..."
              class="flex-1 px-3 py-1.5 rounded-lg bg-black/50 border border-white/15 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#d7ff00]"
            >
          </div>
        </div>

        <!-- 타임라인 목록 -->
        <div class="space-y-2.5 max-h-[560px] overflow-y-auto pr-1" id="audit-timeline-list">
          ${entriesHtml}
        </div>
      </div>

      <!-- 3. 중복 방지 영수증 원장 -->
      <div class="bg-[#0e1422]/90 backdrop-blur-xl rounded-2xl p-6 shadow-2xl border border-white/10 mb-6 space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="text-sm font-extrabold text-white flex items-center gap-2">
            <span>🔐</span> 지급 완료 영수증 목록 (중복 지급 차단 증적)
          </h4>
          <span class="text-xs font-mono text-slate-400">${report.receipts.length}건</span>
        </div>
        <div class="space-y-1.5 max-h-60 overflow-y-auto">
          ${receiptsHtml}
        </div>
      </div>
    `;
  }

  function showAuditTab() {
    const hideIds = [
      'math-progress-snapshot-section',
      'math-daily-goal-presets-section',
      'difficulty-control-panel',
      'preview-section',
      'weekly-words-section',
      'reward-custom-section',
    ];
    for (const id of hideIds) {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    }
    const growthPanel = document.getElementById('growth-panel');
    if (growthPanel) growthPanel.classList.add('hidden');
    const backupSection = document.getElementById('local-backup-section');
    if (backupSection) backupSection.style.display = 'block';
    const auditPanel = document.getElementById('audit-panel');
    if (auditPanel) auditPanel.classList.remove('hidden');

    document.querySelectorAll('.tab-btn').forEach((b) => {
      b.classList.remove('active-tab');
      b.classList.add('inactive-tab');
    });
    const tabAudit = document.getElementById('tab-audit');
    if (tabAudit) {
      tabAudit.classList.remove('inactive-tab');
      tabAudit.classList.add('active-tab');
    }

    renderAuditPanel();
  }

  function setAuditFilter(kind, value) {
    if (!value) return;
    if (kind === 'type') auditFilterState.type = value;
    else if (kind === 'key') auditFilterState.key = value;
    else if (kind === 'period') auditFilterState.period = value;
    renderAuditPanel();
  }

  function onAuditSearchInput(value) {
    const nextVal = String(value || '');
    auditFilterState.query = nextVal;
    renderAuditPanel();
    const input = document.getElementById('audit-search-input');
    if (input) {
      input.focus();
      try {
        input.setSelectionRange(nextVal.length, nextVal.length);
      } catch (_e) {}
    }
  }

  function triggerFileDownload(filename, mimeType, content) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function exportAuditCsv() {
    const L = getLedger();
    if (!L) return;
    const state = readCanonicalRewardState();
    const csv = '\uFEFF' + L.auditCsv(state, currentFilterPayload());
    const dateStr = new Date().toISOString().slice(0, 10);
    triggerFileDownload(`aidengame-reward-audit-${dateStr}.csv`, 'text/csv;charset=utf-8;', csv);
  }

  function exportAuditJson() {
    const L = getLedger();
    if (!L) return;
    const state = readCanonicalRewardState();
    const report = L.auditReport(state, currentFilterPayload());
    const bundle = {
      format: 'aidengame-reward-audit-report',
      exportedAt: new Date().toISOString(),
      filter: currentFilterPayload(),
      report,
      rawLedger: state.reward_ledger,
    };
    const dateStr = new Date().toISOString().slice(0, 10);
    triggerFileDownload(
      `aidengame-reward-audit-${dateStr}.json`,
      'application/json;charset=utf-8;',
      JSON.stringify(bundle, null, 2)
    );
  }

  function purgeGuardianCompanionStores(targetEpoch, nowTs) {
    const d = new Date(nowTs);
    const pad = (n) => String(n).padStart(2, '0');
    const dateKey = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    const pushOrQueue = (k, val) => {
      localStorage.setItem(k, JSON.stringify(val));
      if (global.SyncEngine && typeof global.SyncEngine.pushStats === 'function') {
        global.SyncEngine.pushStats(k, val);
      } else {
        try {
          const q = JSON.parse(localStorage.getItem('sync_queue') || '{}') || {};
          q[k] = { ...val, _updated_at: nowTs };
          localStorage.setItem('sync_queue', JSON.stringify(q));
        } catch (_e) {}
      }
    };

    pushOrQueue('study_youtube_free_time_session_v1', {
      schemaVersion: 1,
      status: 'inactive',
      sessionId: null,
      resetEpoch: targetEpoch,
      resetAt: nowTs,
    });
    pushOrQueue('study_youtube_free_time_daily_usage_v1', {
      schemaVersion: 1,
      dateKey,
      morningMinutes: 0,
      afternoonMinutes: 0,
      resetEpoch: targetEpoch,
    });

    try { localStorage.removeItem('study_youtube_free_time_start_tx_v1'); } catch (_e) {}

    const receiptKeys = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.startsWith('aiden_receipt_')) receiptKeys.push(k);
    }
    for (const rk of receiptKeys) {
      try { localStorage.removeItem(rk); } catch (_e) {}
    }

    const resetJsonKey = (key, transform) => {
      try {
        const raw = localStorage.getItem(key);
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          pushOrQueue(key, transform(parsed));
        }
      } catch (_e) {}
    };

    resetJsonKey('aiden_math_daily_goal_v1', (g) => ({
      ...g,
      currentCount: 0,
      completed: false,
      completedAt: null,
      rewardGranted: false,
      resetEpoch: targetEpoch,
      lastUpdated: new Date(nowTs).toISOString(),
    }));
    resetJsonKey('aiden_daily_streak', (s) => ({
      ...s,
      todayRecorded: false,
      gemAwarded: {},
      resetEpoch: targetEpoch,
    }));
    resetJsonKey('aiden_diversity', (v) => ({
      ...v,
      subjectsWithCorrect: [],
      gemAwarded: false,
      resetEpoch: targetEpoch,
    }));
    resetJsonKey('aiden_milestones', (m) => ({
      ...m,
      achieved: {},
      session: { rocketStreak: 0, milestoneStreak: 0, sessionCorrect: 0 },
      resetEpoch: targetEpoch,
    }));
  }

  function openRewardResetModal() {
    const modal = document.getElementById('reward-reset-modal');
    if (!modal) return;
    const summaryEl = document.getElementById('reward-reset-modal-summary');
    const noteInput = document.getElementById('reward-reset-note-input');
    const state = readCanonicalRewardState();
    if (noteInput) noteInput.value = '';
    if (summaryEl) {
      const customCount = Object.values(state.custom_inventory || {}).reduce((acc, n) => acc + (Number(n) || 0), 0);
      summaryEl.innerHTML = `
        <div class="flex justify-between"><span>현재 보유 보석:</span><span class="font-bold text-white">💎 ${state.gems}개 → 0개</span></div>
        <div class="flex justify-between"><span>현재 자유시간:</span><span class="font-bold text-white">📺 ${state.youtube_minutes}분 → 0분</span></div>
        <div class="flex justify-between"><span>현재 간식:</span><span class="font-bold text-white">🍪 ${state.snacks}개 → 0개</span></div>
        <div class="flex justify-between"><span>커스텀 보상 합계:</span><span class="font-bold text-white">🎁 ${customCount}개 → 0개</span></div>
      `;
    }
    modal.classList.remove('hidden');
  }

  function cancelRewardReset() {
    const modal = document.getElementById('reward-reset-modal');
    if (modal) modal.classList.add('hidden');
  }

  function confirmRewardReset() {
    const L = getLedger();
    if (!L || typeof L.resetState !== 'function') return;
    const noteInput = document.getElementById('reward-reset-note-input');
    const customNote = noteInput && noteInput.value.trim()
      ? noteInput.value.trim()
      : '보호자 수동 전체 보상 초기화';
    const nowTs = Date.now();
    const current = readCanonicalRewardState();
    const nextState = L.resetState(current, {
      at: nowTs,
      reason: 'guardian_manual_reset',
      actor: 'guardian',
      surface: 'guardian',
      note: customNote,
    });
    nextState.last_updated = new Date(nowTs).toISOString();
    nextState._updated_at = nowTs;

    localStorage.setItem('study_rewards', JSON.stringify(nextState));
    try {
      localStorage.setItem('study_rewards_ledger_v1', JSON.stringify(nextState.reward_ledger));
    } catch (_e) {}

    purgeGuardianCompanionStores(nextState.reward_ledger.reset_epoch, nowTs);

    if (global.SyncEngine && typeof global.SyncEngine.pushStats === 'function') {
      global.SyncEngine.pushStats('study_rewards', nextState);
    } else {
      try {
        const q = JSON.parse(localStorage.getItem('sync_queue') || '{}') || {};
        q.study_rewards = nextState;
        localStorage.setItem('sync_queue', JSON.stringify(q));
      } catch (_e) {}
    }

    if (global.RewardSystem && typeof global.RewardSystem.init === 'function') {
      global.RewardSystem.init();
    }
    if (global.DailyStreak && typeof global.DailyStreak.reload === 'function') {
      global.DailyStreak.reload();
    }
    if (global.DiversityReward && typeof global.DiversityReward.reload === 'function') {
      global.DiversityReward.reload();
    }
    if (global.MilestoneTracker && typeof global.MilestoneTracker.reload === 'function') {
      global.MilestoneTracker.reload();
    }
    if (typeof global.loadRewards === 'function') {
      global.loadRewards();
    }
    cancelRewardReset();
    renderAuditPanel();
  }

  function checkInitialAuditRoute() {
    try {
      const hash = String(global.location?.hash || '');
      const params = new URLSearchParams(global.location?.search || '');
      if (hash === '#audit' || params.get('tab') === 'audit') {
        showAuditTab();
      }
    } catch (_e) {}
  }

  global.showAuditTab = showAuditTab;
  global.renderAuditPanel = renderAuditPanel;
  global.setAuditFilter = setAuditFilter;
  global.onAuditSearchInput = onAuditSearchInput;
  global.exportAuditCsv = exportAuditCsv;
  global.exportAuditJson = exportAuditJson;
  global.openRewardResetModal = openRewardResetModal;
  global.cancelRewardReset = cancelRewardReset;
  global.confirmRewardReset = confirmRewardReset;

  global.addEventListener('storage', (e) => {
    if (!e || !e.key || e.key === 'study_rewards' || e.key === 'study_rewards_ledger_v1') {
      const panel = document.getElementById('audit-panel');
      if (panel && !panel.classList.contains('hidden')) renderAuditPanel();
    }
  });
  global.addEventListener('cloud-sync-complete', () => {
    const panel = document.getElementById('audit-panel');
    if (panel && !panel.classList.contains('hidden')) renderAuditPanel();
  });
  global.addEventListener('hashchange', checkInitialAuditRoute);

  if (global.document && global.document.readyState === 'loading') {
    global.document.addEventListener('DOMContentLoaded', checkInitialAuditRoute);
  } else {
    setTimeout(checkInitialAuditRoute, 0);
  }
})(window);
