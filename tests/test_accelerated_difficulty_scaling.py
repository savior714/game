"""Test Accelerated Difficulty Scaling

가속화된 난이도 승급 조건(MIN_DATA = 2, Flow Boost 가속)을 검증합니다.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_ENGINE = ROOT / "shared" / "domain" / "progress-engine.js"
DOMAINS_ENGINES = [
    ROOT / "domains" / "math" / "engine.js",
    ROOT / "domains" / "english" / "engine.js",
    ROOT / "domains" / "korean" / "engine.js",
    ROOT / "domains" / "science" / "engine.js",
]


def test_min_data_accelerated_to_2() -> None:
    """4개 과목 엔진 모두 MIN_DATA가 2로 설정되어 빠른 승급 판단을 보장한다."""
    for engine_path in DOMAINS_ENGINES:
        content = engine_path.read_text(encoding="utf-8")
        assert (
            "const MIN_DATA           = 2;" in content
            or "const MIN_DATA = 2;" in content
        ), f"{engine_path.relative_to(ROOT)}의 MIN_DATA가 2로 설정되지 않았습니다."


def test_progress_engine_flow_boost_acceleration() -> None:
    """ProgressEngine.getDifficultyLevel 부스트 가속화 로직을 실행하여 검증한다."""
    node_script = f"""
    const window = {{}};
    {PROGRESS_ENGINE.read_text(encoding="utf-8")}

    const emptyStats = window.ProgressEngine.emptyStats(['math']);
    const opts = {{ upThreshold: 0.85, downThreshold: 0.75 }};

    const r0 = window.ProgressEngine.getDifficultyLevel(emptyStats, 'math', 2, 0, [], opts);
    const r1 = window.ProgressEngine.getDifficultyLevel(emptyStats, 'math', 2, 0, [true], opts);
    const r2 = window.ProgressEngine.getDifficultyLevel(emptyStats, 'math', 2, 0, [true, true], opts);
    const r3 = window.ProgressEngine.getDifficultyLevel(emptyStats, 'math', 2, 0, [true, true, true], opts);
    const r5 = window.ProgressEngine.getDifficultyLevel(emptyStats, 'math', 2, 0, [true, true, true, true, true], opts);

    console.log(JSON.stringify({{ r0, r1, r2, r3, r5 }}));
    """

    res = subprocess.run(
        ["node", "-e", node_script], capture_output=True, text=True, check=True
    )
    out = json.loads(res.stdout.strip())

    assert out["r0"] == 0, "기초 레벨 0"
    assert out["r1"] == 0, "1개 정답 시 boost 0"
    assert out["r2"] == 1, "2개 정답 시 boost 1 (accelerated)"
    assert out["r3"] == 2, "3개 정답 시 boost 2 (accelerated)"
    assert out["r5"] == 3, "5개 정답 시 boost 3 (accelerated)"
