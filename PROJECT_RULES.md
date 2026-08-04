# PROJECT_RULES.md — AidenGame 프로젝트 정책

작업 절차는 `AGENTS.md`를 따른다. 이 문서는 제품·아키텍처·품질 경계만 정의한다.

## 1. 제품 목적

AidenGame은 어린이를 위한 정적 웹 기반 학습 게임 플랫폼이다. 단순한 학습 흐름, 즉각적인 피드백, 성취감, 보호자 통제를 우선한다.

## 2. 런타임과 경로

| 역할 | 경로 |
|---|---|
| 메인 허브 | `index.html` |
| 공용 스타일 | `styles.css` |
| 과목별 게임 | `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/` |
| 지원 도메인 | `domains/reward/`, `domains/auth/`, `domains/sync/` |
| 공용 로직 | `shared/domain/`, `shared/ui/`, `shared/event-bus.js` |
| 실험 | `experiments/` |
| 보호자·관리 | `guardian/`, `admin/` |
| 테스트 | `tests/` |
| 검증 | `verify.sh`, `scripts/`, `tools/` |

- 신규 UI와 로직은 가장 가까운 기능 디렉터리에 둔다.
- 여러 과목이 공유하는 로직만 `shared/`로 올린다.
- 실험은 안정화 전까지 `experiments/`에 격리한다.
- 빈 `src/`를 새 runtime SSOT로 사용하지 않는다.
- Next.js, Tauri, 별도 백엔드 API는 현재 범위에 추가하지 않는다.
- generated artifact와 authoring source를 구분한다.
- Ocean Rescue는 가장 가까운 technical spec을 따른다.

## 3. 기술 스택

- 사용자 런타임: HTML, CSS, JavaScript
- 배포: `vercel.json` 기반 정적 호스팅
- 검증 도구: Python, `uv`, `just`, Ruff, type checker, Pytest
- Ocean Rescue build tooling은 해당 경로의 lockfile과 spec이 authority다.
- dependency·toolchain upgrade는 독립 failure domain으로 수행한다.

## 4. 개발·배포

- canonical branch는 `origin/main`이다.
- `main` 직접 수정과 fast-forward push가 기본이다.
- PR·feature branch는 요청 시에만 사용한다.
- 병렬 충돌 방지는 `agents/workflows/work-package-claim.md`의 최소 path/resource lock만 사용한다.
- generated artifact는 canonical source와 build pipeline을 통해 갱신한다.
- 원격 상태나 필수 검증이 불명확하면 publish하지 않는다.

## 5. 품질

- 한 작업은 하나의 failure domain 또는 하나의 검증 가능한 가설로 제한한다.
- 수정 전 재현 조건과 단일 criterion을 정한다.
- 수정 후 그 criterion만 focused verification으로 판정한다.
- unrelated cleanup은 포함하지 않는다.
- 새 검증은 잡아낼 구체적 failure mode가 있을 때만 추가한다.
- full-suite는 실제 회귀 위험이나 cutover가 요구할 때만 실행한다.

대표 명령:

```bash
just verify
just lint
just typecheck
just test
just ci
```

## 6. 사용자 경험

- 어린이가 이해할 수 있는 짧고 명확한 문구를 사용한다.
- 실패보다 재시도와 성취 피드백을 강조한다.
- 터치 환경과 작은 화면을 기본으로 고려한다.
- 핵심 흐름은 키보드와 보조 기술로도 사용할 수 있어야 한다.
- 시각 효과가 조작과 가독성을 방해하지 않게 한다.

## 7. 보안

- API 키, 토큰, 쿠키, `.env` 원문을 노출하지 않는다.
- 인증·동기화·보호자 기능은 권한이 불명확할 때 fail-closed한다.
- 외부 입력을 검증하고 안전한 DOM API를 사용한다.

## 8. 문서

| 목적 | SSOT |
|---|---|
| 실행 규약 | `AGENTS.md` |
| 프로젝트 정책 | `PROJECT_RULES.md` |
| 병렬 잠금 | `agents/workflows/work-package-claim.md` + Issue #1 |
| Git·publish | `agents/workflows/git.md` |
| 요구사항·회귀 | `tests/` |
| 배포 | `vercel.json`과 실제 entry |
| 기능 설계 | 대상 기능에 가장 가까운 `docs/` 문서 |

과거 Plan·Blueprint 상태 관리가 제품 변경보다 우선하지 않는다.
