/**
 * @fileoverview 보상 감사 원장(RewardLedger) 순수 로직 검증.
 *
 * 고정하는 계약:
 * - 기준점 초기화(BASELINE_RESET_EPOCH = 1): 이전 누적 보상 스냅샷·구 epoch 원장은 모두 0으로 초기화되며
 *   이전 잔액은 reset_history 감사 증적으로만 남는다.
 * - 잔액은 현행 epoch의 "획득/사용 델타의 합"이며, 소비는 어떤 스냅샷에도 되살아나지 않는다.
 * - 병합은 교환 가능(commutative)·결합 가능·멱등(idempotent)하며, 상위 reset_epoch가 하위 epoch를 지배한다.
 * - 빈 브라우저({})는 현행 epoch의 항등원으로 동작하여 초기화 이후 적립한 보상을 0으로 깎지 않는다.
 * - auditReport / auditCsv가 초 단위 타임스탬프, 변경 전/후 잔액, 사유·출처·영수증을 정확히 산출한다.
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

// ── 0. 기준점 초기화: 이전 누적 스냅샷 및 구 epoch 원장은 즉시 0으로 초기화되고 증적이 남는다 ──
const preCutoverRaw = { gems: 7, youtube_minutes: 30, snacks: 3, marble_plays: 2, bubble_plays: 1, _updated_at: 1000 };
const cutoverState = migrate(preCutoverRaw);
for (const key of Ledger.FIELD_KEYS) {
  assert.equal(cutoverState[key], 0, `이전 누적 ${key}는 기준점 전환 시 0으로 초기화되어야 한다.`);
}
assert.equal(cutoverState.reward_ledger.v, 1);
assert.equal(cutoverState.reward_ledger.reset_epoch, Ledger.BASELINE_RESET_EPOCH);
assert.equal(cutoverState.reward_ledger.reset_history.length, 1);
assert.equal(cutoverState.reward_ledger.reset_history[0].previous_balances.gems, 7);
assert.equal(Ledger.verify(cutoverState).ok, true, "초기화 직후 잔액과 원장이 일치해야 한다.");

// 구 epoch(reset_epoch 미지정) 원장도 동일하게 0으로 정리된다.
const preCutoverLedgerState = {
  gems: 15,
  youtube_minutes: 40,
  snacks: 4,
  reward_ledger: {
    v: 1,
    base: { gems: 10, youtube_minutes: 40, snacks: 4, marble_plays: 0, bubble_plays: 0, custom_inventory: {} },
    base_at: 500,
    events: [{ id: "old-ev-1", at: 900, key: "gems", delta: 5, type: "grant", reason: "old_quiz" }],
  },
};
const cutoverFromOldLedger = migrate(preCutoverLedgerState);
assert.equal(cutoverFromOldLedger.gems, 0);
assert.equal(cutoverFromOldLedger.youtube_minutes, 0);
assert.equal(cutoverFromOldLedger.snacks, 0);
assert.equal(cutoverFromOldLedger.reward_ledger.events.length, 0);

// ── 1. 초기화 이후 적립한 보상은 정확히 보존된다 ──
const seeded = apply(
  {},
  [
    { key: "gems", delta: 7 },
    { key: "youtube_minutes", delta: 30 },
    { key: "snacks", delta: 3 },
    { key: "marble_plays", delta: 2 },
    { key: "bubble_plays", delta: 1 },
  ],
  { at: 1000, type: "grant", reason: "post_reset_earn", source: "math", detail: "초기화 이후 학습 획득" }
);
assert.equal(seeded.gems, 7);
assert.equal(seeded.youtube_minutes, 30);
assert.equal(seeded.snacks, 3);
assert.equal(Ledger.verify(seeded).ok, true);

// ── 2. 전부 사용한 뒤: 어떤 오래된 스냅샷도 잔액을 되살리지 못한다 ──
const emptied = apply(
  seeded,
  [
    { key: "gems", delta: -7 },
    { key: "youtube_minutes", delta: -30 },
    { key: "snacks", delta: -3 },
    { key: "marble_plays", delta: -2 },
    { key: "bubble_plays", delta: -1 },
  ],
  { at: 2000, type: "consume", reason: "parent_consume", detail: "전량 사용" }
);
for (const key of Ledger.FIELD_KEYS) {
  assert.equal(emptied[key], 0, `${key}는 사용 후 0이어야 한다.`);
}

const staleLedgerSnapshot = { ...seeded, _updated_at: 999999 };
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
const afterGrant = apply(emptied, [{ key: "gems", delta: 2 }], {
  at: 3000,
  type: "grant",
  reason: "math_daily_goal",
  source: "math",
  receipt: "receipt-math-goal-1",
  detail: "수학 오늘의 목표 달성 (덧셈 5문제)",
});
assert.equal(afterGrant.gems, 2, "획득 이벤트 1건만큼만 증가해야 한다.");
const regranted = Ledger.mergeStates(afterGrant, staleLegacySnapshot);
assert.equal(regranted.gems, 2, "획득 후에도 오래된 스냅샷은 초과 지급하지 못한다.");

// ── 4. 병합은 교환 가능하고 멱등하다 ──
const left = apply(seeded, [{ key: "gems", delta: -2 }], { at: 4000, type: "consume" });
const right = apply(seeded, [{ key: "gems", delta: 3 }], { at: 5000, type: "grant" });
const mergedLR = Ledger.mergeStates(left, right);
const mergedRL = Ledger.mergeStates(right, left);
assert.equal(mergedLR.gems, mergedRL.gems, "병합 순서가 결과를 바꾸면 안 된다.");
assert.equal(mergedLR.gems, 8, "획득과 사용은 모두 반영되어야 한다(7 - 2 + 3).");
assert.equal(Ledger.mergeStates(mergedLR, mergedLR).gems, mergedLR.gems, "같은 상태를 다시 병합해도 값이 변하지 않아야 한다.");
assert.equal(Ledger.mergeStates(mergedLR, left).gems, mergedLR.gems, "이미 포함한 이벤트를 다시 병합해도 중복 계산하지 않아야 한다.");

// ── 5. 영수증은 합집합 병합(중복 지급 방지) ──
const receiptA = Ledger.mergeReceipts(
  { "reward.daily-streak.2026-10-23": { receiptId: "reward.daily-streak.2026-10-23", grantedAt: 10, grants: [] } },
  {}
);
const receiptB = Ledger.mergeReceipts(
  {},
  { "reward.daily-streak.2026-10-23": { receiptId: "reward.daily-streak.2026-10-23", grantedAt: 10, grants: [] } }
);
assert.deepEqual(Object.keys(receiptA), Object.keys(receiptB), "영수증은 어느 쪽에만 있어도 보존되어야 한다.");
const mergedStateWithReceipts = Ledger.mergeStates(
  { ...afterGrant, claimed_receipts: { r1: { receiptId: "r1", grantedAt: 1, grants: [] } } },
  { ...afterGrant, claimed_receipts: {} }
);
assert.ok(mergedStateWithReceipts.claimed_receipts.r1, "영수증은 병합에서 사라지면 안 된다.");

// ── 6. 사용자 정의 보상도 같은 원장 규칙을 따른다 ──
const withCustom = apply(seeded, [{ key: "custom:sticker", delta: 5 }], { at: 6000, type: "grant" });
assert.equal(withCustom.custom_inventory.sticker, 5);
const customUsed = apply(withCustom, [{ key: "custom:sticker", delta: -5 }], { at: 7000, type: "consume" });
assert.equal(customUsed.custom_inventory.sticker || 0, 0);
const customMerged = Ledger.mergeStates(customUsed, withCustom);
assert.equal(customMerged.custom_inventory.sticker || 0, 0, "사용한 사용자 정의 보상도 되살아나면 안 된다.");

// ── 7. 음수 잔액은 0으로 고정되고, 원장 합계와 표시 잔액이 어긋나지 않는다 ──
const overdrawn = apply(apply(seeded, [{ key: "snacks", delta: -3 }], { at: 8000 }), [{ key: "snacks", delta: -3 }], { at: 9000 });
assert.equal(overdrawn.snacks, 0);
assert.equal(Ledger.verify(overdrawn).ok, true);

// ── 8. 감사 기록(activity & auditReport & auditCsv)은 전후 잔액·시각·상세 사유를 정확히 계산한다 ──
const activity = Ledger.activity(afterGrant, { limit: 3 });
assert.equal(activity.length, 3);
assert.equal(activity[0].key, "gems");
assert.equal(activity[0].delta, 2);
assert.equal(activity[0].balanceBefore, 0);
assert.equal(activity[0].balanceAfter, 2);
assert.equal(activity[0].source, "math");
assert.match(activity[0].detail, /수학 오늘의 목표 달성/);

const fullAudit = Ledger.auditReport(afterGrant, { type: "grant", key: "gems" });
assert.equal(fullAudit.ok, true);
assert.equal(fullAudit.epoch, 1);
assert.equal(fullAudit.entries.length, 2);
const gemSummary = fullAudit.summaries.find((s) => s.key === "gems");
assert.equal(gemSummary.earned, 9);
assert.equal(gemSummary.consumed, 7);
assert.equal(gemSummary.actual, 2);
assert.equal(gemSummary.matches, true);

const csv = Ledger.auditCsv(afterGrant, {});
assert.match(csv, /발생시각\(로컬\)/);
assert.match(csv, /수학 오늘의 목표 달성/);
assert.match(csv, /receipt-math-goal-1/);

// ── 9. 조작된(원장과 불일치) 상태는 검증에서 잡히고, 잔액을 늘리지 못한다 ──
const tampered = { ...afterGrant, gems: 99 };
const tamperedReport = Ledger.verify(tampered);
assert.equal(tamperedReport.ok, false);
assert.equal(tamperedReport.mismatches[0].key, "gems");
const adopted = migrate(tampered);
assert.equal(adopted.gems, 2, "원장 합계를 넘는 외부 값은 반영되지 않아야 한다.");
assert.equal(Ledger.verify(adopted).ok, true);
assert.ok(
  !adopted.reward_ledger.events.some((event) => event.reason === "external_write"),
  "증가 방향 외부 쓰기는 이벤트로 승격되지 않아야 한다."
);

const shrunk = migrate({ ...afterGrant, gems: 0 });
assert.equal(shrunk.gems, 0);
assert.ok(
  shrunk.reward_ledger.events.some((event) => event.reason === "external_write" && event.delta < 0),
  "감소 방향 외부 쓰기는 감사 이벤트로 남아야 한다."
);

// ── 10. 빈 브라우저({})와 클라우드 현행 원장을 병합할 때 0으로 깎아내리면 안 된다(항등원 보장) ──
const freshBrowserMerged = Ledger.mergeStates({}, seeded);
assert.equal(freshBrowserMerged.gems, 7, "새 브라우저의 빈 상태({})가 초기화 이후 적립 보석을 0으로 만들면 안 된다.");
assert.equal(freshBrowserMerged.youtube_minutes, 30);
assert.equal(freshBrowserMerged.snacks, 3);
const reverseFreshMerged = Ledger.mergeStates(seeded, {});
assert.equal(reverseFreshMerged.gems, 7);
assert.equal(reverseFreshMerged.youtube_minutes, 30);
assert.equal(reverseFreshMerged.snacks, 3);

// ── 11. 새 브라우저에서 첫 보상을 얻은 직후 mergeLedgers(새로고침 복구)해도 이벤트가 증발하면 안 된다 ──
const firstEarnOnEmpty = apply({}, [{ key: "gems", delta: 2 }], { at: 5000, type: "grant", reason: "math_goal" });
assert.equal(firstEarnOnEmpty.gems, 2);
const reloadedLedger = Ledger.mergeLedgers(firstEarnOnEmpty.reward_ledger, firstEarnOnEmpty.reward_ledger);
assert.equal(Ledger.computeBalances(reloadedLedger).gems, 2);

// ── 12. 기기 A + 기기 B가 병합되면 양쪽 모두 동일 잔액으로 수렴한다 ──
const deviceAWithEarn = apply(seeded, [{ key: "gems", delta: 3 }], { at: 1500, type: "grant" });
const mergedAB = Ledger.mergeStates(deviceAWithEarn, firstEarnOnEmpty);
const mergedBA = Ledger.mergeStates(firstEarnOnEmpty, deviceAWithEarn);
assert.equal(mergedAB.gems, 12, "기기 A(7+3)와 기기 B(+2) 병합 결과는 12여야 한다.");
assert.equal(mergedBA.gems, 12);

// ── 13. 현행 epoch에서 오염된 legacy_snapshot_downward 이벤트는 정규화 시 자동 제거된다 ──
const poisonedCurrentEpoch = {
  gems: 0,
  youtube_minutes: 0,
  snacks: 0,
  marble_plays: 0,
  bubble_plays: 0,
  custom_inventory: {},
  reward_ledger: {
    v: 1,
    reset_epoch: 1,
    events: [
      { id: "ev-good-1", at: 1000, key: "gems", delta: 7, type: "grant", reason: "math_daily_goal" },
      { id: "ev-bad-1", at: 1100, key: "gems", delta: -7, type: "adjust", reason: "legacy_snapshot_downward" },
    ],
  },
};
const healed = migrate(poisonedCurrentEpoch);
assert.equal(healed.gems, 7);
assert.equal(healed.reward_ledger.events.length, 1);

// ── 14. 메타데이터(shop_items, theme) 병합 시 undefined가 실제 배열/문자열을 이기면 안 된다 ──
const cloudWithCustomShop = {
  ...seeded,
  theme: "analog",
  shop_items: [
    { id: "youtube", name: "유튜브 10분", cost: 2 },
    { id: "custom_1", name: "레고 조립", cost: 5 },
  ],
};
const mergedMeta = Ledger.mergeStates({}, cloudWithCustomShop);
assert.equal(mergedMeta.theme, "analog");
assert.equal(mergedMeta.shop_items.length, 2);

// ── 15. MAX_EVENTS(1000) 초과 압축(fold) 시 같은 밀리초 경계 이벤트가 있어도 누락 없이 보존된다 ──
let heavy = migrate({});
for (let i = 0; i < 1020; i += 1) {
  const ts = 1000 + Math.floor(i / 5);
  heavy = apply(heavy, [{ key: "gems", delta: 1 }], { at: ts, type: "grant" });
}
assert.equal(heavy.gems, 1020, "압축 후에도 총 보석 합계 1020이 정확해야 한다.");
assert.ok(heavy.reward_ledger.folded_count > 0);
assert.equal(Ledger.verify(heavy).ok, true);
const heavyMerged = Ledger.mergeStates(heavy, firstEarnOnEmpty);
assert.equal(heavyMerged.gems, 1022);

// ── 16. 보호자 수동 초기화(resetState): reset_epoch가 증가하며 하위 epoch 잔액을 완전히 제압한다 ──
const resetEpoch2 = Ledger.resetState(mergedAB, {
  at: 20000,
  actor: "guardian",
  reason: "guardian_manual_reset",
  note: "주간 보상 정산 초기화",
});
assert.equal(resetEpoch2.gems, 0);
assert.equal(resetEpoch2.youtube_minutes, 0);
assert.equal(resetEpoch2.reward_ledger.reset_epoch, 2);
assert.equal(Ledger.mergeStates(resetEpoch2, mergedAB).gems, 0, "하위 epoch 기기가 이전 잔액을 부활시키면 안 된다.");
assert.equal(Ledger.mergeStates(mergedAB, resetEpoch2).gems, 0, "병합 순서와 무관하게 상위 epoch가 승리해야 한다.");

const postResetEarn = apply(resetEpoch2, [{ key: "gems", delta: 4 }], { at: 21000, type: "grant", reason: "daily_streak" });
assert.equal(Ledger.mergeStates(postResetEarn, mergedAB).gems, 4, "재초기화 이후 새로 적립한 보석만 남는다.");

console.log("PASS: reward ledger enforces epoch reset, audit trail, and commutative merge.");
