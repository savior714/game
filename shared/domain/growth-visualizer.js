/**
 * @fileoverview 성장 시각화 모듈 — 난이도토스트 / 주간요약 / 숙련도바
 * @module growth-visualizer
 */

const GrowthVisualizer = (() => {
  const SESSION_LOG_KEY = 'aiden_session_log';

  const DIFF_LABELS = ['입문', '기초', '중급', '숙련', '마스터', '초월', '전설'];

  const SUBJECT_DOMAIN_KEYS = {
    math: ['+', '-', '\xD7'],
    english: null,
    korean: ['spelling', 'antonym', 'honorific'],
    science: ['biology', 'earth', 'physics'],
  };

  let state;

  function getDefaultState() {
    return {
      levelUpShown: false,
      lastLevelUpSubject: null,
    };
  }

  function load() {
    const saved = localStorage.getItem('aiden_growth_state');
    if (saved) {
      try {
        state = { ...getDefaultState(), ...JSON.parse(saved) };
        return;
      } catch (e) {
        console.error('[GrowthVisualizer] Failed to load state:', e);
      }
    }
    state = getDefaultState();
  }

  function save() {
    localStorage.setItem('aiden_growth_state', JSON.stringify(state));
  }

  function showToast(message) {
    if (typeof RewardSystemUI !== 'undefined' && typeof RewardSystemUI.showToast === 'function') {
      RewardSystemUI.showToast(message);
    }
  }

  function registerDomainKeys(subject, domainKeys) {
    SUBJECT_DOMAIN_KEYS[subject] = domainKeys;
  }

  function checkLevelUp(subject, oldLevel, newLevel) {
    if (newLevel > oldLevel && !state.levelUpShown) {
      const oldLabel = DIFF_LABELS[oldLevel] || `Lv.${oldLevel}`;
      const newLabel = DIFF_LABELS[newLevel] || `Lv.${newLevel}`;
      const message = `${subject} ${oldLabel} → ${newLabel} 난이도 상승! 🎉`;
      showToast(message);
      state.levelUpShown = true;
      state.lastLevelUpSubject = subject;
      save();
    }
  }

  function resetLevelUpFlag() {
    state.levelUpShown = false;
    save();
  }

  function calculateProficiency(subject, stats, domainKeys) {
    let totalAttempts = 0;
    let totalCorrect = 0;

    const keys = domainKeys || SUBJECT_DOMAIN_KEYS[subject] || [];
    for (const domain of keys) {
      if (!stats[domain]) continue;
      const levels = stats[domain].levels;
      if (!levels) continue;
      for (const level of Object.values(levels)) {
        totalAttempts += level.attempts || 0;
        totalCorrect += level.correct || 0;
      }
    }

    if (totalAttempts === 0) return 0;
    return Math.round((totalCorrect / totalAttempts) * 100);
  }

  function showProficiencyBar(subject, stats, domainKeys) {
    const proficiency = calculateProficiency(subject, stats, domainKeys);

    let container = document.getElementById('proficiency-bar-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'proficiency-bar-container';
      container.className = 'proficiency-bar-container';
      const qCount = document.getElementById('q-count');
      if (qCount) {
        qCount.parentNode.insertBefore(container, qCount.nextSibling);
      } else {
        const gameArea = document.getElementById('game-area');
        if (gameArea) {
          gameArea.insertBefore(container, gameArea.firstChild);
        }
      }
    }

    const barFill = document.createElement('div');
    barFill.className = 'proficiency-bar-fill';
    const colors = ['#aed581', '#66bb6a', '#4fc3f7', '#29b6f6', '#ffca28', '#ab47bc', '#ef5350'];
    const level = Math.min(6, Math.floor(proficiency / 15));
    barFill.style.width = proficiency + '%';
    barFill.style.background = colors[level] || '#aed581';

    container.innerHTML = '';
    container.appendChild(barFill);

    const label = document.createElement('span');
    label.className = 'proficiency-label';
    label.textContent = `🎯 ${proficiency}%`;
    label.style.cssText = 'position:absolute;right:8px;top:-2px;font-size:0.75rem;font-weight:bold;color:#64748b;';
    container.style.position = 'relative';
    container.appendChild(label);

    container.style.display = 'block';
  }

  function loadSessionLog() {
    const saved = localStorage.getItem(SESSION_LOG_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('[GrowthVisualizer] Failed to load session log:', e);
      }
    }
    return {};
  }

  function saveSessionLog(log) {
    localStorage.setItem(SESSION_LOG_KEY, JSON.stringify(log));
  }

  function recordSessionEnd(subject, stats, domainKeys) {
    const log = loadSessionLog();
    const today = getTodayKey();

    if (!log[today]) log[today] = [];

    const keys = domainKeys || SUBJECT_DOMAIN_KEYS[subject] || [];
    for (const domain of keys) {
      if (!stats[domain]) continue;
      const levels = stats[domain].levels;
      if (!levels) continue;

      let domainCorrect = 0;
      let domainTotal = 0;
      for (const level of Object.values(levels)) {
        domainCorrect += level.correct || 0;
        domainTotal += level.attempts || 0;
      }

      if (domainTotal > 0) {
        log[today].push({
          time: new Date().toISOString(),
          subject,
          domain,
          correct: domainCorrect,
          total: domainTotal,
        });
      }
    }

    const dates = Object.keys(log).sort();
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 90);
    const cutoffKey = getTodayKeyFrom(cutoff);

    for (const date of dates) {
      if (date < cutoffKey) delete log[date];
    }

    saveSessionLog(log);
  }

  function getTodayKey() {
    return new Date().toISOString().split('T')[0];
  }

  function getTodayKeyFrom(date) {
    return date.toISOString().split('T')[0];
  }

  function getWeeklySummary() {
    const log = loadSessionLog();
    const subjects = ['math', 'english', 'korean', 'science'];

    const now = new Date();
    now.setHours(23, 59, 59, 999);
    const thisWeekStart = new Date(now);
    thisWeekStart.setDate(now.getDate() - now.getDay());
    thisWeekStart.setHours(0, 0, 0, 0);

    const lastWeekStart = new Date(thisWeekStart);
    lastWeekStart.setDate(thisWeekStart.getDate() - 7);

    const summary = {};
    for (const subject of subjects) {
      const allSessions = [];
      for (const date of Object.keys(log)) {
        for (const entry of log[date]) {
          if (entry.subject === subject) {
            allSessions.push(entry);
          }
        }
      }

      const thisWeekSessions = allSessions.filter(entry => {
        const d = new Date(entry.time);
        return d >= thisWeekStart && d <= now;
      });

      const lastWeekSessions = allSessions.filter(entry => {
        const d = new Date(entry.time);
        return d >= lastWeekStart && d < thisWeekStart;
      });

      const thisWeekCorrect = thisWeekSessions.reduce((s, e) => s + e.correct, 0);
      const thisWeekTotal = thisWeekSessions.reduce((s, e) => s + e.total, 0);
      const lastWeekCorrect = lastWeekSessions.reduce((s, e) => s + e.correct, 0);
      const lastWeekTotal = lastWeekSessions.reduce((s, e) => s + e.total, 0);

      summary[subject] = {
        thisWeekSessions: thisWeekSessions.length,
        lastWeekSessions: lastWeekSessions.length,
        sessionChange: thisWeekSessions.length - lastWeekSessions.length,
        thisWeekCorrect,
        thisWeekTotal,
        lastWeekCorrect,
        lastWeekTotal,
        correctChange: thisWeekCorrect - lastWeekCorrect,
        avgAccuracy: thisWeekTotal > 0 ? Math.round((thisWeekCorrect / thisWeekTotal) * 100) : 0,
      };
    }

    return summary;
  }

  load();

  return {
    registerDomainKeys,
    checkLevelUp,
    resetLevelUpFlag,
    showProficiencyBar,
    calculateProficiency,
    recordSessionEnd,
    getWeeklySummary,
  };
})();
