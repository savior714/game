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
    marble_plays: 4,
    bubble_plays: 3,
    custom_inventory: { sticker: 5 },
    shop_items: [{ id: "sticker", label: "스티커", icon: "⭐", price: 1 }],
  })],
]);
const toasts = [];
const openedModals = [];
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
    openYoutubeModal: (st) => openedModals.push(["youtube", st.youtube_minutes]),
    openSnackModal: (st) => openedModals.push(["snack", st.snacks]),
    openCustomModal: (item, st) => openedModals.push(["custom", item.id, st.custom_inventory[item.id] || 0]),
  },
};
vm.runInNewContext(`${source}\nglobalThis.rewardSystemUnderTest = RewardSystem;\nRewardSystem.getState().snacks = 8;\nRewardSystem.getState().youtube_minutes = 30;\nRewardSystem.getState().marble_plays = 4;\nRewardSystem.getState().bubble_plays = 3;\nRewardSystem.getState().custom_inventory = { sticker: 5 };\nRewardSystem.getState().shop_items = [{ id: 'sticker', label: '스티커' }];`, context);
const rewards = context.rewardSystemUnderTest;

let callbackState = null;
assert.equal(rewards.consumeInternal("snack", (state) => { callbackState = state; }, 3), true);
assert.equal(rewards.getState().snacks, 5);
assert.equal(callbackState.snacks, 5);
assert.match(toasts.at(-1), /간식 3개 사용 완료/);

assert.equal(rewards.consumeInternal("sticker", null, 4), true);
assert.equal(rewards.getState().custom_inventory.sticker, 1);
assert.match(toasts.at(-1), /스티커 4개 사용 완료/);

assert.equal(rewards.consumeInternal("marble", null, 2), true);
assert.equal(rewards.getState().marble_plays, 2);
assert.match(toasts.at(-1), /마블 게임 2회 사용 완료/);

assert.equal(rewards.consumeInternal("bubble", null, 2), true);
assert.equal(rewards.getState().bubble_plays, 1);
assert.match(toasts.at(-1), /비눗방울 게임 2회 사용 완료/);

const stateBeforeInvalidUse = JSON.stringify(rewards.getState());
assert.equal(rewards.consumeInternal("snack", null, 6), false);
assert.equal(rewards.consumeInternal("sticker", null, 2), false);
assert.equal(rewards.consumeInternal("snack", null, 1.5), false);
assert.equal(rewards.consumeInternal("snack", null, 0), false);
assert.equal(JSON.stringify(rewards.getState()), stateBeforeInvalidUse);

// YouTube minutes can also be consumed in bulk (1 unit = 10 minutes) via parent deduction.
assert.equal(rewards.consumeInternal("youtube", null, 2), true);
assert.equal(rewards.getState().youtube_minutes, 10);
assert.match(toasts.at(-1), /유튜브 2개 \(20분\) 사용 완료/);

// Reject YouTube deduction exceeding remaining minutes (10 min left < 20 min requested)
assert.equal(rewards.consumeInternal("youtube", null, 2), false);
assert.equal(rewards.getState().youtube_minutes, 10);

// Even when youtube_minutes or snacks are 0, clicking the HUD item still opens the modal
rewards.getState().youtube_minutes = 0;
rewards.getState().snacks = 0;
rewards.consume("youtube");
rewards.consume("snack");
assert.deepEqual(openedModals, [
  ["youtube", 0],
  ["snack", 0],
]);

console.log("PASS: bulk youtube/snack/custom consumption is atomic and bounded.");
