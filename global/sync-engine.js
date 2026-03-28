window.SyncEngine = (() => {
  const QUEUE_KEY = 'sync_queue';

  const DEFAULT_STUDY_SHOP_ITEMS = [
    { id: 'youtube', icon: '📺', label: '유튜브 15분', desc: '좋아하는 영상 시청', price: 1 },
    { id: 'snack', icon: '🍪', label: '간식 1개', desc: '맛있는 간식 시간', price: 1 },
    { id: 'marble', icon: '🎮', label: '마블 게임', desc: '마블 한 판 더!', price: 1 }
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
    if (Array.isArray(R.shop_items) && R.shop_items.length > 0) shop_items = R.shop_items;
    else if (Array.isArray(L.shop_items) && L.shop_items.length > 0) shop_items = L.shop_items;
    else shop_items = DEFAULT_STUDY_SHOP_ITEMS.slice();

    return {
      ...L,
      ...R,
      gems: Math.max(L.gems || 0, R.gems || 0),
      youtube_minutes: Math.max(L.youtube_minutes || 0, R.youtube_minutes || 0),
      snacks: Math.max(L.snacks || 0, R.snacks || 0),
      marble_plays: Math.max(L.marble_plays || 0, R.marble_plays || 0),
      custom_inventory,
      shop_items,
      _updated_at: Math.max(L._updated_at || 0, R._updated_at || 0)
    };
  }
  
  function getQueue() {
    try {
      return JSON.parse(localStorage.getItem(QUEUE_KEY) || '{}');
    } catch { return {}; }
  }

  function saveQueue(q) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  }

  // Supabase에 데이터 Push 
  async function pushToSupabase(key, payload) {
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
      const success = await pushToSupabase(k, q[k]);
      if (success) {
        delete q[k];
        updated = true;
      }
    }
    
    if (updated) saveQueue(q);
  }

  // 서버의 최신 데이터를 가져와서 로컬 localStorage 교체 (최종 기록 우선)
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

      let hasUpdates = false;
      for (const row of data) {
        const localRaw = localStorage.getItem(row.data_key);
        let localTime = 0;
        if (localRaw) {
          try {
             const parsed = JSON.parse(localRaw);
             localTime = parsed._updated_at || 0;
          } catch(e){}
        }

        const dbTime = row.payload._updated_at || new Date(row.updated_at).getTime();

        // 최종 완료 기록을 우선시
        if (dbTime > localTime) {
          let toStore = row.payload;
          if (row.data_key === 'study_rewards') {
            let localParsed = {};
            if (localRaw) {
              try {
                localParsed = JSON.parse(localRaw);
              } catch (e) {
                localParsed = {};
              }
            }
            toStore = mergeStudyRewardsPayload(localParsed, row.payload);
          }
          localStorage.setItem(row.data_key, JSON.stringify(toStore));
          hasUpdates = true;
        } else if (localTime > dbTime && localRaw) {
          // 로컬이 더 최신이면 클라우드로 푸시 큐 등록
          pushStats(row.data_key, JSON.parse(localRaw)); 
        }
      }

      // 동기화 완료 후 UI를 리로드하거나 이벤트를 방출하여 화면 갱신 유도
      if (hasUpdates) {
        window.dispatchEvent(new Event('cloud-sync-complete'));
      }
    } catch (e) { console.error('Pull Error', e); }
  }

  function pushStats(key, data) {
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
    // 접속 중인 페이지가 쓰는 주요 Key들을 풀링 (예시로 기본 공통키만 명시)
    pullAndMerge(['study_rewards', 'mathGameStats', 'englishGameStats', 'koreanGameStats', 'scienceGameStats']);
  });

  return { pushStats, pullAndMerge };
})();
