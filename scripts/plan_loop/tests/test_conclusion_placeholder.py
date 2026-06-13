import unittest

from scripts.plan_loop.plan_lint import _is_conclusion_placeholder


class TestConclusionPlaceholderDetection(unittest.TestCase):
    """Test _is_conclusion_placeholder — [PASS], [FAIL] 등 결과 마커 허용."""

    def test_pass_marker_allowed(self):
        """[PASS] 로 시작하면 통과 — 실제 Conclusion 값."""
        self.assertFalse(_is_conclusion_placeholder("[PASS] tests/api/test_foo.py 생성."))

    def test_fail_marker_allowed(self):
        """[FAIL] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[FAIL] waiting에 encounter_id 누락."))

    def test_skip_marker_allowed(self):
        """[SKIP] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[SKIP] 검증 생략 — 미구현 API."))

    def test_ok_marker_allowed(self):
        """[OK] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[OK] lint 0 오류."))

    def test_done_marker_allowed(self):
        """[DONE] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[DONE] 모든 테스트 Green."))

    def test_generic_uppercase_still_flagged(self):
        """[TBD], [TODO] 등 일반 대문자 마커는 여전히 placeholder."""
        self.assertTrue(_is_conclusion_placeholder("[TBD]"))
        self.assertTrue(_is_conclusion_placeholder("[TODO]"))
        self.assertTrue(_is_conclusion_placeholder("[VALUE]"))

    def test_korean_placeholder_still_flagged(self):
        """[판정 — 비개발자용 요약...] 은 여전히 placeholder."""
        self.assertTrue(_is_conclusion_placeholder("[판정 — 비개발자용 요약. 검증 결과]"))

    def test_empty_is_placeholder(self):
        """빈 문자열은 placeholder."""
        self.assertTrue(_is_conclusion_placeholder(""))

    def test_normal_text_passes(self):
        """일반 텍스트는 placeholder 아님."""
        self.assertFalse(_is_conclusion_placeholder("테스트 6건 추가, 검증 통과."))

    def test_korean_success_marker_allowed(self):
        """[성공] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[성공] 테스트 6건 통과, exit 0."))

    def test_korean_fail_marker_allowed(self):
        """[실패] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[실패] waiting에 encounter_id 누락."))

    def test_korean_abort_marker_allowed(self):
        """[중단] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[중단] 의존 Task 실패로 스킵."))

    def test_korean_skip_marker_allowed(self):
        """[생략] 로 시작하면 통과."""
        self.assertFalse(_is_conclusion_placeholder("[생략] 미구현 API — 구조만 검증."))


if __name__ == "__main__":
    unittest.main()
