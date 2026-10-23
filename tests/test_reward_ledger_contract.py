"""보상 원장(RewardLedger) 배선 계약 — 소비가 되살아나지 않는 구조를 고정한다.

이 테스트가 잡는 회귀:
- 보상 저장 경로가 다시 "메모리 스냅샷 전체 덮어쓰기"로 돌아가는 경우
- 클라우드 병합이 값 기반(`Math.max`)으로 돌아가 사용 기록을 덮는 경우
- 보상 화면/게임 화면이 원장 스크립트 없이 로드되어 소비 이벤트가 유실되는 경우
- 보호자 화면이 오래된 인벤토리 스냅샷을 다시 저장하는 경우
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REWARD_JS = ROOT / "domains" / "reward" / "reward.js"
REWARD_UI_JS = ROOT / "domains" / "reward" / "reward_ui.js"
SYNC_ENGINE = ROOT / "domains" / "sync" / "sync-engine.js"
GUARDIAN_JS = ROOT / "domains" / "reward" / "guardian" / "guardian.js"
LEDGER_JS = ROOT / "shared" / "domain" / "reward-ledger.js"
LEDGER_MJS = ROOT / "tests" / "test_reward_ledger.mjs"
ACTIVITY_UI_MJS = ROOT / "tests" / "test_reward_activity_ui.mjs"
GUARDIAN_AUDIT_MJS = ROOT / "tests" / "test_guardian_reward_audit.mjs"

ENTRY_POINTS = [
    ROOT / "index.html",
    ROOT / "domains" / "math" / "index.html",
    ROOT / "domains" / "korean" / "index.html",
    ROOT / "domains" / "english" / "index.html",
    ROOT / "domains" / "science" / "index.html",
    ROOT / "domains" / "english" / "weekly-test" / "index.html",
    ROOT / "domains" / "reward" / "guardian" / "index.html",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_reward_ledger_node_suite() -> None:
    """원장 병합/감사 규칙(교환 가능·멱등·소비 보존)을 Node에서 검증한다."""
    node = shutil.which("node")
    assert node is not None, "node is required"
    proc = subprocess.run(
        [node, str(LEDGER_MJS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"{proc.stderr}\n{proc.stdout}"
    assert "PASS:" in proc.stdout


def test_reward_activity_ui_node_suite() -> None:
    """보상 화면이 최근 획득/사용 기록을 실제로 렌더링하는지 확인한다."""
    node = shutil.which("node")
    assert node is not None, "node is required"
    proc = subprocess.run(
        [node, str(ACTIVITY_UI_MJS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"{proc.stderr}\n{proc.stdout}"
    assert "PASS:" in proc.stdout


def test_guardian_reward_audit_node_suite() -> None:
    """보호자 감사 패널, 5개 보상 프로듀서, CSV/JSON 내보내기, 전체 초기화를 검증한다."""
    node = shutil.which("node")
    assert node is not None, "node is required"
    proc = subprocess.run(
        [node, str(GUARDIAN_AUDIT_MJS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"{proc.stderr}\n{proc.stdout}"
    assert "PASS:" in proc.stdout


def test_reward_core_commits_through_ledger_and_verifies_write() -> None:
    """보상 코어는 델타를 원장에 커밋하고, 저장 후 이벤트 잔존 여부를 확인한다."""
    code = _read(REWARD_JS)
    assert (
        "RewardLedger.mergeStates" not in code
    )  # 모듈 참조는 ledger() 헬퍼를 통해서만 한다
    assert "L.mergeStates(disk, memory" in code, (
        "저장 시 디스크 원장과 메모리 원장을 병합해야 한다."
    )
    assert "L.diffSnapshots(beforeSnapshot, L.snapshot(state))" in code, (
        "변경분을 델타로 계산해야 한다."
    )
    assert "L.applyDeltas(next, deltas" in code, "델타는 원장 이벤트로 확정되어야 한다."
    assert "hasEventById" in code, "저장 후 이벤트 잔존 검증이 있어야 한다."
    assert "duplicateReceipt" in code, "다른 탭이 먼저 지급한 영수증을 감지해야 한다."
    assert "grantOnce" in code
    assert "normalizeYoutubeMinutes" in code
    assert "getRecentActivity" in code
    assert "LEDGER_JOURNAL_KEY" in code, "원장 복구 저널이 있어야 한다."
    assert "L.mergeLedgers(journal, base.reward_ledger)" in code


def test_sync_engine_merges_study_rewards_with_ledger_not_max() -> None:
    """클라우드 병합은 원장 병합을 사용하고, 값 기반 최댓값 병합을 쓰지 않는다."""
    code = _read(SYNC_ENGINE)
    assert "rewardLedger.mergeStates(L, R, { adoptFields: true })" in code
    assert "mergeStudyRewardsPayload(localParsed || {}, row.payload)" in code
    assert "localTime > dbTime" in code  # 병합 후 재푸시 경로
    # study_rewards 경로에는 값 기반 Math.max 병합이 남아 있으면 안 된다.
    merge_fn_start = code.index("function mergeStudyRewardsPayload")
    merge_fn_end = code.index("function normalizePulledRows")
    merge_fn = code[merge_fn_start:merge_fn_end]
    assert "Math.max(L.gems" not in merge_fn
    assert "Math.max(L.snacks" not in merge_fn
    assert "minOf" in merge_fn, "원장이 없을 때도 하향(최솟값) 병합으로 동작해야 한다."


def test_reward_install_pages_load_ledger_before_reward_module() -> None:
    """보상 스택을 쓰는 모든 진입 화면은 원장을 먼저 로드한다."""
    for path in ENTRY_POINTS:
        html = _read(path)
        assert "reward-ledger.js" in html, f"{path}가 보상 원장을 로드하지 않는다."
        ledger_idx = html.index("reward-ledger.js")
        reward_idx = html.find("domains/reward/reward")
        if reward_idx != -1:
            assert ledger_idx < reward_idx, (
                f"{path}에서 원장이 보상 코어보다 먼저 로드되어야 한다."
            )
        sync_idx = html.find("domains/sync/sync-engine.js")
        if sync_idx != -1:
            assert ledger_idx < sync_idx, (
                f"{path}에서 원장이 동기화 엔진보다 먼저 로드되어야 한다."
            )


def test_guardian_edits_merge_instead_of_overwriting_inventory_snapshot() -> None:
    """보호자 화면의 보상 저장은 잔액 스냅샷을 통째로 덮어쓰지 않는다."""
    code = _read(GUARDIAN_JS)
    assert "Ledger.mergeStates(fresh, memory" in code
    assert "Ledger.setQuantity(memory, key, value" in code
    assert "function setRewardInventory" in code
    # 원장이 없는 환경에서만 기존 스냅샷 저장으로 폴백하고,
    # 정상 경로는 병합 결과(merged)를 저장해야 한다.
    assert "localStorage.setItem('study_rewards', JSON.stringify(merged))" in code
    assert "if (!Ledger) {" in code


def test_ui_exposes_receipt_history_and_double_click_guard() -> None:
    """보상 화면은 최근 획득/사용 기록을 보여주고, 중복 클릭 차감을 막는다."""
    code = _read(REWARD_UI_JS)
    assert "function renderActivityLog(state)" in code
    assert "getRecentActivity" in code
    assert "verifyIntegrity" in code
    assert "if (deductYtBtn.disabled) return;" in code
    assert "RewardSystem.normalizeYoutubeMinutes()" in code


def test_daily_gem_sources_use_receipt_based_grants() -> None:
    """출석·다양성·마일스톤 보석은 영수증 기반 지급(중복 방지)을 사용한다."""
    streak = _read(ROOT / "shared" / "domain" / "daily-streak.js")
    diversity = _read(ROOT / "shared" / "domain" / "diversity-reward.js")
    milestone = _read(ROOT / "shared" / "domain" / "milestone-tracker.js")

    assert "reward.daily-streak." in streak
    assert "RewardSystem.grantOnce(" in streak
    assert "reward.diversity." in diversity
    assert "RewardSystem.grantOnce(" in diversity
    assert "reward.milestone." in milestone
    assert "RewardSystem.grantOnce(" in milestone

    # 원장 모듈 자체에 지급 API가 있어야 한다.
    ledger = _read(LEDGER_JS)
    assert "function mergeStates" in ledger
    assert "function applyDeltas" in ledger
    assert "function verify" in ledger
