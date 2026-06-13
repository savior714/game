"""
Linear Issue UUID Cache — 메타데이터 캐시 유틸리티 (LIS-007 Phase 1).

`.linear_cache.json` 파일을 사용하여 Linear Issue ID(TEM-17)와 UUID 간의 매핑을 저장/조회.
API 호출 횟수를 줄이고, 재실행 시 중복 조회를 방지한다.
"""

import json
from pathlib import Path
from typing import Optional


CACHE_FILE = ".linear_cache.json"


class LinearCache:
    """Linear Issue ID ↔ UUID 매핑 캐시."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or Path(CACHE_FILE)
        self._data: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """캐시 파일을 로드한다. 파일이 없으면 빈 딕셔너리로 초기화."""
        if self.cache_path.exists():
            try:
                self._data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        """현재 캐시 상태를 파일에 저장한다."""
        self.cache_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_issue_uuid(self, human_id: str) -> Optional[str]:
        """Human-readable Issue ID (예: TEM-17)로 UUID를 조회한다."""
        return self._data.get(human_id)

    def set_issue_uuid(self, human_id: str, uuid: str) -> None:
        """Issue ID ↔ UUID 매핑을 캐시에 저장한다."""
        self._data[human_id] = uuid

    def get_all(self) -> dict[str, str]:
        """모든 캐시 데이터를 반환한다."""
        return dict(self._data)

    def clear(self) -> None:
        """캐시를 비운다."""
        self._data.clear()
