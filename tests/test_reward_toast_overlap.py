from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REWARD_UI = ROOT / "domains" / "reward" / "reward_ui.js"


def test_showtoast_clears_existing_toasts_before_adding_new() -> None:
    """중복 정답 시 토스트가 겹치지 않도록 기존 토스트 제거 로직이 존재해야 함."""
    code = REWARD_UI.read_text(encoding="utf-8")

    # showToast 함수 추출
    start = code.index("function showToast(msg)")
    block = code[start : start + 600]

    # 기존 .reward-toast 요소를 제거하는 로직이 있어야 함
    has_cleanup = (
        "querySelectorAll('.reward-toast')" in block
        or "querySelector('.reward-toast')" in block
        or "document.querySelectorAll" in block
        and "remove" in block
        or ".reward-toast" in block
        and "forEach" in block
        or ".reward-toast" in block
        and "remove()" in block
    )

    assert has_cleanup, (
        "showToast() 시작 시 기존 .reward-toast 요소를 제거하는 로직이 없습니다. "
        "중복 정답 시 토스트가 겹쳐 표시됩니다."
    )
