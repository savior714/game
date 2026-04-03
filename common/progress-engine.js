(function (global) {
  function emptyStats(domainKeys) {
    const base = {};
    for (const key of domainKeys) {
      base[key] = { levels: {}, weaknesses: {} };
      for (let i = 0; i <= 6; i++) {
        base[key].levels[i] = { attempts: 0, correct: 0, totalTime: 0 };
      }
    }
    return base;
  }

  function loadStats(storageKey, domainKeys) {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        const base = emptyStats(domainKeys);
        for (const key of domainKeys) {
          if (parsed[key]) {
            if (parsed[key].levels) Object.assign(base[key].levels, parsed[key].levels);
            if (parsed[key].weaknesses) Object.assign(base[key].weaknesses, parsed[key].weaknesses);
          }
        }
        return base;
      }
    } catch (e) {}
    return emptyStats(domainKeys);
  }

  function saveStats(storageKey, stats) {
    stats._updated_at = Date.now();
    localStorage.setItem(storageKey, JSON.stringify(stats));
    if (window.SyncEngine) {
      window.SyncEngine.pushStats(storageKey, stats);
    }
  }

  function getBaseDiffLevel(stats, domainKey, minData, opts) {
    opts = opts || {};
    const UP_THRESHOLD = opts.upThreshold !== undefined ? opts.upThreshold : 0.9;
    const DOWN_THRESHOLD = opts.downThreshold !== undefined ? opts.downThreshold : 0.8;

    const domainStats = stats[domainKey];
    let baseLevel = 0;

    for (let i = 0; i < 6; i++) {
      const lv = domainStats.levels[i];
      const acc = lv.attempts > 0 ? lv.correct / lv.attempts : 0;
      
      // 히스테리시스: 다음 레벨 시도 기록이 있으면 '이미 도달'로 간주하여 완화 기준 적용, 
      // 기록이 없으면 첫 승급이므로 상향 기준 적용.
      const hasReachedNext = domainStats.levels[i + 1] && domainStats.levels[i + 1].attempts > 0;
      const threshold = hasReachedNext ? DOWN_THRESHOLD : UP_THRESHOLD;

      if (lv.attempts >= minData && acc >= threshold) {
        baseLevel = i + 1;
      } else {
        break;
      }
    }
    return baseLevel;
  }

  function getDifficultyLevel(stats, domainKey, minData, globalBoost, recentHistory, opts) {
    const flowBoost = getRecentFlowBoost(recentHistory);
    const base = getBaseDiffLevel(stats, domainKey, minData, opts) + globalBoost + flowBoost;
    const wrongs = recentHistory.filter((r) => r === false).length;
    const penalty = wrongs >= 2 ? 1 : 0;
    return Math.max(0, Math.min(6, base - penalty));
  }

  function getRecentFlowBoost(recentHistory) {
    if (!Array.isArray(recentHistory) || recentHistory.length === 0) return 0;
    const recent = recentHistory.slice(-5);
    const corrects = recent.filter((r) => r === true).length;
    if (corrects >= 5) return 2;
    if (corrects >= 3) return 1;
    return 0;
  }

  global.ProgressEngine = {
    emptyStats,
    loadStats,
    saveStats,
    getBaseDiffLevel,
    getDifficultyLevel,
  };
})(window);
