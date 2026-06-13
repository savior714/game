"""KCD 검색 SQL에 대한 EXPLAIN ANALYZE (Task 4.1 / TEM-23).

`kcd_master`에 트랜잭션 범위의 벤치 행(`code` LIKE ``__bench__%``)을 적재한 뒤
리포지토리와 동등한 ``ILIKE`` 검색·코드 정확 일치 조회를 실행하고,
마지막에 **ROLLBACK**하여 벤치 데이터를 남기지 않습니다.

Usage (저장소 루트, ``DATABASE_URL`` 설정됨)::

    uv run python scripts/verify/kcd_search_explain.py
    uv run python scripts/verify/kcd_search_explain.py --rows 50000 --query 당뇨
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 저장소 루트 (``src`` 임포트)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

from src.infrastructure.config.settings import settings  # noqa: E402

_BENCH_PREFIX = "__bench__"


def _sync_conninfo(database_url: str) -> str:
    u = (database_url or "").strip()
    if u.startswith("postgresql+asyncpg://"):
        return "postgresql://" + u.removeprefix("postgresql+asyncpg://")
    if u.startswith("postgresql://"):
        return u
    msg = "DATABASE_URL must be postgresql+asyncpg:// or postgresql://"
    raise ValueError(msg)


def _search_sql_fragment(pattern: str) -> sql.Composed:
    p = pattern
    return sql.SQL(
        "(code ILIKE {pat} OR name_ko ILIKE {pat} OR name_en ILIKE {pat})"
    ).format(pat=sql.Literal(f"%{p}%"))


def main() -> int:
    parser = argparse.ArgumentParser(description="KCD search EXPLAIN ANALYZE (rollback bench rows).")
    parser.add_argument("--rows", type=int, default=20_000, help="Number of bench rows (default 20000).")
    parser.add_argument("--query", type=str, default="E11", help="Substring for ILIKE search (default E11).")
    args = parser.parse_args()

    raw_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    try:
        conninfo = _sync_conninfo(raw_url)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    n = max(0, args.rows)
    q = args.query

    try:
        with psycopg.connect(conninfo, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DELETE FROM kcd_master WHERE code LIKE {}").format(
                        sql.Literal(f"{_BENCH_PREFIX}%")
                    )
                )

                if n > 0:
                    cur.execute(
                        """
                        INSERT INTO kcd_master (code, name_ko, name_en, is_standard)
                        SELECT
                            %s || lpad(gs::text, 8, '0'),
                            '벤치마크 상병 ' || lpad(gs::text, 8, '0'),
                            'Bench disease ' || lpad(gs::text, 8, '0'),
                            TRUE
                        FROM generate_series(1, %s) AS gs
                        """,
                        (_BENCH_PREFIX, n),
                    )

                cur.execute("SELECT count(*)::bigint FROM kcd_master")
                (total_after_seed,) = cur.fetchone()  # type: ignore[misc]

                frag = _search_sql_fragment(q)
                explain_like = sql.SQL(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                    "SELECT id, code, name_ko, name_en FROM kcd_master WHERE {cond} LIMIT 20"
                ).format(cond=frag)
                print("=== EXPLAIN: repository-equivalent ILIKE OR (limit 20) ===")
                cur.execute(explain_like)
                for (line,) in cur.fetchall():
                    print(line)

                sample_code = f"{_BENCH_PREFIX}00000001"
                explain_eq = (
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                    "SELECT id, code, name_ko, name_en FROM kcd_master WHERE code = %s"
                )
                print()
                print(f"=== EXPLAIN: exact code match ({sample_code}) ===")
                cur.execute(explain_eq, (sample_code,))
                for (line,) in cur.fetchall():
                    print(line)

                print()
                print(f"[summary] kcd_master row count during run: {total_after_seed}")
                print("[summary] Bench rows rolled back; production data unchanged.")

            conn.rollback()
    except psycopg.OperationalError as e:
        print(f"PostgreSQL 연결 실패: {e}", file=sys.stderr)
        print("DATABASE_URL 대상 서버가 떠 있는지 확인하세요.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
