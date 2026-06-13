---
scope:
- '*'
always_apply: false
priority: 1
domain: core
verify_with:
- just prevent-tech-debt
- just env-lint
---
<!-- Language: ko -->
# Secrets & Credentials (ZERO-LEAK, 재발 금지)

> **도메인 지침 이전**: HIRA API·PHI 보안 → `[medical/emr_security.md](../domains/medical/emr_security.md)`. CSV 시딩·인코딩 → `[infra/seeding.md](../domains/infra/seeding.md)` (경로 매칭 시 `just route`로 동적 로드).

**정책 상위 SSOT**: `[PROJECT_RULES.md](../../PROJECT_RULES.md) §4.1`. 본 절은 실행 방법만 고정한다.

- **절대 금지**: `.env`, `.env.*`, 앱/CI 시크릿 파일, 키·PEM 등에서 **비밀 문자열을 읽어 채팅·PR·도구 결과에 붙여 넣는 행위**. `grep API_KEY`, `grep LINEAR`, `cat .env` 등 **stdout/stderr에 비밀이 실릴 수 있는 명령**으로 키 존재를 “확인”하는 것도 금지다. (확인이 필요하면 “파일이 있는지”만 `test -f` 등으로, 내용은 열지 않는다.)
- **선행 동의**: 외부 API·GraphQL·git remote 등에 **비밀이 필요하면 먼저 사용자에게** 자격 증명을 어떻게 둘지 묻는다. 기본 경로는 **`just` 스크립트**(내부적으로 비밀 주입)를 쓰고, 로컬 `.env`를 에이전트가 직접 열어 인용하는 것은 사용자가 명시적으로 허용한 경우에만 허용한다.
- **직접 쉘 실행 금지 및 just 위임 강제**: 에이전트가 쉘에서 직접 `.env`를 소싱(`source`)하는 것은 원천 금지된다. 비밀값이 필요한 작업은 무조건 사전에 정의된 `just` 명령어(내부적으로 비밀을 안전하게 주입하는)만을 통해서 실행해야 한다.
- **Linear (저장소 정책)**: Linear 이슈 조회·상태·댓글 동기화는 루트 **`.env`의 `LINEAR_API_KEY`**와 **`scripts/linear_sync/sync_engine.py`** GraphQL 경로를 표준으로 한다. 에이전트는 키를 채팅에 노출하지 않고, `just linear-sync`·`just linear-pull` 출력만 참조한다. **빈 셸 `printenv`만으로 "키 없음" 결론을 내리지 말 것** — 상세는 [linear.md](../workflows/linear.md)「실행 절차 → API 키·`.env` SSOT」.
- **`.env` / `.env.example` 편집 게이트 (재발 방지)**: **`KEY=VALUE`와 `#` 주석만** — `unset`·`export`·`source`·`$(…)`·리다이렉트 등 **셸 명령 금지** (Docker Compose·`run_dev.sh` 파싱 실패). 저장 후 **`just env-lint` PASS** (`scripts/verify/lint_dotenv.py`; `just lint`에 포함). 로컬 `.env`는 Git에 없으므로 에이전트가 손대면 반드시 린트를 돌린다.

### `.env` 소비자별 strictness (동일 파일, 다른 실패 조건)

| 소비자 | 한 줄 오류 시 |
|--------|----------------|
| Docker Compose | **전체 ABORT** |
| Python `load_env()` line-filter | 해당 줄 skip, 나머지 통과 가능 |
| bash `export` in `run_dev.sh` | invalid identifier 즉시 실패 |

→ 셸 명령을 `.env`에 넣으면 **가장 strict한 소비자** 기준으로 dev 전체가 깨진다. 편집 후 `just env-lint` 필수.

- **실패·에러 시**: 스택 트레이스·환경 덤프에 키가 섞여 있을 수 있으므로 **응답에 원문을 붙이지 않는다.**
- **노출 발생 시**: 키 문자열을 다시 보여주지 말고 **즉시 폐기·재발급(회전)**을 안내한다.
