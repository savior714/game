/**
 * @fileoverview 보호자 보상 감사 패널(guardian-audit.js), 위임 이벤트(guardian-events.js),
 * 모든 보상 획득 프로듀서(daily-streak, diversity-reward, milestone-tracker, daily-goal, rocket-core),
 * CSV/JSON 내보내기 및 전체 초기화 실행 End-to-End 검증.
 *
 * 실행: node tests/test_guardian_reward_audit.mjs
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import vm from "node:vm";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (rel) => readFileSync(resolve(root, rel), "utf8");

const store = new Map();
const downloads = [];
const pushedPayloads = [];
const docListeners = new Map();
const winListeners = new Map();

function createMockElement(id, tag = "div") {
  const classes = new Set(id === "audit-panel" || id === "reward-reset-modal" ? ["hidden"] : []);
  return {
    id,
    tagName: tag.toUpperCase(),
    innerHTML: "",
    textContent: "",
    value: "",
    href: "",
    download: "",
    dataset: {},
    style: { display: "block" },
    classList: {
      add: (...names) => names.forEach((n) => classes.add(n)),
      remove: (...names) => names.forEach((n) => classes.delete(n)),
      contains: (name) => classes.has(name),
      toggle: (name, force) => {
        if (force === undefined) {
          if (classes.has(name)) classes.delete(name);
          else classes.add(name);
        } else if (force) classes.add(name);
        else classes.delete(name);
      },
    },
    appendChild() {},
    removeChild() {},
    remove() {},
    focus() {},
    click() {
      downloads.push({ download: this.download, href: this.href });
    },
    closest(selector) {
      if (selector === "[data-action]" && this.dataset.action) return this;
      return null;
    },
  };
}

const elements = new Map([
  ["tab-english", createMockElement("tab-english", "button")],
  ["tab-math", createMockElement("tab-math", "button")],
  ["tab-korean", createMockElement("tab-korean", "button")],
  ["tab-science", createMockElement("tab-science", "button")],
  ["tab-growth", createMockElement("tab-growth", "button")],
  ["tab-audit", createMockElement("tab-audit", "button")],
  ["level-panel", createMockElement("level-panel")],
  ["math-level-panel", createMockElement("math-level-panel")],
  ["weekly-section", createMockElement("weekly-section")],
  ["reward-custom-section", createMockElement("reward-custom-section")],
  ["local-backup-section", createMockElement("local-backup-section")],
  ["growth-panel", createMockElement("growth-panel")],
  ["audit-panel", createMockElement("audit-panel")],
  ["audit-panel-body", createMockElement("audit-panel-body")],
  ["reward-reset-modal", createMockElement("reward-reset-modal")],
  ["reward-reset-modal-summary", createMockElement("reward-reset-modal-summary")],
  ["reward-reset-note-input", createMockElement("reward-reset-note-input", "input")],
]);

const document = {
  readyState: "complete",
  body: { appendChild() {}, removeChild() {} },
  head: { appendChild() {} },
  addEventListener(type, fn) {
    if (!docListeners.has(type)) docListeners.set(type, []);
    docListeners.get(type).push(fn);
  },
  getElementById(id) {
    return elements.get(id) || null;
  },
  querySelector() { return null; },
  querySelectorAll(sel) {
    if (sel === ".tab-btn") {
      return ["tab-english", "tab-math", "tab-korean", "tab-science", "tab-growth", "tab-audit"].map((k) => elements.get(k));
    }
    return [];
  },
  createElement(tag) {
    return createMockElement("", tag);
  },
};

const blobs = [];
class MockBlob {
  constructor(parts, opts = {}) {
    this.content = parts.join("");
    this.type = opts.type || "";
    blobs.push(this);
  }
}

const window = {
  document,
  location: { href: "https://example.test/domains/reward/guardian/index.html", pathname: "/domains/reward/guardian/index.html", hash: "" },
  history: { replaceState() {} },
  navigator: { onLine: true, userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" },
  URL: Object.assign(URL, {
    createObjectURL: () => "blob:mock-audit",
    revokeObjectURL: () => {},
  }),
  Blob: MockBlob,
  SyncEngine: {
    pushStats(key, payload) {
      pushedPayloads.push({ key, payload: JSON.parse(JSON.stringify(payload)) });
    },
  },
  addEventListener(type, fn) {
    if (!winListeners.has(type)) winListeners.set(type, []);
    winListeners.get(type).push(fn);
  },
  dispatchEvent(ev) {
    (winListeners.get(ev.type) || []).forEach((fn) => fn(ev));
  },
};
window.window = window;
window.self = window;

const localStorage = {
  get length() { return store.size; },
  key(idx) { return Array.from(store.keys())[idx] || null; },
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
window.localStorage = localStorage;

const ctx = vm.createContext({
  window,
  self: window,
  globalThis: null,
  document,
  location: window.location,
  history: window.history,
  navigator: window.navigator,
  localStorage,
  URL: window.URL,
  Blob: MockBlob,
  console,
  Date,
  Math,
  Number,
  JSON,
  Object,
  Array,
  Set,
  Map,
  String,
  Boolean,
  RegExp,
  Promise,
  Error,
  setTimeout: (fn) => { if (fn) fn(); return 1; },
  clearTimeout() {},
  requestAnimationFrame: (fn) => fn(),
});
ctx.globalThis = ctx;

// 1. 코어 원장, 보상 시스템, 모든 학습 보상 프로듀서, 보호자 감사 UI + 위임 이벤트 로드
vm.runInContext(read("shared/domain/reward-ledger.js"), ctx, { filename: "shared/domain/reward-ledger.js" });
vm.runInContext(read("domains/reward/reward.js"), ctx, { filename: "domains/reward/reward.js" });
vm.runInContext("window.RewardSystem = RewardSystem; globalThis.RewardSystem = RewardSystem;", ctx);

for (const file of [
  "shared/domain/daily-streak.js",
  "shared/domain/diversity-reward.js",
  "shared/domain/milestone-tracker.js",
  "domains/math/daily-goal.js",
  "shared/ui/rocket-core.js",
  "domains/reward/guardian/guardian-audit.js",
  "domains/reward/guardian/guardian-events.js",
]) {
  vm.runInContext(read(file), ctx, { filename: file });
}
vm.runInContext(
  "window.DailyStreak = DailyStreak; window.DiversityReward = DiversityReward; window.MilestoneTracker = MilestoneTracker;",
  ctx
);

const rs = ctx.RewardSystem;

// 2. 5개 보상 획득 경로 + 보석 교환 + 보상 사용을 실제로 모두 발생시킨다.
// (a) 출석 연속 학습 보상 (영어)
ctx.window.DailyStreak.recordAnswer("english", true);
// (b) 다과목 다양성 보상 (수학 추가 -> 2과목 달성)
ctx.window.DiversityReward.recordCorrect("english");
ctx.window.DiversityReward.recordCorrect("math");
// (c) 정답 마일스톤 보상 (20문제 연속 정답 누적)
for (let i = 0; i < 20; i += 1) {
  ctx.window.MilestoneTracker.record(true);
}
// (d) 수학 오늘의 목표 보상
const now = Date.now();
let goal = ctx.window.MathDailyGoalEngine.initOrGetDailyGoal({
  now,
  masteryMap: {},
  skillOrder: ["math.add.within_10"],
  preference: { presetId: "light" },
});
for (let i = 0; i < goal.targetCount; i += 1) {
  goal = ctx.window.MathDailyGoalEngine.recordGoalProgress({
    goal,
    skillId: "math.add.within_10",
    correct: true,
    now,
  }).goal;
}
ctx.window.MathDailyGoalEngine.claimGoalReward({ goal, rewardSystem: rs, now });
// (e) 연속 정답 로켓 발사 보상
vm.runInContext('globalThis.SUBJECT_NAME = "science";', ctx);
ctx.window.RocketCore.install(ctx.window, () => ({ globalBoost: 1 }));
ctx.window.showBoostBanner();

// (f) 보석 상점 교환 (간식 1개 교환: 보석 -2, 간식 +1)
assert.equal(rs.exchangeGem("snack"), true);
// (g) 간식 1개 사용
assert.equal(rs.consumeInternal("snack", null, 1), true);

assert.equal(rs.verifyIntegrity().ok, true, "모든 프로듀서·교환·사용 후 원장 무결성이 참이어야 한다.");

// 3. 위임 클릭 이벤트로 #tab-audit 열기 검증
function clickAction(action, extraDataset = {}) {
  const target = createMockElement("", "button");
  target.dataset = { action, ...extraDataset };
  for (const listener of docListeners.get("click") || []) {
    listener({ target, stopPropagation() {}, preventDefault() {} });
  }
}

clickAction("show-audit");
assert.equal(elements.get("audit-panel").classList.contains("hidden"), false, "감사 패널이 표시되어야 한다.");
const initialHtml = elements.get("audit-panel-body").innerHTML;
assert.match(initialHtml, /Epoch #1/);
assert.match(initialHtml, /원장 무결성 검증 통과/);
assert.match(initialHtml, /일일 출석 학습 보상 \(1일차 · 영어\)/);
assert.match(initialHtml, /다과목 학습 보상 \(영어·수학 2과목 달성\)/);
assert.match(initialHtml, /학습 마일스톤 달성/);
assert.match(initialHtml, /수학 오늘의 목표 달성/);
assert.match(initialHtml, /연속 정답 로켓 발사 보상 \(과학\)/);
assert.match(initialHtml, /간식 사용 승인 차감 \(1개 사용\)/);

// 4. 필터(사용 내역만) 및 검색어 입력 검증
clickAction("audit-filter-type", { filterValue: "consume" });
const consumeOnlyHtml = elements.get("audit-panel-body").innerHTML;
assert.match(consumeOnlyHtml, /조회 결과 1건/);
assert.match(consumeOnlyHtml, /간식 사용 승인 차감 \(1개 사용\)/);
assert.doesNotMatch(consumeOnlyHtml, /연속 정답 로켓 발사 보상 \(과학\)/);

clickAction("audit-filter-type", { filterValue: "all" });

// 5. CSV / JSON 감사 리포트 내보내기 검증
clickAction("export-audit-csv");
assert.equal(downloads.length, 1);
assert.match(downloads[0].download, /\.csv$/);
assert.match(blobs[0].content, /수학 오늘의 목표 달성/);

clickAction("export-audit-json");
assert.equal(downloads.length, 2);
assert.match(downloads[1].download, /\.json$/);
const exportedJson = JSON.parse(blobs[1].content);
assert.equal(exportedJson.report.ok, true);
assert.equal(exportedJson.report.epoch, 1);

// 6. 위임 이벤트로 전체 0 초기화 모달 열기 -> 메모 입력 -> 초기화 실행!
clickAction("open-reward-reset-modal");
assert.equal(elements.get("reward-reset-modal").classList.contains("hidden"), false);
elements.get("reward-reset-note-input").value = "10월 4주차 보상 정산 완료";
clickAction("confirm-reward-reset");

assert.equal(elements.get("reward-reset-modal").classList.contains("hidden"), true);
assert.equal(rs.getState().gems, 0, "초기화 직후 보석 잔액이 0이어야 한다.");
assert.equal(rs.getState().youtube_minutes, 0, "초기화 직후 자유시간 잔액이 0이어야 한다.");
assert.equal(rs.getState().snacks, 0, "초기화 직후 간식 잔액이 0이어야 한다.");
assert.equal(rs.verifyIntegrity().ok, true);

const postResetHtml = elements.get("audit-panel-body").innerHTML;
assert.match(postResetHtml, /Epoch #2/);
assert.match(postResetHtml, /10월 4주차 보상 정산 완료/);
assert.ok(
  pushedPayloads.some((p) => p.key === "study_rewards" && p.payload.reward_ledger.reset_epoch === 2 && p.payload.gems === 0),
  "초기화된 Epoch #2 상태가 즉시 SyncEngine 클라우드 큐로 전송되어야 한다."
);

console.log("PASS: Guardian audit UI, all 5 reward grant producers, filters, CSV/JSON exports, and epoch reset verified.");
