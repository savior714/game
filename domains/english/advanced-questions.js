/* ═══════════════════════════════════
   영어 고급 유형: 혼동 페어, 문장 빈칸, 입력 정규화
   — engine.js에서 WORDS, makeWordChoices와 연동
   ═══════════════════════════════════ */

const EnglishAdvancedQuestions = (function () {
  function levenshtein(a, b) {
    const m = a.length;
    const n = b.length;
    if (m === 0) return n;
    if (n === 0) return m;
    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        dp[i][j] = Math.min(
          dp[i - 1][j] + 1,
          dp[i][j - 1] + 1,
          dp[i - 1][j - 1] + cost
        );
      }
    }
    return dp[m][n];
  }

  /**
   * 철자가 비슷한 오답을 우선하는 4지선다 풀
   * @param {function} fallbackChoices () => string[] — makeWordChoices 결과
   */
  function makeMinimalPairChoices(word, WORDS, wEn, fallbackChoices) {
    const correct = wEn(word).trim();
    const cLow = correct.toLowerCase();
    const scored = [];
    for (const data of Object.values(WORDS)) {
      for (const w of data.words) {
        const v = wEn(w).trim();
        if (!v || v.toLowerCase() === cLow) continue;
        const vLow = v.toLowerCase();
        const dist = levenshtein(cLow, vLow);
        if (dist < 1 || dist > 3) continue;
        const lenBonus = Math.abs(v.length - correct.length) <= 1 ? 0 : 0.3;
        scored.push({ v, score: dist + lenBonus });
      }
    }
    scored.sort((a, b) => a.score - b.score || Math.random() - 0.5);
    const picks = [];
    const seen = new Set([cLow]);
    for (const { v } of scored) {
      if (picks.length >= 3) break;
      const k = v.toLowerCase();
      if (!seen.has(k)) {
        seen.add(k);
        picks.push(v);
      }
    }
    const fb = fallbackChoices();
    let i = 0;
    while (picks.length < 3 && i < fb.length) {
      const v = fb[i++];
      if (v.toLowerCase() !== cLow && !picks.some(p => p.toLowerCase() === v.toLowerCase())) picks.push(v);
    }
    if (picks.length < 3) {
      const pool = [];
      for (const data of Object.values(WORDS)) {
        for (const w of data.words) pool.push(wEn(w).trim());
      }
      pool.sort(() => Math.random() - 0.5);
      for (const v of pool) {
        if (picks.length >= 3) break;
        const k = v.toLowerCase();
        if (k !== cLow && !picks.some(p => p.toLowerCase() === k)) picks.push(v);
      }
    }
    return [correct, ...picks.slice(0, 3)].sort(() => Math.random() - 0.5);
  }

  function articleFor(en) {
    const c = en.trim()[0];
    if (!c) return 'a';
    return 'aeiou'.includes(c.toLowerCase()) ? 'an' : 'a';
  }

  /**
   * 카테고리별 초등 수준 영문장 + 빈칸(_____)
   */
  function buildSentenceLine(word, cat, wEn, wKo) {
    const en = wEn(word);
    const a = articleFor(en);

    function choose(s1, s2) {
      return Math.random() < 0.5 ? s1 : s2;
    }

    const byCat = {
      animals: () => choose(`At the zoo I saw ${a} _____ .`, `This animal is ${a} _____ .`),
      fruits: () => choose(`For a snack I want ${a} _____ .`, `This fruit is ${a} _____ .`),
      colors: () => choose(`My favorite color is _____ .`, `The door looks _____ .`),
      numbers: () => choose(`How do you say this in English? _____`, `I write the number _____ .`),
      body: () => choose(`I wash my _____ carefully.`, `This is my _____ .`),
      actions: () => choose(`Every day I _____ with friends.`, `I can _____ well.`),
      descriptions: () => choose(`Today it feels _____ .`, `This question is _____ .`),
      food_drink: () => choose(`I like _____ .`, `We eat _____ at home.`),
      school: () => choose(`At school I use ${a} _____ .`, `In class we read ${a} _____ .`),
      house: () => choose(`At home I sit on the _____ .`, `There is ${a} _____ in my room.`),
      clothing: () => choose(`I put on my _____ .`, `These _____ are comfortable.`),
      nature: () => choose(`Outside I see ${a} _____ .`, `In nature I find ${a} _____ .`),
      jobs: () => choose(`I want to be ${a} _____ .`, `She works as ${a} _____ .`),
      transport: () => choose(`We travel by _____ .`, `I ride ${a} _____ .`),
      places: () => choose(`We meet at the _____ .`, `Let's go to the _____ .`),
      space: () => choose(`I see ${a} _____ in the sky.`, `The _____ shines brightly.`),
    };

    const fn = byCat[cat];
    if (fn) return fn();

    return choose(`This is ${a} _____ .`, `Look! I see ${a} _____ .`);
  }

  function buildSentenceQuestion(word, cat, wEn, wKo, wIco) {
    const sentenceLine = buildSentenceLine(word, cat, wEn, wKo);
    return {
      ico: wIco(word),
      koHint: wKo(word),
      sentenceLine,
      label: '문장의 빈칸에 알맞은 영단어를 고르세요.',
    };
  }

  /** 입력값과 정답 비교 (공백·대소문자 무시) */
  function normalizeEquals(input, expected) {
    const a = String(input || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');
    const b = String(expected || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');
    return a === b;
  }

  return {
    levenshtein,
    makeMinimalPairChoices,
    buildSentenceQuestion,
    normalizeEquals,
  };
})();
