/**
 * @fileoverview 보상 상점 모달의 "최근 보상 기록" 렌더링 검증.
 *
 * 상단 HUD 보상을 사용한 뒤, 사용자(아이·보호자)가 같은 화면에서
 * 획득(+)/사용(−)과 남은 수량, 무결성 상태를 확인할 수 있어야 한다.
 *
 * 실행: node tests/test_reward_activity_ui.mjs
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import vm from "node:vm";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ledgerSrc = readFileSync(resolve(root, "shared/domain/reward-ledger.js"), "utf8");
const rewardSrc = readFileSync(resolve(root, "domains/reward/reward.js"), "utf8");
const uiSrc = readFileSync(resolve(root, "domains/reward/reward_ui.js"), "utf8");

const store = new Map([
  [
    "study_rewards",
    JSON.stringify({
      gems: 7,
      youtube_minutes: 30,
      snacks: 3,
      marble_plays: 1,
      bubble_plays: 0,
      _updated_at: 1000,
    }),
  ],
]);
const created = [];

function makeEl(tag) {
  const el = {
    tagName: tag,
    id: "",
    className: "",
    innerHTML: "",
    textContent: "",
    style: {},
    dataset: {},
    children: [],
    classList: { add() {}, remove() {}, contains() { return false; } },
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    remove() {},
    addEventListener() {},
    setAttribute() {},
    getAttribute() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() {},
    closest() { return null; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 0, height: 0 }; },
  };
  created.push(el);
  return el;
}

const mount = makeEl("div");
mount.id = "reward-inventory-mount";
mount.dataset = { rewardSurface: "full" };

const document = {
  readyState: "complete",
  addEventListener() {},
  createElement: makeEl,
  getElementById(id) { return id === "reward-inventory-mount" ? mount : null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  body: { appendChild(el) { el.parent = "body"; return el; } },
  head: { appendChild() {} },
};

const window = {
  addEventListener() {},
  location: { href: "https://example.test/index.html", reload() {} },
  innerWidth: 1024,
  innerHeight: 768,
};
window.window = window;
window.self = window;

const context = vm.createContext({
  window,
  document,
  localStorage: {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  },
  navigator: { onLine: false },
  console,
  alert() {},
  prompt() { return null; },
  Date,
  Math,
  Number,
  JSON,
  Object,
  Array,
  Set,
  Map,
  String,
  URL,
  setTimeout: (fn) => fn && 0,
  clearTimeout() {},
});

vm.runInContext(ledgerSrc, context);
vm.runInContext(`${rewardSrc}\n;globalThis.RewardSystem = RewardSystem;`, context);
vm.runInContext(`${uiSrc}\n;globalThis.RewardSystemUI = RewardSystemUI;`, context);

const rewards = context.RewardSystem;

assert.equal(rewards.getState().snacks, 3);
assert.equal(rewards.consumeInternal("snack", null, 3), true);
assert.equal(rewards.getState().snacks, 0);

rewards.openShopModal();
const overlay = created.find((el) => el.className && el.className.includes("reward-modal-overlay"));
assert.ok(overlay, "보석 상점 모달이 생성되어야 한다.");

const html = overlay.innerHTML;
assert.match(html, /보석 상점/);
assert.match(html, /최근 보상 기록/);
assert.match(html, /🍪 간식/);
assert.match(html, /사용/);
assert.match(html, /남은 0개/);
assert.match(html, /✅ 기록 확인됨/);
assert.doesNotMatch(html, /undefined/);
assert.doesNotMatch(html, /NaN/);

// 저장값을 손으로 부풀려도(원장에 없는 증가) 잔액은 늘어나지 않는다.
const gemsBeforeTamper = rewards.getState().gems;
context.localStorage.setItem(
  "study_rewards",
  JSON.stringify({ ...JSON.parse(store.get("study_rewards")), gems: 999 })
);
vm.runInContext("RewardSystem.init();", context);
assert.equal(
  rewards.getState().gems,
  gemsBeforeTamper,
  "원장에 없는 외부 증가는 반영되지 않아야 한다."
);
created.length = 0;
rewards.openShopModal();
const tamperedOverlay = created.find((el) => el.className && el.className.includes("reward-modal-overlay"));
assert.ok(tamperedOverlay, "보석 상점 모달이 다시 생성되어야 한다.");
assert.match(tamperedOverlay.innerHTML, /✅ 기록 확인됨/);

console.log("PASS: reward activity log renders acquisition/consumption and integrity status.");
