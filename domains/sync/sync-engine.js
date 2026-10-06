window.SyncEngine = (() => {
  const QUEUE_KEY = 'sync_queue';

  // Server-authoritative keys: these must only be mutated through server RPC,
  // never pushed back to cloud via generic LWW sync.
  const SERVER_AUTHORITATIVE_KEYS = new Set([
    'aiden_canonical_weekly_vocabulary_v1',
    'englishWeeklyWords'
  ]);

  // Current subject stats keys used by ProgressEngine.createStatsKey().
  // Legacy *GameStats keys remain read-only migration inputs so existing cloud data
  // can be recovered once without becoming the runtime storage authority again.
  const CANONICAL_STATS_KEYS = Object.freeze([
    'aiden_math_stats',
    'aiden_english_stats',
    'aiden_korean_stats',
    'aiden_science_stats'
  ]);

  const LEGACY_STATS_KEY_MAP = Object.freeze({
    mathGameStats: 'aiden_math_stats',
    englishGameStats: 'aiden_english_stats',
    koreanGameStats: 'aiden_korean_stats',
    scienceGameStats: 'aiden_science_stats'
  });

  const DEFAULT_PULL_KEYS = [
    'study_rewards',
    ...CANONICAL_STATS_KEYS,
    ...Object.keys(LEGACY_STATS_KEY_MAP),
    'aiden_canonical_weekly_vocabulary_v1'
  ];

  const DEFAULT_STUDY_SHOP_ITEMS = [
    { id: 'youtube', icon: '📺', label: '유튜브 10분', desc: '좋아하는 영상 시청', price: 1 },
    { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
    { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 },
    { id: 'bubble', icon: '🫧', label: '비눗방울 게임', desc: '버블팡 한 판 더!', price: 1 }
  ];

  /** 로그인 직후 pull 시 서버 빈 값이 로컬 진행을 덮지 않도록 study_rewards만 병합 */
  function mergeStudyRewardsPayload(local, remote) {
    const L = local && typeof local === 'object' ? local : {};
    const R = remote && typeof remote === 'object' ? remote : {};
    const keySet = new Set([
      ...Object.keys(L.custom_inventory || {}),
      ...Object.keys(R.custom_inventory || {})
    ]);
    const custom_inventory = {};
    keySet.forEach((k) => {
      custom_inventory[k] = Math.max(L.custom_inventory?.[k] || 0, R.custom_inventory?.[k] || 0);
    });

    let shop_items;
    if (Array.isArray(R.shop_items) && R.shop_items.length > 0) shop_items = R.shop_items.slice();
    else if (Array.isArray(L.shop_items) && L.shop_items.length > 0) shop_items = L.shop_items.slice();
    else shop_items = DEFAULT_STUDY_SHOP_ITEMS.slice();

    DEFAULT_STUDY_SHOP_ITEMS.forEach((defaultItem) => {
      if (!shop_items.some((item) => item.id === defaultItem.id)) {
        shop_items.push({ ...defaultItem });
      }
    });

    return {
      ...L,
      ...R,
      gems: Math.max(L.gems || 0, R.gems || 0),
      youtube_minutes: Math.max(L.youtube_minutes || 0, R.youtube_minutes || 0),
      snacks: Math.max(L.snacks || 0, R.snacks || 0),
      marble_plays: Math.max(L.marble_plays || 0, R.marble_plays || 0),
      bubble_plays: Math.max(L.bubble_plays || 0, R.bubble_plays || 0),
      custom_inventory,
      shop_items,
      _updated_at: Math.max(L._updated_at || 0, R._updated_at || 0)
    };
  }

  function normalizePulledRows(data) {
    const rowsByKey = new Map(data.map((row) => [row.data_key, row]));
    const normalized = data.filter(
      (row) => !Object.prototype.hasOwnProperty.call(LEGACY_STATS_KEY_MAP, row.data_key)
    );

    for (const [legacyKey, canonicalKey] of Object.entries(LEGACY_STATS_KEY_MAP)) {
      // Canonical cloud data always wins. Legacy data is only a fallback for users
      // whose older row has not yet been migrated.
      if (rowsByKey.has(canonicalKey)) continue;
      const legacyRow = rowsByKey.get(legacyKey);
      if (!legacyRow) continue;
      normalized.push({
        ...legacyRow,
        data_key: canonicalKey,
        legacy_source_key: legacyKey
      });
    }

    return normalized;
  }

  function getQueue() {
    try {
      const raw = localStorage.getItem(QUEUE_KEY);
      if (!raw) return {};
      const q = JSON.parse(raw);
      let cleaned = false;
      for (const k of Object.keys(q)) {
        if (SERVER_AUTHORITATIVE_KEYS.has(k)) {
          delete q[k];
          cleaned = true;
        }
      }
      if (cleaned) {
        localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
      }
      return q;
    } catch { return {}; }
  }

  function saveQueue(q) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  }

  // Supabase에 데이터 Push 
  async function pushToSupabase(key, payload) {
    if (SERVER_AUTHORITATIVE_KEYS.has(key)) return false;
    const user = window.Auth?.getUser();
    if (!user || !window.supabaseClient) return false;
    
    try {
      const { error } = await window.supabaseClient
        .from('user_data')
        .upsert({
          user_id: user.id,
          data_key: key,
          payload: payload,
          updated_at: new Date(payload._updated_at || Date.now()).toISOString()
        }, { onConflict: 'user_id, data_key' });
        
      if (error) console.error('Supabase Push Error:', error);
      return !error;
    } catch(e) {
      console.error(e); 
      return false; 
    }
  }

  // 큐 플러시 (오프라인 캐시 배포)
  async function flushQueue() {
    if (!navigator.onLine || !window.Auth?.getUser()) return;
    const q = getQueue();
    const keys = Object.keys(q);
    let updated = false;

    for (const k of keys) {
      if (SERVER_AUTHORITATIVE_KEYS.has(k)) {
        delete q[k];
        updated = true;
        continue;
      }
      const success = await pushToSupabase(k, q[k]);
      if (success) {
        delete q[k];
        updated = true;
      }
    }
    
    if (updated) saveQueue(q);
  }

  // 서버의 최신 데이터를 가져와서 로컬 localStorage 교체 (최종 기록 우선)
  // canonical weekly vocabulary는 server-authoritative: 항상 remote가 authority.
  async function pullAndMerge(keysToPull) {
    const user = window.Auth?.getUser();
    if (!user || !navigator.onLine || !window.supabaseClient) return;

    try {
      const { data, error } = await window.supabaseClient
        .from('user_data')
        .select('data_key, payload, updated_at')
        .eq('user_id', user.id)
        .in('data_key', keysToPull);

      if (error || !data) return;

      const pulledRows = normalizePulledRows(data);

      let hasUpdates = false;
      let hasWeeklyUpdate = false;
      for (const row of pulledRows) {
        const isLegacyFallback = Boolean(row.legacy_source_key);
        const localRaw = localStorage.getItem(row.data_key);
        let localTime = 0;
        let localParsed = null;
        if (localRaw) {
          try {
             localParsed = JSON.parse(localRaw);
             localTime = localParsed._updated_at || (localParsed.updatedAt ? new Date(localParsed.updatedAt).getTime() : 0);
          } catch(e){}
        }

        const dbTime = row.payload._updated_at || (row.payload.updatedAt ? new Date(row.payload.updatedAt).getTime() : 0) || new Date(row.updated_at).getTime();

        // Server-authoritative keys: always accept remote, never push local back (#4)
        if (SERVER_AUTHORITATIVE_KEYS.has(row.data_key)) {
          if (row.data_key === 'aiden_canonical_weekly_vocabulary_v1') {
            // Always hydrate from remote for canonical weekly set
            localStorage.setItem(row.data_key, JSON.stringify(row.payload));
            // Synchronize legacy projection
            if (window.WeeklyVocabularyStore && typeof window.WeeklyVocabularyStore.toLegacyProjection === 'function') {
              try {
                const legacyProj = window.WeeklyVocabularyStore.toLegacyProjection(row.payload);
                localStorage.setItem('englishWeeklyWords', JSON.stringify(legacyProj));
              } catch (e) {}
            } else if (Array.isArray(row.payload.items)) {
              try {
                const legacyProj = row.payload.items.map(it => ({
                  en: it.word || it.answer,
                  ko: it.ko || '',
                  icon: it.icon || ''
                }));
                localStorage.setItem('englishWeeklyWords', JSON.stringify(legacyProj));
              } catch (e) {}
            }
            hasWeeklyUpdate = true;
            hasUpdates = true;
          }
          // For englishWeeklyWords: do nothing here; it's synced as a projection above
          // Never push server-authoritative keys back to cloud via LWW
          continue;
        }

        // study_rewards는 보존 병합하고, subject stats는 현재 full-snapshot 계약대로 LWW 처리한다.
        if (dbTime > localTime) {
          let toStore = row.payload;
          let safeLocal = localParsed || {};

          if (row.data_key === 'study_rewards') {
            toStore = mergeStudyRewardsPayload(safeLocal, row.payload);
          }
          localStorage.setItem(row.data_key, JSON.stringify(toStore));
          hasUpdates = true;

          // Migrate a legacy-only cloud row into the canonical key. The legacy row is
          // intentionally left untouched; once the canonical row exists it wins on all
          // future pulls and the fallback becomes inert.
          if (isLegacyFallback) {
            pushStats(row.data_key, toStore);
          }
        } else if (localTime > dbTime && localRaw && localParsed) {
          // 로컬이 더 최신이면 클라우드로 푸시 큐 등록
          pushStats(row.data_key, localParsed);
        } else if (isLegacyFallback && localRaw && localParsed) {
          // Equal timestamps can occur after earlier migrations. Ensure the canonical
          // cloud row exists without rewriting local progress.
          pushStats(row.data_key, localParsed);
        }
      }

      if (hasWeeklyUpdate) {
        window.dispatchEvent(new CustomEvent('weekly-vocabulary-synced', {
          detail: { source: 'cloud-pull' }
        }));
      }

      // 동기화 완료 후 UI를 리로드하거나 이벤트를 방출하여 화면 갱신 유도
      if (hasUpdates) {
        window.dispatchEvent(new Event('cloud-sync-complete'));
      }
    } catch (e) { console.error('Pull Error', e); }
  }

  function pushStats(key, data) {
    if (SERVER_AUTHORITATIVE_KEYS.has(key)) return;
    if (!data) return;
    if (!data._updated_at) data._updated_at = Date.now();
    const q = getQueue();
    q[key] = data;
    saveQueue(q);
    
    // 온라인이면 즉시 전송 시도
    if (navigator.onLine) {
      flushQueue();
    }
  }

  // 이벤트 리스너: 온라인  복구 및 로그인 시 큐 전송
  window.addEventListener('online', flushQueue);
  window.addEventListener('auth-changed', () => {
    flushQueue();
    // 접속 중인 페이지가 쓰는 주요 Key들을 풀링 (기본 공통키 + 주간 영단어 단일 진실 소스)
    pullAndMerge(DEFAULT_PULL_KEYS);
  });

  return {
    pushStats,
    pullAndMerge,
    flushQueue,
    getQueue,
    pushToSupabase,
    SERVER_AUTHORITATIVE_KEYS
  };
})();

