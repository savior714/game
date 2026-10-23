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

// ── 10. 빈 브라우저({})와 클라우드 원장을 병합할 때 0으로 깎아내리면 안 된다(항등원 보장) ──
const freshBrowserMerged = Ledger.mergeStates({}, migrated);
assert.equal(freshBrowserMerged.gems, 7, "새 브라우저의 빈 상태({})가 클라우드 보석을 0으로 만들면 안 된다.");
assert.equal(freshBrowserMerged.youtube_minutes, 30, "새 브라우저의 빈 상태({})가 자유시간을 0으로 만들면 안 된다.");
assert.equal(freshBrowserMerged.snacks, 3, "새 브라우저의 빈 상태({})가 간식을 0으로 만들면 안 된다.");
assert.ok(
  !freshBrowserMerged.reward_ledger.events.some((event) => event.reason === "legacy_snapshot_downward"),
  "빈 상태 병합에서 가짜 하향 조정 이벤트(legacy_snapshot_downward)가 생기면 안 된다."
);
const reverseFreshMerged = Ledger.mergeStates(migrated, {});
assert.equal(reverseFreshMerged.gems, 7);
assert.equal(reverseFreshMerged.youtube_minutes, 30);
assert.equal(reverseFreshMerged.snacks, 3);

// ── 11. 새 브라우저에서 첫 보상을 얻은 직후 mergeLedgers(새로고침 복구)해도 이벤트가 증발하면 안 된다 ──
const firstEarnOnEmpty = apply({}, [{ key: "gems", delta: 2 }], { at: 5000, type: "grant", reason: "math_goal" });
assert.equal(firstEarnOnEmpty.gems, 2);
const reloadedLedger = Ledger.mergeLedgers(firstEarnOnEmpty.reward_ledger, firstEarnOnEmpty.reward_ledger);
assert.equal(Ledger.computeBalances(reloadedLedger).gems, 2, "새 브라우저 첫 적립 후 새로고침해도 보석이 유지되어야 한다.");

// ── 12. 기기 A(기존 잔액 이관 base) + 기기 B(빈 base에서 신규 적립)가 병합되면 양쪽 모두 동일 잔액으로 수렴한다 ──
const deviceAWithEarn = apply(migrated, [{ key: "gems", delta: 3 }], { at: 1500, type: "grant" });
const mergedAB = Ledger.mergeStates(deviceAWithEarn, firstEarnOnEmpty);
const mergedBA = Ledger.mergeStates(firstEarnOnEmpty, deviceAWithEarn);
assert.equal(mergedAB.gems, 12, "기기 A(7+3)와 기기 B(+2) 병합 결과는 12여야 한다.");
assert.equal(mergedBA.gems, 12, "병합 순서를 바꿔도 동일하게 12여야 한다.");
assert.equal(mergedAB.youtube_minutes, 30);
assert.equal(mergedBA.youtube_minutes, 30);

// ── 13. 이미 오염된 legacy_snapshot_downward 원장은 정규화/병합 시 자동으로 자가 치유된다 ──
const poisonedCloud = {
  gems: 0,
  youtube_minutes: 0,
  snacks: 0,
  marble_plays: 0,
  bubble_plays: 0,
  custom_inventory: {},
  reward_ledger: {
    v: 1,
    base: { gems: 7, youtube_minutes: 30, snacks: 3, marble_plays: 1, bubble_plays: 2, custom_inventory: {} },
    base_at: 1000,
    events: [
      { id: "ev-bad-1", at: 0, key: "gems", delta: -7, type: "adjust", reason: "legacy_snapshot_downward" },
      { id: "ev-bad-2", at: 0, key: "youtube_minutes", delta: -30, type: "adjust", reason: "legacy_snapshot_downward" },
      { id: "ev-bad-3", at: 0, key: "snacks", delta: -3, type: "adjust", reason: "legacy_snapshot_downward" },
    ],
  },
};
const healed = migrate(poisonedCloud);
assert.equal(healed.gems, 7, "오염된 legacy_snapshot_downward 이벤트는 제거되어 원래 잔액이 복구되어야 한다.");
assert.equal(healed.youtube_minutes, 30);
assert.equal(healed.snacks, 3);
assert.equal(healed.reward_ledger.events.length, 0);

// ── 14. 메타데이터(shop_items, theme) 병합 시 undefined가 실제 배열/문자열을 이기면 안 된다 ──
const cloudWithCustomShop = {
  ...migrated,
  theme: "analog",
  shop_items: [
    { id: "youtube", name: "유튜브 10분", cost: 2 },
    { id: "custom_1", name: "레고 조립", cost: 5 },
  ],
};
const mergedMeta = Ledger.mergeStates({}, cloudWithCustomShop);
assert.equal(mergedMeta.theme, "analog", "빈 상태의 undefined theme가 원격 theme를 지우면 안 된다.");
assert.equal(mergedMeta.shop_items.length, 2, "빈 상태의 undefined shop_items가 원격 상점 목록을 지우면 안 된다.");

// ── 15. MAX_EVENTS(480) 초과 압축(fold) 시 같은 밀리초 경계 이벤트가 있어도 누락 없이 정확히 보존된다 ──
let heavy = migrate({ gems: 0, _updated_at: 100 });
for (let i = 0; i < 490; i += 1) {
  const ts = 1000 + Math.floor(i / 5);
  heavy = apply(heavy, [{ key: "gems", delta: 1 }], { at: ts, type: "grant" });
}
assert.equal(heavy.gems, 490, "압축 후에도 총 보석 합계 490이 정확해야 한다.");
assert.equal(Ledger.verify(heavy).ok, true);
const heavyMerged = Ledger.mergeStates(heavy, firstEarnOnEmpty);
assert.equal(heavyMerged.gems, 492, "압축된 원장과 다른 기기 원장 병합도 정확해야 한다.");

console.log("PASS: reward ledger keeps consumption durable and merge commutative/idempotent.");
