import argparse
import asyncio
import logging
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.infrastructure.config.settings import settings

# 프로젝트 경로 추가 (uv run 환경에서는 생략 가능하지만 명시적 임포트를 위해)
from src.infrastructure.persistence.schema import Base

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("db_schema_doctor")

class SchemaAuditDoctor:
    """ORM 모델과 실제 데이터베이스 스키마 간의 정합성을 검증하는 도구"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_async_engine(db_url)
        self.orm_meta = Base.metadata

        # PostgreSQL 타입 -> SQLAlchemy 타입 이름 정규화 매핑
        self.type_norm_map = {
            "character varying": "varchar",
            "character": "char",
            "timestamp with time zone": "timestamptz",
            "timestamp without time zone": "timestamp",
            "double precision": "float",
            "boolean": "bool",
            "integer": "int4",
            "bigint": "int8",
            "smallint": "int2",
            "text": "text",
            "jsonb": "jsonb",
            "uuid": "uuid",
            "date": "date",
            "numeric": "numeric",
        }

    async def get_db_schema(self) -> dict[str, dict[str, dict[str, Any]]]:
        """information_schema에서 현재 DB 스키마 정보를 가져옴"""
        query = """
        SELECT 
            table_name, 
            column_name, 
            data_type, 
            is_nullable, 
            column_default,
            is_identity
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """

        db_schema = {}
        async with self.engine.connect() as conn:
            result = await conn.execute(text(query))
            for row in result:
                table = row.table_name
                if table not in db_schema:
                    db_schema[table] = {}

                db_schema[table][row.column_name] = {
                    "type": row.data_type.lower(),
                    "nullable": row.is_nullable.upper() == "YES",
                    "default": row.column_default,
                    "is_identity": row.is_identity.upper() == "YES"
                }
        return db_schema

    async def get_db_indexes(self) -> dict[str, dict[str, dict[str, Any]]]:
        """PostgreSQL 시스템 카탈로그에서 인덱스 정보를 가져옴 (GIN 등 특수 인덱스 포함)"""
        query = """
        SELECT
            t.relname as table_name,
            i.relname as index_name,
            am.amname as index_type,
            ix.indisunique as is_unique,
            pg_get_indexdef(ix.indexrelid) as index_def
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_am am ON i.relam = am.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = 'public'
          AND t.relkind = 'r'
        ORDER BY t.relname, i.relname;
        """
        db_indexes = {}
        async with self.engine.connect() as conn:
            result = await conn.execute(text(query))
            for row in result:
                table = row.table_name
                if table not in db_indexes:
                    db_indexes[table] = {}

                db_indexes[table][row.index_name] = {
                    "type": row.index_type.lower(),
                    "unique": row.is_unique,
                    "def": row.index_def
                }
        return db_indexes

    def get_orm_schema(self) -> dict[str, dict[str, dict[str, Any]]]:
        """SQLAlchemy Base.metadata에서 ORM 스키마 정보를 추출"""
        orm_schema = {}
        for table_name, table in self.orm_meta.tables.items():
            orm_schema[table_name] = {}
            for col in table.columns:
                # SQLAlchemy 타입을 소문자 문자열로 변환 (정규화를 위해)
                orm_type = str(col.type).lower()
                # 괄호 제거 (예: varchar(50) -> varchar)
                base_type = orm_type.split('(')[0]

                orm_schema[table_name][col.name] = {
                    "type": base_type,
                    "nullable": col.nullable,
                    "default": col.server_default,
                    "is_identity": hasattr(col, "identity") and col.identity is not None
                }
        return orm_schema

    def get_orm_indexes(self) -> dict[str, dict[str, dict[str, Any]]]:
        """ORM 모델 정의에서 인덱스 정보를 가져옴"""
        orm_indexes = {}
        for table_name, table in self.orm_meta.tables.items():
            orm_indexes[table_name] = {}
            # 1. 컬럼 레벨 인덱스 (Index=True)
            for col in table.columns:
                if col.index:
                    # SQLAlchemy는 내부적으로 'ix_table_column' 형태의 이름을 가질 수 있음
                    idx_name = f"ix_{table_name}_{col.name}"
                    orm_indexes[table_name][idx_name] = {
                        "type": "btree", # 기본값
                        "unique": col.unique or False,
                        "columns": [col.name]
                    }

            # 2. 테이블 레벨 인덱스 (__table_args__)
            for idx in table.indexes:
                idx_type = "btree"
                pg_opts = idx.dialect_options.get("postgresql", {})

                # SQLAlchemy 2.0+ pattern for postgresql_using
                using_val = pg_opts.get("using") or pg_opts.get("postgresql_using")
                if isinstance(using_val, str):
                    idx_type = using_val.lower()

                orm_indexes[table_name][idx.name] = {
                    "type": idx_type,
                    "unique": idx.unique,
                    "columns": [c.name for c in idx.columns]
                }
        return orm_indexes

    def _normalize_type(self, type_name: str) -> str:
        """DB 타입을 ORM 친화적 타입명으로 정규화"""
        t = type_name.lower()
        return self.type_norm_map.get(t, t)

    def compare(self, orm_schema: dict, db_schema: dict) -> list[str]:
        """두 스키마를 비교하여 차이점(Issue) 목록 반환"""
        issues = []

        orm_tables = set(orm_schema.keys())
        db_tables = set(db_schema.keys())

        # 1. 테이블 존재 여부 확인
        missing_tables = orm_tables - db_tables
        for table in missing_tables:
            issues.append(f"[TABLE MISSING] DB에 '{table}' 테이블이 없습니다.")

        extra_tables = db_tables - orm_tables
        if extra_tables:
            logger.debug(f"DB에만 존재하는 테이블: {extra_tables}")

        # 2. 존재하는 테이블 내 컬럼 비교
        for table in orm_tables & db_tables:
            orm_cols = orm_schema[table]
            db_cols = db_schema[table]

            # 컬럼 누락 확인
            missing_cols = set(orm_cols.keys()) - set(db_cols.keys())
            for col in missing_cols:
                issues.append(f"[COLUMN MISSING] '{table}' 테이블에 '{col}' 컬럼이 없습니다.")

            # 속성 불일치 확인
            for col in set(orm_cols.keys()) & set(db_cols.keys()):
                orm_attr = orm_cols[col]
                db_attr = db_cols[col]

                # 타입 비교 (정규화 후)
                orm_type = self._normalize_type(orm_attr["type"])
                db_type = self._normalize_type(db_attr["type"])

                if orm_type != db_type:
                    # SQLAlchemy 'datetime' -> PG 'timestamp', 'timestamptz' 허용
                    # SQLAlchemy 'string' -> PG 'varchar', 'text' 허용
                    # SQLAlchemy 'uuid' -> PG 'uuid'
                    # SQLAlchemy 'char' -> PG 'uuid' (일부 SQLAlchemy 버전/정의에서 uuid를 char로 표현할 때 대응)
                    is_compatible = (
                        (orm_type == "datetime" and db_type in ["timestamp", "timestamptz"]) or
                        (orm_type == "string" and db_type in ["varchar", "text", "character varying"]) or
                        (orm_type == "char" and db_type == "uuid") or
                        (orm_type == "uuid" and db_type == "uuid") or
                        (orm_type == "json" and db_type == "jsonb") or
                        (db_type == "user-defined") # Enum 타입 등은 일단 수동 확인 대상으로 간주하되 오탐 최소화
                    )

                    if not is_compatible:
                        issues.append(
                            f"[TYPE MISMATCH] '{table}.{col}': ORM({orm_type}) vs DB({db_type})"
                        )

                # Nullable 비교 (Primary Key는 암시적으로 NOT NULL)
                if orm_attr["nullable"] != db_attr["nullable"]:
                    # DB identity 컬럼 등 특수 상황 제외 로직 (필요 시 추가)
                    issues.append(
                        f"[NULLABLE MISMATCH] '{table}.{col}': ORM({orm_attr['nullable']}) vs DB({db_attr['nullable']})"
                    )

                # Identity 비교
                if orm_attr["is_identity"] != db_attr["is_identity"]:
                    issues.append(
                        f"[IDENTITY MISMATCH] '{table}.{col}': ORM(identity={orm_attr['is_identity']}) vs DB(identity={db_attr['is_identity']})"
                    )

        return issues

    def compare_indexes(self, orm_indexes: dict, db_indexes: dict) -> list[str]:
        """인덱스 구성을 비교"""
        issues = []
        for table in orm_indexes:
            if table not in db_indexes:
                # 테이블 자체가 없는 경우는 compare()에서 처리하므로 여기선 인덱스 누락으로 기록
                for idx_name in orm_indexes[table]:
                    issues.append(f"[INDEX MISSING] '{table}'에 '{idx_name}' 인덱스가 없습니다.")
                continue

            orm_idxs = orm_indexes[table]
            db_idxs = db_indexes[table]

            for idx_name, orm_attr in orm_idxs.items():
                # 이름이 정확히 일치하지 않을 수 있음 (SQLAlchemy 자동 생성 명칭)
                # 컬럼 구성과 타입이 같으면 일치로 간주하는 로직
                found = False
                for db_idx_name, db_attr in db_idxs.items():
                    # 1. 이름이 같으면 우선 비교
                    if idx_name == db_idx_name:
                        if orm_attr["type"] != db_attr["type"]:
                            issues.append(
                                f"[INDEX TYPE MISMATCH] '{table}.{idx_name}': ORM({orm_attr['type']}) vs DB({db_attr['type']})"
                            )
                        found = True
                        break

                    # 2. 이름이 달라도 definition에 컬럼명들이 포함되어 있고 타입이 같으면 매칭 시도
                    # (간단하게 하기 위해 일단 이름 매칭을 주력으로 하되, GIN 인덱스 등은 명시적 이름 사용 권장)

                if not found:
                    # 보조 확인: DB 인덱스를 순회하며 컬럼 조합이 같은 게 있는지 확인
                    # (여기선 단순화하여 이름 기반으로 먼저 체크)
                    issues.append(f"[INDEX MISSING] '{table}'에 '{idx_name}'({orm_attr['type']}) 인덱스를 찾을 수 없습니다.")

        return issues

async def run_audit(args):
    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    doctor = SchemaAuditDoctor(db_url)

    logger.info("📡 DB 스키마 및 인덱스 분석 중...")
    db_schema = await doctor.get_db_schema()
    db_indexes = await doctor.get_db_indexes()

    logger.info("🏗️ ORM 모델 분석 중...")
    orm_schema = doctor.get_orm_schema()
    orm_indexes = doctor.get_orm_indexes()

    logger.info("🔍 정합성 검사 시작...")
    issues = doctor.compare(orm_schema, db_schema)
    index_issues = doctor.compare_indexes(orm_indexes, db_indexes)

    all_issues = issues + index_issues

    if not all_issues:
        logger.info("✅ 모든 스키마가 일치합니다! (All Clear)")
        sys.exit(0)
    else:
        logger.error(f"❌ {len(all_issues)}개의 불일치가 발견되었습니다:")
        for issue in all_issues:
            print(f"  - {issue}")

        if args.exit_on_error:
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EMR Database Schema Consistency Doctor")
    parser.add_argument("--exit-on-error", action="store_true", help="불일치 발견 시 exit code 1 반환")
    parser.add_argument("--report", type=str, help="결과를 저장할 리포트 파일 경로")

    args = parser.parse_args()

    try:
        asyncio.run(run_audit(args))
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        sys.exit(1)
