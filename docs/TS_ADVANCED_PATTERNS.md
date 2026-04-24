# TypeScript Advanced Patterns — DDD / Symbol Reference / Type Flatten

> **상위 문서**: [TS_TYPE_VALIDATION.md](TS_TYPE_VALIDATION.md) (핵심 전략 SSOT)
> **목적**: 토큰 최적화를 위한 고급 아키텍처 패턴 모음.

---

## 1. DDD 기반 타입 분리 (Context Slimming)

> LLM이 구현 코드를 읽지 않고도 타입을 파악할 수 있도록 **Domain Layer를 물리적으로 분리**합니다.

### 1-1. 디렉토리 구조 표준

```
src/
  domain/
    models/         ← 순수 인터페이스/타입 정의만 (구현부 없음)
      user.ts          export interface User { id: string; role: UserRole }
      order.ts         export interface Order { ... }
    schemas/        ← Zod 스키마 (z.infer로 타입 자동 추출)
      user.schema.ts
    index.ts        ← Barrel Export — LLM 컨텍스트 단일 진입점
  services/         ← 구현부 (LLM 컨텍스트에서 제외)
  repositories/     ← I/O 레이어 (LLM 컨텍스트에서 제외)
```

### 1-2. Barrel Export 원칙

```typescript
// src/domain/index.ts — LLM에게 이 파일 하나만 전달
export type { User, UserRole } from './models/user';
export type { Order, OrderStatus } from './models/order';
export { UserSchema } from './schemas/user.schema';
```

| 전략 | 효과 |
| :--- | :--- |
| **Domain Layer 격리** | 로직 무시, 스키마만 빠르게 파악 |
| **Barrel Export** | 타입 주입 시 단일 파일만 참조 (토큰 ~70% 절감) |
| **Type-Only Files** | `.d.ts` 또는 `interface`만 있는 파일 → 구현부 0줄 |

### 1-3. `scripts/types-extractor.ts` 활용

```bash
# Barrel Export 전체를 LLM 최소 컨텍스트로 추출
npx ts-node scripts/types-extractor.ts --barrel src/domain/index.ts

# 단일 심볼만 추출
npx ts-node scripts/types-extractor.ts --name UserService
```

---

## 2. Symbol Reference 전략 (Agentic IDE 공통)

### 2-1. `@Files` 대신 `@Symbols` 사용

```
❌ @UserService.ts           → 전체 파일 (~200줄) 주입
✅ @interface UserService    → 시그니처 선언부만 (~10줄) 주입
✅ @type UserRole            → 타입 별칭 1줄만 주입
```

**행동 강령** (Cursor AI / Antigravity 공통):
- 타입 오류 수정 시 `@Symbol`로 관련 `interface`/`type`만 참조
- 구현 코드(`function body`)는 **명시적 요청 시에만** 읽음
- `node_modules` 소스는 절대 읽지 않음 → `.d.ts` 파일만 참조

### 2-2. Minimalist Prompt Template

```
[타입 에러 수정 표준 프롬프트]

tsc 에러: {에러 코드} — {에러 메시지}
발생 위치: {파일명}:{라인}

관련 타입 (src/domain/index.ts Barrel Export):
{types-extractor.ts 출력값}

에러 컨텍스트 (±5줄):
{type-check-slice.ps1 출력값}

요청: 구현 로직 수정 금지.
타입 호환성만 해결하는 Interface 확장 또는 Type Guard를 제안하라.
```

---

## 3. 타입 설계 원칙: Flatten & Simplify

> 복잡한 Conditional Type은 LLM의 **추론 루프**를 유발합니다.

| 안티패턴 | 표준 패턴 |
| :--- | :--- |
| `T extends U ? A : B extends C ? D : E` | 중간 명명 타입으로 **단계 분리** |
| 중첩 `infer` 체인 | `ts-morph`로 **정적 추출** 후 명시적 타입 사용 |
| 동일 유니온 타입 중복 선언 | `src/domain/models/`에서 **단일 선언 후 import** |

```typescript
// ❌ 안티패턴: 중첩 Conditional Type
type Result<T> = T extends string ? 'text' : T extends number ? 'num' : 'other';

// ✅ 표준: 중간 타입으로 평탄화
type StringResult = 'text';
type NumberResult = 'num';
type OtherResult = 'other';
type Result<T> = T extends string ? StringResult
  : T extends number ? NumberResult
  : OtherResult;
```

- **Opaque Types 지양**: 런타임에서 의미 없는 브랜딩은 LLM 추론 비용만 증가시킵니다.
- **자동화**: `scripts/types-extractor.ts --flat` 플래그로 Conditional Type 감지 및 경고를 받습니다.

---

> **참조**: [TS_TYPE_VALIDATION.md](TS_TYPE_VALIDATION.md) | [VIBE_CODING_PROTOCOL.md](VIBE_CODING_PROTOCOL.md)
> **스크립트**: `scripts/types-extractor.ts` | `scripts/type-check-slice.ps1`
