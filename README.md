# 🎮 어린이 학습 게임 놀이터 (AidenGame)

아이들의 성취감과 자기주도 학습을 최우선으로 하는 적응형 학습 게임 플랫폼입니다.  
현재 런타임은 루트 기반 정적 HTML/CSS/JavaScript 구조로 운영됩니다.

## 🚀 핵심 기능

- **4대 과목**: 국어, 수학, 영어, 과학 학습 게임 제공
- **적응형 난이도**: 실력 변화에 따라 문제 난이도 자동 조정
- **보상 루프**: 연속 정답 기반 로켓/보석 보상과 보호자 상점 연동
- **공용 코어**: 과목별 엔진이 공통 로직(`shared/`)을 재사용
- **우주 탐험 실험실**: `2D/3D` 렌더 모드, 태블릿 제스처(핀치/회전), 고해상도 렌더링 적용

## 🧭 현재 엔트리/라우팅 (SSOT)

- 메인 허브: `index.html`
- 보호자 관리: `domains/reward/guardian/index.html`
- 우주 탐험 페이지: `experiments/space-explorer/index.html`
- 우주 탐험 모듈 엔트리: `experiments/space-explorer/main.js`
- 배포 라우팅 설정: `vercel.json`
  - 별도 rewrite 없이 정적 파일 경로를 그대로 제공
  - 루트 허브 링크: `/experiments/space-explorer/index.html`

### 운영 / 실험 / 레거시 경로 구분표

| 구분 | 경로 | 상태 | 용도 |
| --- | --- | --- | --- |
| 메인 운영 엔트리 | `index.html` | 운영중 | 과목 선택 허브 및 공용 진입점 |
| 과목별 페이지 | `domains/{math,english,korean,science}/index.html` | 운영중 | 학습 루프 본편 |
| 보호자 관리 페이지 | `domains/reward/guardian/index.html` | 운영중 | 난이도, 주간 영단어, 보상 상점 및 성장 요약 관리 |
| 우주 탐험 실험 페이지 | `experiments/space-explorer/index.html` | 운영중(실험) | 2D/3D 우주 시뮬레이션 및 터치 제스처 실험 |
| 과거 보호자/관리 alias | `guardian/index.html`, `admin/index.html` | 없음 | rewrite가 없으므로 사용하지 않음 |
| 과거 우주 탐험 alias | `/space-explorer.html` | 없음 | `vercel.json` rewrite가 없으므로 사용하지 않음 |

## 🛠️ 로컬 개발

- 메인 런타임은 정적 템플릿 파일을 기준으로 동작합니다.
- 프로젝트 검증은 루트 `verify.sh`를 사용합니다.

```bash
bash ./verify.sh
```

## 🎮 Ocean Rescue 개발 toolchain

Ocean Rescue에는 도메인 로컬 build-time Node 경계가 존재합니다.

- **Package boundary:** `domains/ocean-rescue`
- **Node pin:** `domains/ocean-rescue/.node-version`
- **Project pnpm:** `packageManager` + `corepack pnpm` (예: `corepack pnpm install`)
- **Sync:** `just sync-ocean-rescue-node`
- **Toolchain check:** `just check-ocean-rescue-toolchain`
- **Typecheck:** `just typecheck-ocean-rescue`
- **Development server:** `just dev-ocean-rescue` (개발 전용, `http://127.0.0.1:5173/index.dev.html`)
- **Dev-server check:** `just check-ocean-rescue-dev-server`
- **Shadow bundle build:** `just build-ocean-rescue-shadow-bundle` (결정적 IIFE 번들, `dist/ocean-rescue-app.shadow.js`)
- **Shadow bundle check:** `just check-ocean-rescue-shadow-bundle`
- **Typed profile check:** `just check-ocean-rescue-typed-profile` (WP-31A 프로파일 모델 수직 슬라이스 검증 번들)

제약:

- Node는 **build-time 전용**입니다. 전체 browser runtime은 Node를 요구하지 않습니다.
- Canonical production build: `just build-ocean-rescue` (Vite IIFE bundle + vendored Pixi, `ocean-rescue/index.html` 생성). `just build-ocean-rescue-render-package`도 동일 pipeline입니다.
- Operational rollback: `just rollback-ocean-rescue-to-legacy` (배포 캐노니컬 아티팩트 `ocean-rescue/index.html`을 legacy ordered-script 형태로 복원).
- Proof-only legacy artifact: `just build-ocean-rescue-legacy-proof` (`dist/legacy-rollback.html` 생성, 캐노니컬 아티팩트 미변경).
- Vite dev server는 **개발 전용**입니다. 실행 중에는 현재 global-namespace 소스를 `index.dev.html` + `vite.config.ts`를 통해 그대로 제공합니다 (WP-11). Production pipeline은 변경되지 않습니다.
- Shadow bundle은 **검증 전용**입니다. 18개 비-vendor 스크립트를 하나의 결정적 IIFE 번들로 결합하며(WP-20), vendored Pixi는 별도 prerequisite script로 유지됩니다. Production 소유권은 WP-21부터 Vite bundle pipeline에 있습니다.
- 프로파일 모델은 WP-31A부터 canonical ESM 그래프에서 `src/esm/profile.js` → `src/profile/profile.ts`(strict TypeScript)를 사용합니다. `src/profile.js`는 변경 없이 legacy rollback 전용으로 유지됩니다.

## ✅ 검증 체계

- 테스트: `tests/`
- 통합 검증: `verify.sh`
- 문서/설계 기준:
  - `PROJECT_RULES.md`
  - `docs/SPACE_EXPLORER_PLAN.md`
  - `templates/docs/specs/technical/DESIGN.md`
- 세션 연속성(핸드오프): `docs/agent-context/memory/MEMORY.md`

## 📁 주요 디렉토리

- `/`: 사용자 런타임 HTML/CSS/JS 엔트리
- `shared/`: 과목 공용 코어 로직 (`domain/`, `ui/`)
- `domains/`: 과목별 게임 (`math/`, `english/`, `korean/`, `science/`) + 지원 도메인 (`reward/`, `auth/`, `sync/`)
- `experiments/`: 실험 모듈 (`space-explorer/`, `marble/`)
- `docs/`: 실행 계획, 스펙, 설계 SSOT
