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

  function getBaseDiffLevel(stats, domainKey, minData) {
    const domainStats = stats[domainKey];
    let baseLevel = 0;
    for (let i = 0; i < 6; i++) {
      const lv = domainStats.levels[i];
      const acc = lv.attempts > 0 ? lv.correct / lv.attempts : 0;
      if (lv.attempts >= minData && acc >= 0.9) baseLevel = i + 1;
      else break;
    }
    return baseLevel;
  }

  function getDifficultyLevel(stats, domainKey, minData, globalBoost, recentHistory) {
    const base = getBaseDiffLevel(stats, domainKey, minData) + globalBoost;
    const wrongs = recentHistory.filter((r) => r === false).length;
    const penalty = wrongs >= 2 ? 1 : 0;
    return Math.max(0, Math.min(6, base - penalty));
  }

  global.ProgressEngine = {
    emptyStats,
    loadStats,
    saveStats,
    getBaseDiffLevel,
    getDifficultyLevel,
  };
})(window);
