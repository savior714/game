"""GFM 표 → 불릿 카드 변환기 유닛 테스트."""

import unittest

from scripts.linear_sync.lib.table_formatter import (
    convert_gfm_table_to_bullets,
    format_linear_body,
)


class TestConvertGfmTableToBullets(unittest.TestCase):
    """GFM 표 변환기 테스트."""

    def test_simple_two_column_table(self):
        """단순 2 열 표 변환."""
        input_text = """
> 설명
>
> | Task | Verify |
> |------|--------|
> | 구현 | 테스트 |
> | 배포 | 모니터링 |
"""
        result = convert_gfm_table_to_bullets(input_text)
        self.assertIn("**Task**: 구현", result)
        self.assertIn("**Verify**: 테스트", result)
        self.assertIn("**Task**: 배포", result)
        self.assertIn("**Verify**: 모니터링", result)

    def test_table_with_three_columns(self):
        """3 열 표 변환."""
        input_text = """
| ID | Name | Status |
|----|------|--------|
| 1  | Alice| Active |
| 2  | Bob  | Inactive|
"""
        result = convert_gfm_table_to_bullets(input_text)
        self.assertIn("**ID**: 1", result)
        self.assertIn("**Name**: Alice", result)
        self.assertIn("**Status**: Active", result)

    def test_table_with_html_breaks(self):
        """HTML `<br>` 태그가 있는 셀 변환."""
        input_text = """
| 설명 | 값 |
|------|------|
| 줄 1<br>줄 2 | A |
"""
        result = convert_gfm_table_to_bullets(input_text)
        self.assertIn("**설명**:", result)
        self.assertIn("  - 줄 1", result)
        self.assertIn("  - 줄 2", result)
        self.assertIn("**값**: A", result)

    def test_code_fence_not_parsed_as_table(self):
        """코드 블록은 표로 오인하지 않음."""
        input_text = """
```
| not | a | table |
|-----|---|-------|
| 1   | 2 | 3     |
```
"""
        result = convert_gfm_table_to_bullets(input_text)
        # 표 변환이 없어야 함
        self.assertNotIn("**not**:", result)
        self.assertIn("| not | a | table |", result)

    def test_inline_pipe_not_parsed_as_table(self):
        """인라인 코드의 파이프는 표로 오인하지 않음."""
        input_text = """
A | B | C 조건
"""
        result = convert_gfm_table_to_bullets(input_text)
        # 표 변환이 없어야 함
        self.assertNotIn("**A**:", result)
        self.assertIn("A | B | C 조건", result)

    def test_empty_input(self):
        """빈 입력 처리."""
        self.assertEqual(convert_gfm_table_to_bullets(""), "")

    def test_no_table_preserves_text(self):
        """표가 없는 경우 원본 보존."""
        input_text = """
일반 텍스트
- 불릿 1
- 불릿 2
"""
        result = convert_gfm_table_to_bullets(input_text)
        self.assertEqual(result, input_text)

    def test_multiple_tables(self):
        """여러 표가 있는 경우 모두 변환."""
        input_text = """
| Table 1 |
|---------|
| A       |

| Table 2 |
|---------|
| B       |
"""
        result = convert_gfm_table_to_bullets(input_text)
        self.assertIn("**Table 1**: A", result)
        self.assertIn("**Table 2**: B", result)

    def test_format_linear_body_wrapper(self):
        """전처리 래퍼 함수 테스트."""
        input_text = """
| 열 | 값 |
|----|----|
| A  | 1  |
"""
        result = format_linear_body(input_text)
        self.assertIn("**열**: A", result)
        self.assertIn("**값**: 1", result)


if __name__ == "__main__":
    unittest.main()
