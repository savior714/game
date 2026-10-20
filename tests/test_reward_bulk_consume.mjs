/**
 * @fileoverview 보상 여러 개 일괄 사용에 대한 RewardSystem 핵심 로직 검증.
 * 실행: node tests/test_reward_bulk_consume.mjs
 */
import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import vm from "node:vm";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(resolve(root, "domains/reward/reward.js"), "utf8");
const storage = new Map([
  ["study_rewards", JSON.stringify({
    gems: 0,
    youtube_minutes: 30,
    snacks: 8,
    custom_inventory: { sticker: 5 },
    shop_items: [{ id: "sticker", label: "스티커", icon: "⭐", price: 1 }],
  })],
]);
const toasts = [];
const document = {
  readyState: "loading",
  addEventListener() {},
};
const context = {
  console,
  alert() {},
  Date,
  Math,
  Number,
  JSON,
  document,
  window: { addEventListener() {} },
  localStorage: {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  },
  RewardSystemUI: {
    syncInventoryBarWithState() {},
    updateUI() {},
    showToast: (message) => toasts.push(message),
  },
};
vm.runInNewContext(`${source}\nglobalThis.rewardSystemUnderTest = RewardSystem;\nRewardSystem.getState().snacks = 8;\nRewardSystem.getState().youtube_minutes = 30;\nRewardSystem.getState().custom_inventory = { sticker: 5 };\nRewardSystem.getState().shop_items = [{ id: 'sticker', label: '스티커' }];`, context);
const rewards = context.rewardSystemUnderTest;

let callbackState = null;
assert.equal(rewards.consumeInternal("snack", (state) => { callbackState = state; }, 3), true);
assert.equal(rewards.getState().snacks, 5);
assert.equal(callbackState.snacks, 5);
assert.match(toasts.at(-1), /간식 3개 사용 완료/);

assert.equal(rewards.consumeInternal("sticker", null, 4), true);
assert.equal(rewards.getState().custom_inventory.sticker, 1);
assert.match(toasts.at(-1), /스티커 4개 사용 완료/);

const stateBeforeInvalidUse = JSON.stringify(rewards.getState());
assert.equal(rewards.consumeInternal("snack", null, 6), false);
assert.equal(rewards.consumeInternal("sticker", null, 2), false);
assert.equal(rewards.consumeInternal("snack", null, 1.5), false);
assert.equal(rewards.consumeInternal("snack", null, 0), false);
assert.equal(JSON.stringify(rewards.getState()), stateBeforeInvalidUse);

// YouTube minutes continue to be consumed by the session transaction, not as a bulk item deduction.
assert.equal(rewards.consumeInternal("youtube", null, 2), false);
assert.equal(rewards.getState().youtube_minutes, 30);

console.log("PASS: bulk snack/custom consumption is atomic and bounded; YouTube session charging stays guarded.");
