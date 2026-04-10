/**
 * 보상 시스템 로직 검증 스크립트 (Node.js)
 * localStorage 및 DOM이 없는 환경이므로 모의 객체를 사용하여 로직만 테스트합니다.
 */

// 1. Mock LocalStorage
const mockStorage = {};
global.localStorage = {
  getItem: (key) => mockStorage[key] || null,
  setItem: (key, val) => { mockStorage[key] = val; },
};

// 2. Mock DOM
global.document = {
  readyState: 'complete',
  addEventListener: () => {},
  getElementById: () => ({ textContent: '', style: {}, dataset: {}, getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }) }),
  querySelectorAll: () => [],
  querySelector: () => ({ style: {}, textContent: '', querySelector: () => ({ textContent: '' }) }),
  createElement: () => ({ 
    style: {}, 
    appendChild: () => {}, 
    remove: () => {},
    querySelector: () => ({ style: {}, textContent: '' })
  }),
  body: { 
    prepend: () => {}, 
    appendChild: () => {},
    dataset: {},
    style: {}
  },
  head: { appendChild: () => {} },
  documentElement: { style: { setProperty: () => {} } }
};
global.window = {
  location: { pathname: '/math/index.html' },
  addEventListener: () => {},
  innerWidth: 1000,
  innerHeight: 800,
  getComputedStyle: () => ({ paddingTop: '0px' })
};
global.alert = () => {};
global.requestAnimationFrame = (callback) => callback();
global.performance = { now: () => Date.now() };

// 3. Load RewardSystem (Using eval to load the file as a string to avoid module issues in simple script)
const fs = require('fs');
const path = require('path');
const rewardJsContent = fs.readFileSync(path.join(__dirname, '..', 'global', 'reward.js'), 'utf8');

// reward.js가 IIFE이므로 전역 RewardSystem을 획득해야 함
// 파일 내용에서 'const RewardSystem =' 부분을 제거하여 eval 결과를 바로 받거나, 
// 전역 변수로 선언되도록 처리합니다.
const rewardJsCode = rewardJsContent + "\nRewardSystem;"; 
const RS = eval(rewardJsCode);

function test() {
  console.log('--- 보상 시스템 검증 시작 ---');

  // 초기 상태 확인
  let state = RS.getState();
  console.log('초기 보석:', state.gems);

  // 보석 추가 테스트
  RS.add('gems', 1);
  state = RS.getState();
  console.log('보석 1개 추가 후:', state.gems);
  if (state.gems !== 1) throw new Error('보석 추가 실패');

  // 보석 교환 테스트 (유튜브)
  const initialYT = state.youtube_minutes;
  RS.exchangeGem('youtube');
  state = RS.getState();
  console.log('유튜브 교환 후 - 보석:', state.gems, '유튜브:', state.youtube_minutes);
  if (state.gems !== 0 || state.youtube_minutes !== initialYT + 15) throw new Error('유튜브 교환 실패');

  // 보석 부족 상황 테스트
  try {
    RS.exchangeGem('snack');
    if (RS.getState().snacks !== 0) throw new Error('보석 부족한데 교환됨');
    console.log('보석 부족 시 교환 차단 확인');
  } catch (e) {
    console.log('보석 부족 예외 발생 (문구 노출 확인 필요)');
  }

  // 보석 여러 개 추가 및 교환
  RS.add('gems', 2);
  RS.exchangeGem('snack');
  RS.exchangeGem('marble');
  state = RS.getState();
  console.log('여러 개 교환 후 - 보석:', state.gems, '간식:', state.snacks, '마블:', state.marble_plays);
  if (state.gems !== 0 || state.snacks !== 1 || state.marble_plays !== 1) throw new Error('복합 교환 실패');

  console.log('--- 모든 로직 검증 통과! ---');
}

try {
  test();
} catch (err) {
  console.error('검증 실패:', err.message);
  process.exit(1);
}
