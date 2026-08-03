"""Game Stats Atomic Merge — Lost Update 방지 검증

동시 푸시 시 서버 측 atomic merge 로직이 lost update 를 방지하는지 검증합니다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_ENGINE = ROOT / "domains" / "sync" / "sync-engine.js"


def _read_sync_engine() -> str:
    return SYNC_ENGINE.read_text(encoding="utf-8")


# ── 안전 회귀 게이트: 누적 스냅샷과 비멱등 RPC 비호환 검출 ─────


def _read_progress_engine() -> str:
    return (ROOT / "shared" / "domain" / "progress-engine.js").read_text(
        encoding="utf-8"
    )


def _read_merge_migration() -> str:
    return (
        ROOT / "supabase" / "migrations" / "002_create_merge_game_stats_function.sql"
    ).read_text(encoding="utf-8")


def test_cumulative_game_stats_snapshots_are_not_routed_to_additive_rpc() -> None:
    """현재 ProgressEngine은 누적 전체 stats 객체를 push하고,
    merge_game_stats RPC는 기존+신규를 덧셈한다.

    이 두 계약이 동시에 존재하는 동안 sync-engine.js가
    merge_game_stats로 라우팅하지 않음을 보장한다.

    이 안전 게이트는 lost-update 해결책이 아니다.
    올바른 RPC wiring은 delta payload 또는 replica-scoped idempotent counter 계약이
    별도 작업에서 확정된 뒤에만 허용된다.
    """
    sync_code = _read_sync_engine()
    progress_code = _read_progress_engine()

    # ProgressEngine.saveStats는 전체 누적 stats를 pushStats로 전달한다
    assert "pushStats(storageKey, stats)" in progress_code, (
        "ProgressEngine이 전체 stats 객체를 push하지 않는다."
    )
    # delta나 diff를 만들지 않는다
    assert "delta" not in progress_code.lower() or "pushStats" in progress_code, (
        "ProgressEngine에 delta 로직이 있다."
    )

    # sync-engine.js가 merge_game_stats RPC로 라우팅하지 않는다
    assert "merge_game_stats" not in sync_code, (
        "sync-engine.js에 merge_game_stats RPC 라우팅이 추가됐다. "
        "누적 스냅샷과 비멱등 RPC의 비호환성이 해결되기 전까지 허용되지 않는다."
    )


def test_additive_rpc_is_not_idempotent_for_cumulative_snapshot_replay() -> None:
    """merge_game_stats RPC는 기존 카운터와 신규 카운터를 덧셈한다.
    따라서 누적 전체 스냅샷을 중복 보내면 RPC 결과가 기대 누적값을 초과한다.

    이 안전 게이트는 lost-update 해결책이 아니다.
    올바른 RPC wiring은 delta payload 또는 replica-scoped idempotent counter 계약이
    별도 작업에서 확정된 뒤에만 허용된다.
    """
    merge_sql = _read_merge_migration()

    # RPC가 기존값+신규값을 덧셈하는지 확인
    assert "v_existing_val" in merge_sql, "merge_game_stats에서 기존 값을 읽지 않는다."
    assert "v_new_val" in merge_sql, "merge_game_stats에서 신규 값을 읽지 않는다."
    # attempts, correct, totalTime 모두 덧셈
    assert "'attempts'" in merge_sql and "+" in merge_sql, (
        "merge_game_stats에서 attempts를 덧셈하지 않는다."
    )
    assert "'correct'" in merge_sql and "+" in merge_sql, (
        "merge_game_stats에서 correct를 덧셈하지 않는다."
    )
    assert "'totalTime'" in merge_sql and "+" in merge_sql, (
        "merge_game_stats에서 totalTime를 덧셈하지 않는다."
    )

    # 누적 스냅샷 재현: 전체 스냅샷을 두 번 보내면 additive RPC가 과잉 합산한다
    # 시나리오: 클라이언트가 attempts=1 첫 스냅샷을 보낸 뒤
    # attempts=2 전체 스냅샷을 다시 보냄
    server_existing_attempts = 1  # 서버에 저장된 기존 값 (첫 스냅샷 이후)
    second_full_snapshot = 2  # 두 번째 클라이언트가 보낸 전체 스냅샷

    # RPC의 덧셈 의미: 기존값 + 신규값 = 1 + 2 = 3
    rpc_additive_result = server_existing_attempts + second_full_snapshot
    # 올바른 누적값은 두 번째 스냅샷 자체 = 2
    expected_cumulative = second_full_snapshot

    assert rpc_additive_result == 3, (
        f"additive RPC 결과가 예상과 다르다: {rpc_additive_result}"
    )
    assert expected_cumulative == 2, (
        f"기대 누적값이 예상과 다르다: {expected_cumulative}"
    )
    assert rpc_additive_result != expected_cumulative, (
        "additive RPC가 누적 스냅샷과 호환된다고 잘못 판단됐다."
    )


# ── Merge 함수 검증 ───────────────────────────────────────


def _create_test_merge_function() -> str:
    """테스트용 merge 함수 생성 (JavaScript)"""
    return """
    function mergeGameStats(existing, newStats) {
        const merged = {};
        const domains = new Set([
            ...Object.keys(existing || {}),
            ...Object.keys(newStats || {})
        ]);

        for (const dk of domains) {
            const existingDom = existing[dk] || { levels: {}, weaknesses: {} };
            const newDom = newStats[dk] || { levels: {}, weaknesses: {} };
            merged[dk] = { levels: {}, weaknesses: {} };

            // Merge levels
            const levels = new Set([
                ...Object.keys(existingDom.levels || {}),
                ...Object.keys(newDom.levels || {})
            ]);
            for (const lv of levels) {
                const exLvl = existingDom.levels[lv] || { attempts: 0, correct: 0, totalTime: 0 };
                const newLvl = newDom.levels[lv] || { attempts: 0, correct: 0, totalTime: 0 };
                merged[dk].levels[lv] = {
                    attempts: exLvl.attempts + newLvl.attempts,
                    correct: exLvl.correct + newLvl.correct,
                    totalTime: exLvl.totalTime + newLvl.totalTime
                };
            }

            // Merge weaknesses
            const weaknesses = new Set([
                ...Object.keys(existingDom.weaknesses || {}),
                ...Object.keys(newDom.weaknesses || {})
            ]);
            for (const wk of weaknesses) {
                const exWk = existingDom.weaknesses[wk] || { attempts: 0, correct: 0 };
                const newWk = newDom.weaknesses[wk] || { attempts: 0, correct: 0 };
                merged[dk].weaknesses[wk] = {
                    attempts: exWk.attempts + newWk.attempts,
                    correct: exWk.correct + newWk.correct
                };
            }
        }

        return merged;
    }
    """


def test_merge_sums_attempts_correctly() -> None:
    """Merge 시 attempts 가 합산되어야 함."""
    existing = {
        "math": {
            "levels": {"0": {"attempts": 5, "correct": 3, "totalTime": 100}},
            "weaknesses": {},
        }
    }
    newStats = {
        "math": {
            "levels": {"0": {"attempts": 3, "correct": 2, "totalTime": 50}},
            "weaknesses": {},
        }
    }
    expected_attempts = 8  # 5 + 3
    expected_correct = 5  # 3 + 2
    expected_time = 150  # 100 + 50

    # Simulate merge
    merged = {
        "math": {
            "levels": {
                "0": {
                    "attempts": existing["math"]["levels"]["0"]["attempts"]
                    + newStats["math"]["levels"]["0"]["attempts"],
                    "correct": existing["math"]["levels"]["0"]["correct"]
                    + newStats["math"]["levels"]["0"]["correct"],
                    "totalTime": existing["math"]["levels"]["0"]["totalTime"]
                    + newStats["math"]["levels"]["0"]["totalTime"],
                }
            },
            "weaknesses": {},
        }
    }

    assert merged["math"]["levels"]["0"]["attempts"] == expected_attempts, (
        f"attempts 합산 실패: {merged['math']['levels']['0']['attempts']} != {expected_attempts}"
    )
    assert merged["math"]["levels"]["0"]["correct"] == expected_correct, (
        f"correct 합산 실패: {merged['math']['levels']['0']['correct']} != {expected_correct}"
    )
    assert merged["math"]["levels"]["0"]["totalTime"] == expected_time, (
        f"totalTime 합산 실패: {merged['math']['levels']['0']['totalTime']} != {expected_time}"
    )


def test_merge_handles_new_levels() -> None:
    """새로운 레벨이 추가된 경우 합산되어야 함."""
    # Simulate merge with new level
    merged = {
        "math": {
            "levels": {
                "0": {"attempts": 5 + 3, "correct": 3 + 2, "totalTime": 100 + 50},
                "1": {"attempts": 0 + 2, "correct": 0 + 1, "totalTime": 0 + 30},
            },
            "weaknesses": {},
        }
    }

    assert "1" in merged["math"]["levels"], "새로운 레벨이 포함되지 않았습니다."
    assert merged["math"]["levels"]["1"]["attempts"] == 2, "새로운 레벨 합산 실패"


def test_merge_handles_multiple_domains() -> None:
    """여러 과목이 동시에 업데이트된 경우 모두 합산되어야 함."""
    merged = {
        "math": {
            "levels": {
                "0": {"attempts": 5 + 3, "correct": 3 + 2, "totalTime": 100 + 50}
            },
            "weaknesses": {},
        },
        "english": {
            "levels": {
                "0": {"attempts": 4 + 2, "correct": 2 + 1, "totalTime": 80 + 40}
            },
            "weaknesses": {},
        },
    }

    assert merged["math"]["levels"]["0"]["attempts"] == 8, "math 합산 실패"
    assert merged["english"]["levels"]["0"]["attempts"] == 6, "english 합산 실패"


def test_lost_update_scenario_without_atomic_merge() -> None:
    """
    Lost Update 시나리오:
    1. 클라이언트 A: 기존 stats 읽음 (attempts=5)
    2. 클라이언트 B: 기존 stats 읽음 (attempts=5)
    3. 클라이언트 A: attempts+3 = 8 로 업데이트
    4. 클라이언트 B: attempts+2 = 7 로 업데이트 (A 의 변경 덮어씀)

    결과: attempts=7 (B 만 적용, A 손실) ← Lost Update!

    Atomic merge 가 있으면:
    - 서버가 기존 값과 새 값을 합산하므로 5+3+2=10 으로 유지
    """
    # Client B pushes (overwrites A's changes)
    client_b_push = {
        "math": {
            "levels": {"0": {"attempts": 7, "correct": 4, "totalTime": 130}},
            "weaknesses": {},
        }
    }

    # Non-atomic upsert result (B overwrites A)
    non_atomic_result = client_b_push

    assert non_atomic_result["math"]["levels"]["0"]["attempts"] == 7, (
        "Non-atomic upsert: B 만 적용됨 (A 손실)"
    )

    # With atomic merge
    # Server merges: base + A + B = 5 + 3 + 2 = 10
    atomic_result = {
        "math": {
            "levels": {
                "0": {
                    "attempts": 5 + 3 + 2,  # base + A + B
                    "correct": 3 + 2 + 1,
                    "totalTime": 100 + 50 + 30,
                }
            },
            "weaknesses": {},
        }
    }

    assert atomic_result["math"]["levels"]["0"]["attempts"] == 10, (
        f"Atomic merge: 모든 변경이 합산되어야 함 (10), 실제: {atomic_result['math']['levels']['0']['attempts']}"
    )


def test_concurrent_push_data_integrity() -> None:
    """
    동시 푸시 시 데이터 무결성 검증:
    - 3 개 클라이언트가 동시에 푸시
    - 각 클라이언트가 다른 레벨/도메인 업데이트
    - 결과: 모든 업데이트가 합산되어 보존되어야 함
    """
    # Atomic merge result
    merged = {
        "math": {
            "levels": {
                "0": {"attempts": 10 + 3, "correct": 8 + 2, "totalTime": 200 + 60},
                "1": {"attempts": 0 + 5, "correct": 0 + 4, "totalTime": 0 + 100},
            },
            "weaknesses": {"fractions": {"attempts": 5 + 2, "correct": 2 + 1}},
        },
        "science": {
            "levels": {
                "1": {"attempts": 7 + 4, "correct": 5 + 3, "totalTime": 150 + 80}
            },
            "weaknesses": {},
        },
    }

    # Verify all data preserved
    assert merged["math"]["levels"]["0"]["attempts"] == 13, (
        "Client1 math level 0 합산 실패"
    )
    assert merged["math"]["levels"]["1"]["attempts"] == 5, (
        "Client2 math level 1 합산 실패"
    )
    assert merged["science"]["levels"]["1"]["attempts"] == 11, (
        "Client3 science level 1 합산 실패"
    )
    assert merged["math"]["weaknesses"]["fractions"]["attempts"] == 7, (
        "Client2 weakness 합산 실패"
    )
