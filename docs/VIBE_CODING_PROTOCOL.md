# Vibe Coding Protocol — Validate-and-Prune Strategy

> **핵심 원칙**: LLM이 코드를 "상상"하게 두지 말고, **컴파일러/런타임이 뱉은 팩트에 기반해 사고하도록 강제**한다.
> 토큰 효율 = 추론의 선명도. 정보를 적게 줄수록 LLM은 더 정교하게 사고한다.

---

## 1. Core: CLI 피드백 루프 (Validate-and-Prune)

LLM에게 "내 코드 맞아?"라고 묻는 순간 수천 토큰이 증발합니다.
**도구(Tool)가 뱉은 에러 메시지만 전달**하십시오.

```
Step 1: npm test  또는  npm run type-check  실행
         ↓ 에러 발생
Step 2: 파일명 + 라인 번호 + 에러 메시지만 복사
         ↓
Step 3: LLM에게 해당 정보 + 수정 대상 함수 시그니처만 제공
         ↓
Step 4: LLM이 수정 제안  →  다시 CLI 실행  →  에러 0개 확인
```

> **Prune(가지치기)**: 에러가 없는 파일, 관련 없는 로직, 라이브러리 소스 — 전부 제거한 뒤 LLM에 전달한다.

---

## 2. Hierarchy: 코드 컨텍스트 슬라이싱 (L1 / L2 / L3)

전체 파일을 읽히지 말고, **계층을 나눠 점진적으로 주입**하십시오.

| 계층 | 제공 데이터 | LLM의 역할 | 토큰 비용 |
| :---: | :--- | :--- | :---: |
| **L1: Skeleton** | 인터페이스 + 타입 선언부만 (`.d.ts` / `types.ts`) | 아키텍처 정합성 판단 | 최소 |
| **L2: Scope** | 수정 대상 함수 1개 (Body 포함) | 로직 오류 수정 + 타입 캐스팅 | 중간 |
| **L3: Mock** | 의존 함수의 이름/타입 시그니처만 | 외부 호출 규약 확인 | 최소 |

**원칙**: L1부터 시작. LLM이 L1만으로 해결 못할 때만 L2 추가. L3는 의존 관계 확인 시에만.

```
❌ 안티패턴: L1 + L2 + L3 전부 첨부하여 "고쳐줘" 요청
✅ 표준:     L1(스켈레톤)만 먼저 → LLM이 "L2 필요"라고 요청할 때 추가
```

---

## 3. Agent-to-Agent Protocol (Cursor / Antigravity 전용)

에이전트가 자의적으로 모든 파일을 인덱싱하지 못하도록 **컨텍스트 범위를 명시적으로 선언**합니다.

### 3-1. 표준 프롬프트 블록

```markdown
### [Agent-to-Agent Protocol]
**Target:** cursor-small-v2 / antigravity
**Context Constraint:**
1. DO NOT read files outside of the provided @symbols.
2. DO NOT index @Codebase — use @Symbols only.
3. USE CLI output (tsc / npm test stderr) as the ground truth for validation.
4. DO NOT read node_modules source — reference .d.ts only.

**Execution Flow:**
1. Read @Error_Log (Terminal stdout/stderr).
2. Locate the specific function in @Modified_File (L2 scope only).
3. Compare @Interface_Definition (L1 skeleton) with the implementation.
4. Provide ONLY the fixed code snippet. No explanations.
```

### 3-2. 환경별 적용 위치

| 환경 | 적용 위치 | 적용 방법 |
| :--- | :--- | :--- |
| **Cursor AI** | `.cursorrules` §3 | 파일에 고정 저장 → 모든 세션에 자동 적용 |
| **Antigravity** | `.antigravityrules` §7 | 주석 블록으로 에이전트 제약 |
| **Claude Code** | `CLAUDE.md` | Fatal Constraints §1에 통합 |

---

## 4. 실전 바이브 코딩 패턴

### 4-1. `@Codebase` 금지 → `@Symbols` 사용

```
❌ @Codebase        → 프로젝트 전체 인덱싱 (토큰 킬러)
✅ @UserService     → 해당 클래스 시그니처만 참조
✅ @interface User  → 타입 정의 1개만 참조
```

### 4-2. Short-Circuit Prompting (2단계 분리)

```
1단계: "이 코드에서 타입 에러가 날 가능성이 있는 곳 3군데만 리스트업해."
         → LLM이 위험 지점만 식별 (컨텍스트 최소)
         ↓
2단계: 확인된 위치의 코드만 전달 → 수정 요청
         → LLM이 정확한 컨텍스트에서 수정 (정밀도 최대)
```

### 4-3. Implementation Hiding

```typescript
// ✅ 검증과 무관한 보일러플레이트는 생략
class UserService {
  constructor(private readonly repo: UserRepository) {}

  async findById(id: string): Promise<User> {
    // ... implementation hidden
  }

  // 수정 대상: 이 메서드의 타입 에러 해결 필요
  async updateRole(id: string, role: UserRole): Promise<void> {
    const user = await this.findById(id);  // TS2345 발생 위치
    // ... implementation hidden
  }
}
```

> **효과**: LLM이 구현 세부사항이 아닌 **타입 계약(Contract)에만 집중**합니다.

### 4-4. CLI Ground Truth 패턴 (3개 환경 공통)

```powershell
# ✅ LLM에게 전달할 팩트 생성 (PowerShell)
$errors = powershell -NoProfile -Command "npm run type-check 2>&1 | Select-String 'error TS'"
# → 이 출력값만 LLM에 전달. 전체 파일 첨부 금지.
```

```bash
# ✅ LLM에게 전달할 팩트 생성 (Bash)
npm run type-check 2>&1 | grep "error TS" | head -20
```

---

## 5. 검증 체크리스트 (바이브 코딩 세션 전)

- [ ] `@Codebase` 참조를 모두 `@Symbols`로 교체했는가?
- [ ] LLM에 전달하는 컨텍스트가 L1(스켈레톤)부터 시작하는가?
- [ ] `tsc` / `npm test` 결과 에러 라인만 추출하여 전달하는가?
- [ ] 구현부 대신 `// ... implementation hidden`으로 생략했는가?
- [ ] Agent-to-Agent Protocol 블록이 프롬프트 상단에 선언되어 있는가?

---

> **참조**: [TS_TYPE_VALIDATION.md](TS_TYPE_VALIDATION.md) | [TS_ADVANCED_PATTERNS.md](TS_ADVANCED_PATTERNS.md)
> **적용 파일**: `.cursorrules` §3 | `.antigravityrules` §7 | `AI_GUIDELINES.md` §5
