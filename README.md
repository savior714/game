# 🎮 어린이 학습 게임 놀이터 (Learning Playground)

아이들의 성취감을 최우선으로 하는 지능형 적응형 학습 플랫폼입니다. 정적 HTML/JS로 구성되며, 로컬 개발 시 `serve_game.py`로 동일 출처에서 서빙합니다.

## 🚀 주요 기능

- **4대 과목**: 국어·수학·영어·과학 놀이(메인 허브 `index.html`에서 진입).
- **7단계 정밀 난이도**: 입문부터 전설까지 실력에 맞춰 조정.
- **단계별 마스터**: 현재 단계를 충분히 익혀야 다음 단계로 진행(과목별 세부 비율은 스펙 참고).
- **컨디션 케어 (Confidence Recovery)**: 연속 오답 시 난이도를 한 단계 내려 자신감 회복을 돕습니다.
- **중복 방지 (Anti-Repetition)**: 최근 출제 버퍼로 같은 유형이 연속으로 나오지 않도록 제한합니다.
- **그물망 보호 (Net Shield)**: 연속 정답으로 그물망을 쌓고, 실수 시 한 번 튕겨 복귀하는 보호 로직이 전 과목에 맞춰져 있습니다.
- **로켓 & 보석 경제**: 20연속 정답 시 로켓 발사 연출과 함께 💎 보석이 지급되며, 보석으로 유튜브·간식·마블 등 보상을 상점에서 선택합니다(기존 룰렛 방식은 보석/상점 모델로 대체됨).
- **보호자 맞춤 상점**: 구글 로그인 연동 환경에서 보호자가 보상 아이콘·문구·가격(보석)을 등록·삭제할 수 있습니다(`guardian/index.html`).
- **계정·동기화**: Supabase 기반 구글 로그인(`global/auth.js`)과 오프라인 큐·타임스탬프 병합(`global/sync-engine.js`)으로 기기 간 진행·보상 상태를 맞출 수 있습니다.
- **관리자(선택)**: 허용된 구글 계정만 `admin/index.html`에서 사용자 디렉터리 등을 조회할 수 있도록 구성되어 있습니다(`supabase/user_directory.sql`, RLS).

## 🛠️ 실행 방법

1. Python이 있는 환경에서 프로젝트 루트에서 서버를 띄웁니다.

   ```bash
   python serve_game.py
   ```

2. 브라우저에서 `http://localhost:3000` — 메인 허브(과목 선택).

3. 바로 특정 화면을 열려면 인자를 넘깁니다(예: `python serve_game.py math`, `english`, `korean`, `marble`, `admin`). 브라우저만 끄고 서버만 유지하려면 `--no-browser`를 붙입니다.

4. 과학·보호자 화면 등은 허브 링크 또는 URL로 엽니다(예: `http://localhost:3000/science/index.html`, `http://localhost:3000/guardian/index.html`).

> Supabase URL/키·OAuth 설정은 배포·로컬 테스트 시 환경에 맞게 구성해야 합니다. 자세한 스키마는 `supabase/` 및 문서를 참고하세요.

## 📁 문서 체계 (SDD)

- `docs/memory.md`: 프로젝트 현재 상태 요약 (SSOT)
- `docs/CRITICAL_LOGIC.md`: 핵심 설계·비즈니스 로직
- `docs/specs/`, `specs/`: 과목·플랫폼 세부 스펙

## 🧩 디렉터리 개요

- `common/`: 전 과목 공용 — `rocket-core.js`, `rocket-effects.js`, `progress-engine.js`, `quiz-ui-core.js`
- `global/`: 전역 보상·인증·동기화 — `reward.js`, `reward_ui.js`, `reward.css`, `auth.js`, `sync-engine.js`
- 과목별 `engine.js` / `ui.js` 등은 공용 코어를 재구현하지 않고 위임 호출하는 방식을 유지합니다.

전 과목 데이터·코어 계약 검증은 `verify_all.js`(및 관련 스크립트)로 자동 점검할 수 있습니다.
