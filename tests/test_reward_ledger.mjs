/**
 * @fileoverview 보상 원장(RewardLedger) 순수 로직 검증.
 *
 * 고정하는 계약:
 * - 잔액은 "획득/사용 델타의 합"이며, 소비는 어떤 스냅샷에도 되살아나지 않는다.
 * - 병합은 교환 가능(commutative)하고 멱등(idempotent)하다.
 * - 영수증은 합집합으로 병합되어 같은 보상이 두 번 지급되지 않는다.
 * - 원장이 없는(구버전) 스냅샷은 잔액을 늘릴 수 없고, 줄어든 사실만 반영한다.
 *
 * 실행: node tests/test_reward_ledger.mjs
 */

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import vm from "node:vm";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(resolve(root, "shared/domain/reward-ledger.js"), "utf8");
const context = vm.createContext({ console, Date, Math, Number, JSON, Object, Array, Set, Map, String });
vm.runInContext(source, context);
const Ledger = context.RewardLedger;

assert.ok(Ledger, "RewardLedger 전역이 정의되어야 한다.");

function migrate(state) {
  return Ledger.normalizeState(state, { adoptFields: true });
}

function apply(state, deltas, meta) {
  return Ledger.applyDeltas(state, deltas, meta || { at: Date.now(), type: "consume" }).state;
}

// ── 1. 원장 도입: 기존 스냅샷은 1회 이관되고 잔액이 보존된다 ──
const legacy = { gems: 7, youtube_minutes: 30, snacks: 3, marble_plays: 2, bubble_plays: 1, _updated_at: 1000 };
const migrated = migrate(legacy);
assert.equal(migrated.gems, 7);
assert.equal(migrated.youtube_minutes, 30);
assert.equal(migrated.snacks, 3);
assert.equal(migrated.reward_ledger.v, 1);
assert.equal(Ledger.verify(migrated).ok, true, "이관 직후 잔액과 원장이 일치해야 한다.");

// ── 2. 전부 사용한 뒤: 어떤 오래된 스냅샷도 잔액을 되살리지 못한다 ──
const emptied = apply(
  migrated,
  [
    { key: "gems", delta: -7 },
    { key: "youtube_minutes", delta: -30 },
    { key: "snacks", delta: -3 },
    { key: "marble_plays", delta: -2 },
    { key: "bubble_plays", delta: -1 },
  ],
  { at: 2000, type: "consume" }
);
for (const key of Ledger.FIELD_KEYS) {
  assert.equal(emptied[key], 0, `${key}는 사용 후 0이어야 한다.`);
}

const staleLedgerSnapshot = { ...migrated, _updated_at: 999999 };
const staleLegacySnapshot = {
  gems: 7,
  youtube_minutes: 30,
  snacks: 3,
  marble_plays: 2,
  bubble_plays: 1,
  _updated_at: 999999,
};

for (const [name, stale] of [
  ["원장 스냅샷", staleLedgerSnapshot],
  ["원장 없는 스냅샷", staleLegacySnapshot],
]) {
  const merged = Ledger.mergeStates(emptied, stale);
  for (const key of Ledger.FIELD_KEYS) {
    assert.equal(merged[key], 0, `${name} 병합 후 ${key}가 되살아나면 안 된다.`);
  }
  assert.equal(Ledger.verify(merged).ok, true);
}

// ── 3. 정말 획득한 만큼만 다시 채워진다 ──
const afterGrant = apply(emptied, [{ key: "gems", delta: 2 }], { at: 3000, type: "grant" });
assert.equal(afterGrant.gems, 2, "획득 이벤트 1건만큼만 증가해야 한다.");
const regranted = Ledger.mergeStates(afterGrant, staleLegacySnapshot);
assert.equal(regranted.gems, 2, "획득 후에도 오래된 스냅샷은 초과 지급하지 못한다.");

// ── 4. 병합은 교환 가능하고 멱등하다 ──
const left = apply(migrated, [{ key: "gems", delta: -2 }], { at: 4000, type: "consume" });
const right = apply(migrated, [{ key: "gems", delta: 3 }], { at: 5000, type: "grant" });
const mergedLR = Ledger.mergeStates(left, right);
const mergedRL = Ledger.mergeStates(right, left);
assert.equal(mergedLR.gems, mergedRL.gems, "병합 순서가 결과를 바꾸면 안 된다.");
assert.equal(mergedLR.gems, 8, "획득과 사용은 모두 반영되어야 한다(7 - 2 + 3).");
assert.equal(Ledger.mergeStates(mergedLR, mergedLR).gems, mergedLR.gems, "같은 상태를 다시 병합해도 값이 변하지 않아야 한다.");
assert.equal(Ledger.mergeStates(mergedLR, left).gems, mergedLR.gems, "이미 포함한 이벤트를 다시 병합해도 중복 계산하지 않아야 한다.");

// ── 5. 영수증은 합집합 병합(중복 지급 방지) ──
const receiptA = Ledger.mergeReceipts(
  { "reward.daily-streak.2026-10-22": { receiptId: "reward.daily-streak.2026-10-22", grantedAt: 10, grants: [] } },
  {}
);
const receiptB = Ledger.mergeReceipts(
  {},
  { "reward.daily-streak.2026-10-22": { receiptId: "reward.daily-streak.2026-10-22", grantedAt: 10, grants: [] } }
);
assert.deepEqual(Object.keys(receiptA), Object.keys(receiptB), "영수증은 어느 쪽에만 있어도 보존되어야 한다.");
const mergedStateWithReceipts = Ledger.mergeStates(
  { ...afterGrant, claimed_receipts: { r1: { receiptId: "r1", grantedAt: 1, grants: [] } } },
  { ...afterGrant, claimed_receipts: {} }
);
assert.ok(mergedStateWithReceipts.claimed_receipts.r1, "영수증은 병합에서 사라지면 안 된다.");

// ── 6. 사용자 정의 보상도 같은 원장 규칙을 따른다 ──
const withCustom = apply(migrated, [{ key: "custom:sticker", delta: 5 }], { at: 6000, type: "grant" });
assert.equal(withCustom.custom_inventory.sticker, 5);
const customUsed = apply(withCustom, [{ key: "custom:sticker", delta: -5 }], { at: 7000, type: "consume" });
assert.equal(customUsed.custom_inventory.sticker, 0);
const customMerged = Ledger.mergeStates(customUsed, withCustom);
assert.equal(customMerged.custom_inventory.sticker, 0, "사용한 사용자 정의 보상도 되살아나면 안 된다.");

// ── 7. 음수 잔액은 0으로 고정되고, 원장 합계와 표시 잔액이 어긋나지 않는다 ──
const overdrawn = apply(apply(migrated, [{ key: "snacks", delta: -3 }], { at: 8000 }), [{ key: "snacks", delta: -3 }], { at: 9000 });
assert.equal(overdrawn.snacks, 0);
assert.equal(Ledger.verify(overdrawn).ok, true);

// ── 8. 감사 기록(activity)은 델타와 잔액을 함께 보여준다 ──
const activity = Ledger.activity(afterGrant, { limit: 3 });
assert.equal(activity.length, 3);
assert.equal(activity[0].key, "gems");
assert.equal(activity[0].delta, 2);
assert.equal(activity[0].balanceAfter, 2);
assert.equal(activity[1].balanceAfter, 0);

// ── 9. 조작된(원장과 불일치) 상태는 검증에서 잡히고, 잔액을 늘리지 못한다 ──
const tampered = { ...afterGrant, gems: 99 };
const tamperedReport = Ledger.verify(tampered);
assert.equal(tamperedReport.ok, false);
assert.equal(tamperedReport.mismatches[0].key, "gems");
// 원장은 획득 이벤트 없이 늘어난 외부 값을 인정하지 않는다(무단 충전 방지).
const adopted = migrate(tampered);
assert.equal(adopted.gems, 2, "원장 합계를 넘는 외부 값은 반영되지 않아야 한다.");
assert.equal(Ledger.verify(adopted).ok, true);
assert.ok(
  !adopted.reward_ledger.events.some((event) => event.reason === "external_write"),
  "증가 방향 외부 쓰기는 이벤트로 승격되지 않아야 한다."
);

// 반대로 줄어든 외부 값은 소비로 인정되어 감사 기록에 남는다.
const shrunk = migrate({ ...afterGrant, gems: 0 });
assert.equal(shrunk.gems, 0);
assert.ok(
  shrunk.reward_ledger.events.some((event) => event.reason === "external_write" && event.delta < 0),
  "감소 방향 외부 쓰기는 감사 이벤트로 남아야 한다."
);

console.log("PASS: reward ledger keeps consumption durable and merge commutative/idempotent.");
