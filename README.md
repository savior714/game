# 🎮 어린이 학습 게임 놀이터 (AidenGame)

아이들의 성취감과 자기주도 학습을 최우선으로 하는 적응형 학습 게임 플랫폼입니다.  
현재 런타임은 루트 기반 정적 HTML/JS 구조로 운영됩니다.

## 🚀 핵심 기능

- **4대 과목**: 국어, 수학, 영어, 과학 학습 게임 제공
- **적응형 난이도**: 실력 변화에 따라 문제 난이도 자동 조정
- **보상 루프**: 연속 정답 기반 로켓/보석 보상과 보호자 상점 연동
- **공용 코어**: 과목별 엔진이 공통 로직(`common/`)을 재사용
- **우주 탐험 실험실**: `2D/3D` 렌더 모드, 태블릿 제스처(핀치/회전), 고해상도 렌더링 적용

## 🧭 현재 엔트리/라우팅 (SSOT)

- 메인 허브: `index.html`
- 우주 탐험: `space-explorer.html`
- 우주 탐험 모듈 엔트리: `space-explorer/main.js`
- 배포 라우팅 설정: `vercel.json`
  - `/space-explorer.html` -> `/space-explorer.html`

### 운영 / 실험 / 레거시 경로 구분표

| 구분 | 경로 | 상태 | 용도 |
| --- | --- | --- | --- |
| 메인 운영 엔트리 | `index.html` | 운영중 | 과목 선택 허브 및 공용 진입점 |
| 우주 탐험 실험 페이지 | `space-explorer.html` | 운영중(실험) | 2D/3D 우주 시뮬레이션 및 터치 제스처 실험 |
| 과목별 페이지 | `{math,english,korean,science}/index.html` | 운영중 | 학습 루프 본편 |
| 보호자/관리 페이지 | `guardian/index.html`, `admin/index.html` | 운영중(권한/설정 필요) | 보상 관리 및 운영 도구 |
| 과거 루트 엔트리 (`/index.html`) | 없음 | 레거시 폐기 | 템플릿 구조 전환 이후 비사용 |

## 🛠️ 로컬 개발

- 메인 런타임은 정적 템플릿 파일을 기준으로 동작합니다.
- 프로젝트 검증은 루트 `verify.sh`를 사용합니다.

```bash
bash ./verify.sh
```

## ✅ 검증 체계

- 테스트: `tests/`
- 통합 검증: `verify.sh`
- 문서/설계 기준:
  - `PROJECT_RULES.md`
  - `docs/SPACE_EXPLORER_PLAN.md`
  - `templates/docs/specs/technical/DESIGN.md`

## 📁 주요 디렉토리

- `/`: 사용자 런타임 HTML/CSS/JS 엔트리
- `common/`: 과목 공용 코어 로직
- `global/`: 인증/보상/동기화 전역 로직
- `{math,english,korean,science}/`: 과목별 게임 화면
- `space-explorer/`: 우주 탐험 렌더/상호작용 모듈
- `docs/`: 실행 계획, 스펙, 설계 SSOT
