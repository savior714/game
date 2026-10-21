"""보상 클라우드 동기화 — 계정 단위 DB 연동 검증

태블릿/노트북 기기 간에 동일한 계정(Google 로그인)으로 접속했을 때,
보상(보석·자유시간·간식·인벤토리)이 Supabase public.user_data(user_id 기준, RLS 적용)
를 통해 누락 없이 연동되는 계약을 소스 수준에서 검증한다.

검증 대상:
- domains/sync/sync-engine.js: study_rewards를 user_id 기준 풀/푸시 키로 다룬다.
- domains/reward/reward.js: 보상 저장 시 SyncEngine이 없더라도 동기화 큐(sync_queue)에
  기록해 클라우드 연동이 누락되지 않는다.
- index.html: 메인 허브에서 Supabase/인증/동기화 엔진을 정적 스크립트로 선적재한다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_ENGINE = ROOT / "domains" / "sync" / "sync-engine.js"
REWARD = ROOT / "domains" / "reward" / "reward.js"
INDEX_HTML = ROOT / "index.html"
USER_DATA_MIGRATION = ROOT / "supabase" / "migrations" / "001_create_user_data.sql"
USER_DATA_RLS = ROOT / "supabase" / "policies" / "user_data_rls.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_study_rewards_is_pulled_and_pushed_per_user_id():
    """SyncEngine이 study_rewards를 user_id(계정) 기준 Supabase 행으로 풀/푸시한다."""
    sync_code = _read(SYNC_ENGINE)
    assert "'study_rewards'" in sync_code, "study_rewards가 동기화 대상 키에 없다."
    assert "DEFAULT_PULL_KEYS" in sync_code, "DEFAULT_PULL_KEYS 정의가 없다."
    assert "user_id: user.id" in sync_code, "Supabase upsert에 user_id(계정) 바인딩이 없다."
    assert ".eq('user_id', user.id)" in sync_code, "Supabase 조회에 user_id 필터가 없다."
    assert "onConflict: 'user_id, data_key'" in sync_code, "계정·키 기준 upsert 갈등 처리가 없다."


def test_reward_save_enqueues_to_cloud_sync_queue_without_sync_engine():
    """RewardSystem.save()가 SyncEngine 미준비 시에도 보상 상태를 동기화 큐에 기록한다."""
    reward_code = _read(REWARD)
    assert "SYNC_QUEUE_KEY = 'sync_queue'" in reward_code, "동기화 큐 키 상수가 없다."
    assert "_enqueueSyncQueue(STORAGE_KEY, state)" in reward_code, (
        "SyncEngine 부재 시 sync_queue 기록 분기가 없다."
    )
    assert "window.SyncEngine.pushStats(STORAGE_KEY, state)" in reward_code, (
        "SyncEngine 준비 시 즉시 푸시 분기가 없다."
    )


def test_index_html_loads_supabase_auth_sync_statically():
    """메인 허브(index.html)가 인증·동기화 엔진을 정적 스크립트로 선적재한다."""
    html = _read(INDEX_HTML)
    assert "@supabase/supabase-js@2" in html, "supabase-js 스크립트 선적재가 없다."
    assert "./domains/auth/auth.js" in html, "인증 스크립트 선적재가 없다."
    assert "./domains/sync/sync-engine.js" in html, "동기화 엔진 스크립트 선적재가 없다."


def test_user_data_rls_is_per_user_id():
    """user_data 테이블 RLS가 auth.uid() = user_id로 계정 단위 격리된다."""
    ddl = _read(USER_DATA_MIGRATION)
    rls = _read(USER_DATA_RLS)
    assert "CONSTRAINT unique_user_data_key UNIQUE (user_id, data_key)" in ddl, (
        "user_data에 (user_id, data_key) 유일 제약이 없다."
    )
    assert "auth.uid() = user_id" in rls, "user_data RLS가 사용자 본인 데이터만 보도록 제한돼 있지 않다."
    assert "REVOKE ALL ON public.user_data FROM public" in ddl, (
        "public 접근 차단(revoke)이 없다."
    )
