from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_describes_aidengame_product_identity() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "어린이 학습 게임 놀이터" in readme
    assert "Agentic Development System Bootstrap" not in readme
    assert (
        "국어" in readme and "수학" in readme and "영어" in readme and "과학" in readme
    )


def test_readme_tracks_current_runtime_and_verification_paths() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "- 메인 허브: `index.html`" in readme
    assert "- 우주 탐험 페이지: `experiments/space-explorer/index.html`" in readme
    assert "- 우주 탐험 모듈 엔트리: `experiments/space-explorer/main.js`" in readme
    assert "- 배포 라우팅 설정: `vercel.json`" in readme
    assert "루트 `verify.sh`" in readme
    assert "- 우주 탐험 페이지: `experiments/space-explorer.html`" not in readme

    for path in (
        ROOT / "index.html",
        ROOT / "experiments/space-explorer/index.html",
        ROOT / "experiments/space-explorer/main.js",
        ROOT / "vercel.json",
        ROOT / "verify.sh",
    ):
        assert path.is_file(), f"README references missing runtime path: {path}"


def test_readme_includes_route_classification_table() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "운영 / 실험 / 레거시 경로 구분표" in readme
    assert "| 구분 | 경로 | 상태 | 용도 |" in readme
    assert (
        "| 우주 탐험 실험 페이지 | `experiments/space-explorer/index.html` | "
        "운영중·개발 동결 |"
    ) in readme
    assert (
        "| 과거 우주 탐험 alias | `/space-explorer.html`, "
        "`experiments/space-explorer.html` | 없음 |"
    ) in readme
