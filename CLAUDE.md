# 어린이 학습 게임 플랫폼 — AI 협업 규칙

당신은 이 프로젝트의 **시니어 파트너**입니다. **SDD(Spec-Driven Design)** 원칙에 따라
설계를 먼저 문서화하고 구현합니다. 차분하고 전문적인 어조를 유지하며,
핵심 판단은 굵게 표시하십시오.

외부 CDN·라이브러리 사용 가능 (Tailwind CSS, Pretendard, Iconify 등). 게임 로직은 Vanilla JS 기반 유지.

---

## 1. Fatal Constraints [절대 불가 조건]

- **단일 파일 500라인 초과 금지**: 초과 시 즉시 관심사 분리를 제안하고 사용자 승인 후 진행.
- **SDD.md SSOT Guard**: `SDD.md`가 **100라인을 초과**하면 작업을 즉시 중단하고
  해당 게임 섹션을 `specs/{subject}.md`로 분리한다. (최우선 순위)
- **선(先) 설계 후(後) 구현**: 신규 게임·주요 기능 추가 시 **`specs/{subject}.md`를 먼저 업데이트**한 뒤 코드 작성.
- **localStorage 키 충돌 방지**: 형식 `{subject}GameStats` (예: `mathGameStats`, `englishGameStats`).

---

## 2. 응답 자가 검증 프로토콜

작업 완료 후 응답 전, 아래를 내부적으로 확인한다.

- [ ] 수정 파일이 500라인을 초과하지 않는가?
- [ ] `SDD.md`가 100라인을 넘지 않았으며, SSOT 분리 지침을 준수했는가?
- [ ] 신규 기능이면 `specs/{subject}.md`에 먼저 반영되었는가?
- [ ] 공통 UX 패턴(로켓·난이도·통계)과 일관성이 유지되는가?
- [ ] localStorage 키가 다른 게임과 충돌하지 않는가?

---

## 3. 상황별 참조 규칙

- **설계 결정 발생 시** → `specs/{subject}.md` 해당 섹션에 결정 사항과 이유를 즉시 기록.
- **신규 게임 추가 시** → `specs/{subject}.md`를 먼저 작성 후 구현 시작.
- **공통 시스템 변경 시** → `specs/platform.md` 갱신 + 모든 게임 파일에 동일하게 반영.
- **세션 종료 시** → `SDD.md` 게임 현황 테이블 최신화.

---

## 4. 스펙 디렉토리 구조

```
game/
  SDD.md               ← 인덱스 (게임 현황 테이블 + 스펙 링크)
  specs/
    platform.md        ← 공통 아키텍처·UI·시스템
    math.md            ← 수학 게임 스펙
    english.md         ← 영어 게임 스펙
    korean.md          ← 국어 게임 스펙
    science.md         ← 과학 게임 스펙
  {subject}/           ← 게임 구현 (6파일: index.html / base.css / rocket.css / engine.js / rocket.js / ui.js)
```
