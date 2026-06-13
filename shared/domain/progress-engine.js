/**
 * ProgressEngine - 학습 진행률 관리 공통 모듈
 * @module ProgressEngine
 */

/**
 * @typedef {Object.<string, {levels: Object.<number, {attempts: number, correct: number, totalTime: number}>, weaknesses: Object.<string, {attempts: number, correct: number}>}> & { _updated_at?: number }} StatsObject
 */

/**
 * @typedef {{upThreshold?: number, downThreshold?: number}} ProgressOpts
 */

/**
 * @typedef {{stats: StatsObject, domainKey: string, level: number, tag?: string, correct: boolean, elapsed: number, weaknessesKey?: string}} RecordResultArgs
 */
(function (global) {
  /**
   * localStorage 키 네임스페이스 헬퍼
   * @param {string} subject - 과목명 (예: 'english', 'korean', 'math', 'science')
   * @returns {string} 네임스페이스된 localStorage 키
   */
  function createStatsKey(subject) {
    return `aiden_${subject}_stats`;
  }

  /**
   * 빈 통계 객체 생성
   * @param {string[]} domainKeys - 도메인 키 배열 (예: 과목 카테고리 목록)
   * @returns {StatsObject} 빈 통계 객체
   */
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

  /**
   * 통계 로드
   * @param {string} storageKey - localStorage 키
   * @param {string[]} domainKeys - 도메인 키 배열
   * @returns {StatsObject} 통계 객체
   */
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

  /**
   * 통계 저장
   * @param {string} storageKey - localStorage 키
   * @param {StatsObject} stats - 통계 객체
   * @returns {void}
   */
  function saveStats(storageKey, stats) {
    stats._updated_at = Date.now();
    localStorage.setItem(storageKey, JSON.stringify(stats));
    if (window.SyncEngine) {
      window.SyncEngine.pushStats(storageKey, stats);
    }
  }

  /**
   * 기본 난이도 레벨 계산
   * @param {StatsObject} stats - 통계 객체
   * @param {string} domainKey - 도메인 키
   * @param {number} minData - 최소 데이터 포인트
   * @param {ProgressOpts} [opts] - 옵션
   * @returns {number} 계산된 레벨 (0-6)
   */
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

  /**
   * 최종 난이도 레벨 계산 (부스트/페널티 포함)
   * @param {StatsObject} stats - 통계 객체
   * @param {string} domainKey - 도메인 키
   * @param {number} minData - 최소 데이터 포인트
   * @param {number} globalBoost - 전역 부스트
   * @param {boolean[]} recentHistory - 최근 답변 이력
   * @param {ProgressOpts} [opts] - 옵션
   * @returns {number} 계산된 레벨 (0-6)
   */
  function getDifficultyLevel(stats, domainKey, minData, globalBoost, recentHistory, opts) {
    const flowBoost = getRecentFlowBoost(recentHistory);
    const base = getBaseDiffLevel(stats, domainKey, minData, opts) + globalBoost + flowBoost;
    const wrongs = recentHistory.filter((r) => r === false).length;
    const penalty = wrongs >= 2 ? 1 : 0;
    return Math.max(0, Math.min(6, base - penalty));
  }

  /**
   * 최근 답변 흐름 기반 부스트 계산
   * @param {boolean[]} recentHistory - 최근 답변 이력
   * @returns {number} 부스트 값 (0-2)
   */
  function getRecentFlowBoost(recentHistory) {
    if (!Array.isArray(recentHistory) || recentHistory.length === 0) return 0;
    const recent = recentHistory.slice(-5);
    const corrects = recent.filter((r) => r === true).length;
    if (corrects >= 5) return 2;
    if (corrects >= 3) return 1;
    return 0;
  }

  /* ═══════════════════════════════════
     결과 기록 공통 인터페이스
     - 인자: { stats, domainKey, level, tag, correct, elapsed, weaknessesKey }
     - 반환: 업데이트된 stats 객체 (동일 참조)
     - 책임: 레벨별 통계, 태그별 약점 통계 업데이트
     - 비책임: saveStats(), updateStreak(), 그물망/wrongPatterns/recentHistory (과목별 담당)
  ═══════════════════════════════════ */
  /**
   * 결과 기록
   * @param {RecordResultArgs} params - 기록 파라미터
   * @returns {StatsObject} 업데이트된 stats 객체
   */
  function recordResultCore({ stats, domainKey, level, tag, correct, elapsed, weaknessesKey }) {
    const domainStats = stats[domainKey];
    if (!domainStats || !domainStats.levels[level]) return stats;

    // 레벨별 통계 업데이트
    const lvStats = domainStats.levels[level];
    lvStats.attempts++;
    if (correct) lvStats.correct++;
    lvStats.totalTime += elapsed;

    // 태그별 약점 통계 업데이트
    const wKey = weaknessesKey || tag || 'overall';
    if (!domainStats.weaknesses[wKey]) {
      domainStats.weaknesses[wKey] = { attempts: 0, correct: 0 };
    }
    const wStats = domainStats.weaknesses[wKey];
    wStats.attempts++;
    if (correct) wStats.correct++;

    return stats;
  }

  /**
   * ProgressEngine 전역 객체
   * @typedef {Object} ProgressEngine
   * @property {typeof createStatsKey} createStatsKey
   * @property {typeof emptyStats} emptyStats
   * @property {typeof loadStats} loadStats
   * @property {typeof saveStats} saveStats
   * @property {typeof getBaseDiffLevel} getBaseDiffLevel
   * @property {typeof getDifficultyLevel} getDifficultyLevel
   * @property {typeof recordResultCore} recordResultCore
   */

  /** @type {ProgressEngine} */
  global.ProgressEngine = {
    createStatsKey,
    emptyStats,
    loadStats,
    saveStats,
    getBaseDiffLevel,
    getDifficultyLevel,
    recordResultCore,
  };
})(window);
