# 🎮 어린이 학습 게임 놀이터 (AidenGame)

AidenGame은 초등 저학년 어린이가 스스로 반복해서 사용하면서 실제 학습 숙련도를 높이고, 학습 완료 후 게임과 현실 보상을 얻는 개인용 학습 게임 플랫폼입니다.

**제품 방향 SSOT:** [`docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`](docs/specs/product/ACTIVE_PRODUCT_SCOPE.md)

## 🎯 현재 개발 초점

현재 최우선 개발 영역은 **Math를 첫 vertical slice로 하는 curriculum-aligned skill mastery + adaptive daily learning loop**입니다.

```text
skill goal
→ 문제 풀이
→ learning evidence
→ mastery 갱신
→ adaptive next question
→ goal 완료
→ gems + free-time
→ Ocean Rescue
```

- 국어·수학·영어·과학의 기존 핵심 quiz reliability stabilization은 완료된 baseline입니다.
- 첫 구현 대상은 Math이며, 검증된 skill/mastery 계약만 다른 과목으로 확장합니다.
- Ocean Rescue는 학습 문제를 내부에 넣는 교육게임이 아니라 **학습 완료 후 즐기는 active reward game**입니다.
- Space Explorer는 계속 `PAUSED_REFERENCE_ONLY`입니다.
- 새로운 대형 게임, RPG식 meta progression, backend/cloud 선행 개발, runtime LLM, 전체 framework/TypeScript 통일은 현재 기본 개발 목표가 아닙니다.

## 🚀 핵심 제품 surface

- **Core Quiz:** 국어, 수학, 영어, 과학 학습 surface
- **Adaptive learning:** 세부 skill mastery, spaced review, 약점 개선 + 성공 경험 균형
- **Reward loop:** 보석, streak, collection/unlock, 자유시간
- **Ocean Rescue:** 학습 목표 완료 후 이용하는 보상 게임
- **Guardian:** skill 성장/약점, 간단한 목표 preset, 현실 보상 상점
- **Persistence:** local-first, export/import backup 우선

## 📱 기준 사용 환경

- 1차 대상: 가족/개인 사용
- 초기 기준: 실제 사용하는 초등 저학년 아이의 현재 수준
- 기준 기기: Galaxy Tab S10급 Android 태블릿
- UX: landscape-first, portrait/split-screen/resize에서도 핵심 사용 가능
- 현재 runtime은 정적 웹 중심이며 필요에 따라 feature별 tooling을 다르게 사용할 수 있습니다.

## 🧭 현재 엔트리/라우팅

- 메인 허브: `index.html`
- 과목별 학습: `domains/{math,english,korean,science}/index.html`
- 보호자 관리: `domains/reward/guardian/index.html`
- Space Explorer: `experiments/space-explorer/index.html`
- Ocean Rescue source/package: `domains/ocean-rescue/`
- Ocean Rescue production artifact: `ocean-rescue/index.html`
- 배포 라우팅: `vercel.json`

| Surface | 상태 | 역할 |
|---|---|---|
| 메인 허브 | 운영중 | 학습·보상·게임 진입점 |
| Core Quiz 4과목 | 운영중 | adaptive learning의 학습 surface |
| Guardian / Reward | 운영중 | 성장·목표·보상 관리 |
| Ocean Rescue | 운영중·active feature | 학습 완료 후 reward game |
| Space Explorer | 운영중 artifact·개발 동결 | 실험 참고 |

과거 alias나 plan의 WP 번호를 현재 runtime entry 또는 다음 작업의 근거로 사용하지 않습니다.

## 🎮 Ocean Rescue toolchain

Ocean Rescue는 제품 차원에서 active feature지만, **현재 기본 구현 우선순위는 Math mastery/adaptive loop**입니다. Ocean Rescue 자체 작업이 명시적으로 선택되었을 때는 가장 가까운 feature/technical spec과 실제 최신 main을 기준으로 수행합니다.

대표 명령:

- `just sync-ocean-rescue-node`
- `just check-ocean-rescue-toolchain`
- `just typecheck-ocean-rescue`
- `just dev-ocean-rescue`
- `just build-ocean-rescue`
- `just check-ocean-rescue-drift`
- `just check-ocean-rescue-rollback`

제약:

- Node는 Ocean Rescue build-time/tooling boundary에 한정합니다.
- `ocean-rescue/index.html`은 production build pipeline이 생성하는 artifact입니다.
- generated artifact, provenance, registry identity를 손으로 우회 편집하지 않습니다.
- Vite/ESM/TypeScript migration 참고는 [`docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`](docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md)를 사용하되, 그 문서가 현재 제품 우선순위를 소유하지 않습니다.

## 🛠️ 로컬 개발 / 검증

통합 검증 (`verify.sh`):

```bash
bash ./verify.sh
```

주요 문서:

- 실행 규약: `AGENTS.md`
- 제품 방향 SSOT: `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`
- 아키텍처·품질 경계: `PROJECT_RULES.md`
- 문서 권위 색인: `docs/README.md`
- 완료된 Core Quiz reliability 계약: `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`
- 세션 handoff: `docs/agent-context/memory/MEMORY.md`

## 📁 주요 디렉토리

- `/`: 사용자 runtime HTML/CSS/JS entry
- `shared/`: 과목/제품 공용 domain·UI 로직
- `domains/`: Core Quiz, reward, Ocean Rescue 등 기능 도메인
- `experiments/`: 현재 Space Explorer 등 동결 실험 영역
- `ocean-rescue/`: Ocean Rescue production standalone artifact
- `docs/`: 제품 SSOT, feature spec, 기술 참고
- `tests/`: 제품·회귀 계약
