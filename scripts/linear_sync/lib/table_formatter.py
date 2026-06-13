"""GFM 표 → 불릿 카드 변환기 (Linear 렌더링 호환성 향상).

Linear 에디터는 GFM 표를 렌더링할 때 가로 폭 제한 없이 무한히 늘어나는
현상이 발생함. 이를 방지하기 위해 표를 세로형 불릿 카드 형태로 변환:

  | 열 A | 열 B |
  |------|------|
  | 값 1 | 값 2 |

  =>

  - **열 A**: 값 1
  - **열 B**: 값 2

단일 셀에 여러 줄이 있는 경우:

  | 열 A |
  |------|
  | 줄 1<br>줄 2 |

  =>

  - **열 A**:
    - 줄 1
    - 줄 2
"""

import re


def convert_gfm_table_to_bullets(markdown_content: str) -> str:
    """GFM 표 블록을 세로 카드 단락으로 변환.

    Args:
        markdown_content: GFM 표가 포함된 마크다운 본문

    Returns:
        표가 불릿 카드 형태로 변환된 마크다운

    Example:
        >>> input = '''
        > 일부 설명
        >
        > | Task | Verify |
        > |------|--------|
        > | 구현 | 테스트 |
        > '''
        >>> result = convert_gfm_table_to_bullets(input)
        >>> "**Task**: 구현" in result
        True
    """
    if not markdown_content:
        return markdown_content

    lines = markdown_content.splitlines()
    result_lines: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 코드 블록 시작 감지 (백틱 3 개 이상)
        if stripped.startswith("```"):
            # 코드 블록 전체를 그대로 통과
            result_lines.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                result_lines.append(lines[i])
                i += 1
            if i < len(lines):
                result_lines.append(lines[i])
            i += 1
            continue

        # 표 시작 감지: `|` 로 시작하고 분리자가 아닌지 확인
        # Blockquote(`>`) 가 있더라도 stripped 가 `|` 로 시작하면 표로 간주
        clean_for_check = stripped.lstrip(">").strip()
        if clean_for_check.startswith("|") and not _is_separator_line(clean_for_check):
            # 표 시작 — 행을 수집
            table_rows = [clean_for_check]
            i += 1

            # 다음 행이 분리자 (`|---|`) 일 수 있음 — Blockquote 제거 후 확인
            if i < len(lines):
                next_stripped = lines[i].strip()
                next_clean = next_stripped.lstrip(">").strip()
                if _is_separator_line(next_clean):
                    i += 1  # 분리자 건너뜀

            # 표 데이터 행 수집 (아직 `|` 로 시작하면서 코드 블록이 아니면)
            while i < len(lines):
                current = lines[i].strip()
                clean_current = current.lstrip(">").strip()
                if clean_current.startswith("|") and not _is_separator_line(clean_current):
                    table_rows.append(clean_current)
                    i += 1
                elif current.startswith("```"):
                    # 표 안에 코드 블록이 있는 경우 (드문 경우)
                    # 표 끝으로 간주하고 현재 줄부터 다시 처리
                    break
                else:
                    break

            # 표 변환
            converted = _convert_table_rows_to_bullets(table_rows)
            result_lines.extend(converted)
            continue

        result_lines.append(line)
        i += 1

    # 원본의 trailing newline 보존
    if markdown_content.endswith("\n") and not markdown_content.endswith("\n\n"):
        result = "\n".join(result_lines) + "\n"
    elif markdown_content.endswith("\n\n"):
        result = "\n".join(result_lines) + "\n\n"
    else:
        result = "\n".join(result_lines)

    return result


def _is_separator_line(line: str) -> bool:
    """표 분리자 라인 (`|---|`, `|---|---|` 등) 인지 확인."""
    if not line.startswith("|"):
        return False
    # 분리자는 `|` 로 시작하고, `-` 와 `:` 만 포함하며 최소 1 개 열
    # 예: `|---|`, `|:---|`, `|---:|`, `|:---:|`
    parts = line.split("|")
    if len(parts) < 3:  # 최소 2 열 (양 끝의 빈 문자열 포함)
        return False
    # 중간 부분 (분리자) 이 `-` 와 `:` 만으로 구성되었는지 확인
    for part in parts[1:-1]:
        if not re.match(r"^:?-+:?$", part):
            return False
    return True


def _convert_table_rows_to_bullets(rows: list[str]) -> list[str]:
    """표 행 목록을 불릿 카드 리스트로 변환."""
    if len(rows) < 2:
        return rows

    # 헤더와 데이터 분리
    header_row = rows[0]
    data_rows = rows[1:]

    # 헤더 열 추출 (Blockquote 접두사 제거)
    headers = _parse_table_row(header_row)

    result_lines: list[str] = []

    # 각 데이터 행을 처리
    for data_row in data_rows:
        cells = _parse_table_row(data_row)

        # 각 열을 불릿으로 변환
        for idx, header in enumerate(headers):
            cell_value = cells[idx] if idx < len(cells) else ""
            # HTML 태그 제거 (브레이크 등)
            cell_value = re.sub(r"<br\s*/?>", "\n", cell_value)
            # 여러 줄인 경우 들여쓰기
            if "\n" in cell_value:
                result_lines.append(f"- **{header}**:")
                for line in cell_value.splitlines():
                    result_lines.append(f"  - {line.strip()}")
            else:
                result_lines.append(f"- **{header}**: {cell_value}")

    return result_lines


def _parse_table_row(row: str) -> list[str]:
    """표 행을 열 목록으로 파싱 (중첩 파이프 고려).

    Blockquote 접두사 (`>`) 를 제거한 후 파싱.
    """
    # Blockquote 접두사 제거
    cleaned = row.lstrip(">").strip()
    # 단순 파싱: `|` 로 분리하고 양 끝 빈 문자열 제거
    parts = cleaned.split("|")
    # 양 끝의 빈 문자열 제거 (예: `| A | B |` → `['', ' A ', ' B ', '']`)
    content_parts = parts[1:-1]
    return [cell.strip() for cell in content_parts]


def format_linear_body(markdown_content: str) -> str:
    """Linear 전송용 본문 전처리 (표 변환 + 일반 텍스트 보존).

    Args:
        markdown_content: 마크다운 본문

    Returns:
        전처리된 본문
    """
    return convert_gfm_table_to_bullets(markdown_content)
