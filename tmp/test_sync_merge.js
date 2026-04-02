
// mock some data
const local = {
  '+': {
    levels: {
      0: { attempts: 10, correct: 9, totalTime: 100 },
      1: { attempts: 5, correct: 4, totalTime: 50 }
    },
    weaknesses: {
      'add_unit_7_8': { attempts: 2, correct: 1 }
    }
  },
  '_updated_at': 1000
};

const remote = {
  '+': {
    levels: {
      0: { attempts: 5, correct: 5, totalTime: 40 },
      1: { attempts: 10, correct: 10, totalTime: 90 },
      2: { attempts: 2, correct: 2, totalTime: 10 }
    },
    weaknesses: {
      'add_unit_7_8': { attempts: 3, correct: 3 },
      'add_unit_1_2': { attempts: 1, correct: 1 }
    }
  },
  '_updated_at': 2000
};

// Emulate SyncEngine context
const SyncEngine = {
  mergeGameStatsPayload: function(local, remote) {
    const L = local && typeof local === 'object' ? local : {};
    const R = remote && typeof remote === 'object' ? remote : {};
    const merged = {};

    const domainKeys = new Set([...Object.keys(L), ...Object.keys(R)].filter(k => k !== '_updated_at'));
    domainKeys.forEach(dk => {
      const lDom = L[dk] || { levels: {}, weaknesses: {} };
      const rDom = R[dk] || { levels: {}, weaknesses: {} };
      merged[dk] = { levels: {}, weaknesses: {} };

      const allLevels = new Set([...Object.keys(lDom.levels || {}), ...Object.keys(rDom.levels || {})]);
      allLevels.forEach(lvIdx => {
        const lvsL = lDom.levels?.[lvIdx] || { attempts: 0, correct: 0, totalTime: 0 };
        const lvsR = rDom.levels?.[lvIdx] || { attempts: 0, correct: 0, totalTime: 0 };
        merged[dk].levels[lvIdx] = {
          attempts: (lvsL.attempts || 0) + (lvsR.attempts || 0),
          correct: (lvsL.correct || 0) + (rVsR = lvsR.correct || 0), 
          totalTime: (lvsL.totalTime || 0) + (lvsR.totalTime || 0)
        };
      });

      const wKeys = new Set([...Object.keys(lDom.weaknesses || {}), ...Object.keys(rDom.weaknesses || {})]);
      wKeys.forEach(wk => {
        const wl = lDom.weaknesses?.[wk] || { attempts: 0, correct: 0 };
        const wr = rDom.weaknesses?.[wk] || { attempts: 0, correct: 0 };
        merged[dk].weaknesses[wk] = {
          attempts: (wl.attempts || 0) + (wr.attempts || 0),
          correct: (wl.correct || 0) + (wr.correct || 0)
        };
      });
    });

    merged._updated_at = Math.max(L._updated_at || 0, R._updated_at || 0);
    return merged;
  }
};

const result = SyncEngine.mergeGameStatsPayload(local, remote);
console.log(JSON.stringify(result, null, 2));

// Assertions
if (result['+'].levels[0].attempts !== 15) throw new Error('Level 0 attempts mismatch');
if (result['+'].levels[1].correct !== 14) throw new Error('Level 1 correct mismatch');
if (result['+'].weaknesses['add_unit_7_8'].attempts !== 5) throw new Error('Weakness attempts mismatch');
if (result._updated_at !== 2000) throw new Error('Updated at mismatch');

console.log('Merge Test Passed!');
