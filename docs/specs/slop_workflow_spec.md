# Spec: High-Fidelity Architect Workflow (/slop)

## 1. 개요 (Overview)
AI 에이전트가 생성하는 코드의 품질을 "시니어 아키텍트" 수준으로 유지하고, 일반적인 AI의 조잡한 패턴(AI Slop)을 원천 차단하기 위한 강제적 워크플로우를 정의한다.

## 2. 핵심 원칙 (Core Principles)

### 2.1. Zero-Slop Design (Visual & CSS)
- **Systemic Consistency**: 매직 넘버 사용 금지, 디자인 시스템(CSS 변수 등) 준수.
- **Structural Semantics**: 시맨틱 HTML(`main`, `section` 등) 우선 사용.
- **Minimalist Aesthetic**: 과도한 장식 배제, 타이포그래피와 공백 강조.
- **Responsive Integrity**: 모바일 퍼스트 및 고유 크기 조절(`clamp`, `min-max`) 사용.

### 2.2. SDD (Spec-Driven Design) Architecture
- **Interface First**: 구현 전 TypeScript 인터페이스/타입 정의 필수.
- **Logic Separation**: 비즈니스 로직과 프레젠테이션 레이어의 엄격한 분리.
- **No Magic Strings**: 모든 고정 값은 `enums` 또는 `const` 객체로 관리.
- **Error Resilience**: 명시적 에러 바운더리 및 폴백 구현.

### 2.3. Tool-First & Execution Policy
- **Verify Environment**: 실행 환경(Windows, Python 등) 사전 확인.
- **Diagnostic Over Guessing**: 터미널 도구를 이용한 실제 상태 진단 우선.
- **Atomic Commits**: 논리적 단위의 코드 제공.

## 3. 응답 구조 (Response Structure)
1. **Specification**: 아키텍처 결정 사항 요약.
2. **Implementation**: 계층 구조에 따른 코드 구현.
3. **Validation**: 검증 방법 설명.
4. **Next Step**: 후속 집중 작업 제시.

## 4. 물리적 위치
- `C:\Users\savio\.gemini\antigravity\global_workflows\slop.md`
