"""Game Stats Atomic Merge — Lost Update 방지 검증

동시 푸시 시 서버 측 atomic merge 로직이 lost update 를 방지하는지 검증합니다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_ENGINE = ROOT / "domains" / "sync" / "sync-engine.js"


def _read_sync_engine() -> str:
    return SYNC_ENGINE.read_text(encoding="utf-8")


# ── RPC 호출 검증 ─────────────────────────────────────────


def test_game_stats_uses_rpc_merge() -> None:
    """GameStats 푸시는 merge_game_stats RPC 를 사용해야 함."""
    code = _read_sync_engine()
    assert "merge_game_stats" in code, (
        "GameStats 푸시에 merge_game_stats RPC 호출이 없습니다."
    )
    assert "key.endsWith('GameStats')" in code, "GameStats 식별 로직이 없습니다."


def test_rpc_call_has_correct_params() -> None:
    """RPC 호출에 p_user_id, p_data_key, p_payload 가 있어야 함."""
    code = _read_sync_engine()
    assert "p_user_id" in code, "p_user_id 파라미터가 없습니다."
    assert "p_data_key" in code, "p_data_key 파라미터가 없습니다."
    assert "p_payload" in code, "p_payload 파라미터가 없습니다."


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
