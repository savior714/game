---
scope: detail
domain: core
parent: .agents/core/error_patterns.md
lazy_load: true
---
<!-- Language: ko -->

## 2. 테스트 실수

### 2.1 Vitest mock 누락

**증상**: `vi.mock()` 후 "No 'X' export is defined on the 'Y' mock" 에러.

**원인**: 컴포넌트가 import하는 모든 export를 mock에 포함하지 않음.

```
❌ WRONG: 누락된 mock export
vi.mock('@/src/stores/tabStore', () => ({
  useTabActions: vi.fn(),
  useTabContext: vi.fn(),
}))
// 컴포넌트가 ensureConsultationTabPresets도 import함 → 에러

✅ CORRECT: 모든 import를 mock에 포함
vi.mock('@/src/stores/tabStore', () => ({
  useTabActions: vi.fn(),
  useTabContext: vi.fn(),
  ensureConsultationTabPresets: vi.fn(),  // ← 추가
}))
```

### 2.2 Vitest localStorage persistent state

**증상**: 테스트 A에서 설정한 값이 테스트 B에 영향을 줌.

**원인**: `SettingsProvider` 등이 `localStorage`에 상태를 저장하고, 다음 테스트에서 그 값을 읽음.

```
❌ WRONG: localStorage 초기화 안 함
test('singleDeskMode false', () => {
  render(<SettingsProvider><Component /></SettingsProvider>)
  // localStorage에 singleDeskMode: true가 남아있음
})

✅ CORRECT: beforeEach에서 명시적 초기화
beforeEach(() => {
  localStorage.setItem("global-settings-v1", JSON.stringify({
    singleDeskMode: false,
  }))
})
```

### 2.3 Duplicate testId → getAllByTestId

**증상**: `getByTestId()`가 "Found multiple elements with the same test id" 에러.

**원인**: 여러 요소가 동일한 `data-testid`를 가짐.

```
❌ WRONG: getByTestId (중복 요소가 있으면 에러)
const items = screen.getByTestId('item')

✅ CORRECT: getAllByTestId + 개수 검증
const items = screen.getAllByTestId('item')
expect(items.length).toBe(3)
```

### 2.4 React destructuring default 값 누락

**증상**: 테스트에서 "Cannot read properties of undefined (reading 'map')" 에러.

**원인**: mock이 `undefined`를 반환할 때, 컴포넌트가 `.map()` 등을 호출함.

```
❌ WRONG: default 값 없음
const { prescription } = examination
prescription.map(...)  // undefined.map → 에러

✅ CORRECT: default 값 추가
const { prescription = [] } = examination
prescription.map(...)  // safe
```

### 2.5 Vitest split 파일 네이밍 패턴 불일치 (.1/.2/.3)

**증상**: `vitest run tests/unit/dashboard/dashboard-layout-migration.test.1.ts` 실행 시 "No test files found" — 테스트가 실행되지 않음.

**원인**: vitest include 패턴이 `tests/unit/**/*.{test,spec}.{ts,tsx}` 또는 `tests/unit/**/*.test.*.tsx` 로 정의되어 있음. `.1.ts`, `.2.ts`, `.3.ts` 파일은 이 패턴에 매칭되지 않음.

```
❌ WRONG: .1/.2/.3 네이밍
dashboard-layout-migration.test.1.ts  → vitest include 패턴 매칭 실패
dashboard-layout-migration.test.2.ts  → vitest include 패턴 매칭 실패

✅ CORRECT: <name>.<category>.test.ts 네이밍
dashboard-layout-migration.sanitize.test.ts  → 매칭 성공
dashboard-layout-migration.schema.test.ts    → 매칭 성공
dashboard-layout-migration.id.test.ts        → 매칭 성공
```

**예방**: 파일 분할 시 vitest config 의 include 패턴을 먼저 확인하고, 패턴에 맞는 네이밍 사용. 프로젝트 내 기존 split 파일 패턴(`<name>.<category>.test.ts`)을 따름.

**session_note**: "PLAN_discover_implement_hygiene_pilot_20260603_101216.md IMP-002 구현 시 발생. vitest 0 tests found → 네이밍 패턴 매칭 실패 확인. sanitize/schema/id 로 리네임하여 해결."

### 2.6 vi.mock() 별도 파일 분리 시 hoisting 실패

**증상**: `vi.mock()` 을 별도 utils 파일(`*.test-utils.tsx`)에 넣으면 "useAuth must be used within an AuthProvider" — mock 이 적용되지 않음.

**원인**: vitest 의 `vi.mock()` hoisting 은 파일 parse 시점에 top-level 로 끌어올리는데, **별도 import된 파일의 `vi.mock()` 은 hoisting 대상에서 제외됨**. import 시 mock 이 아직 정의되지 않은 상태가 되어 실제 모듈이 로드됨.

```
❌ WRONG: 별도 파일에 vi.mock() 분리
// ConsultationPage.test-utils.tsx
vi.mock("../../../src/contexts/AuthContext", () => ({ ... }))  // hoisting 안 됨!

// ConsultationPage.test.rendering.tsx
import "./ConsultationPage.test-utils"  // mock 이 import 시점에 적용되지 않음
render(<ConsultationPage {...props} />)  // useAuth → AuthProvider 없음 → 에러

✅ CORRECT: 각 테스트 파일에 mock inline
// ConsultationPage.test.rendering.tsx
vi.mock("../../../src/contexts/AuthContext", () => ({ ... }))  // hoisting 됨!
render(<ConsultationPage {...props} />)  // mock 적용됨

✅ CORRECT: 공유 데이터만 utils 로 분리 (mock 은 inline 유지)
// ConsultationPage.test-utils.tsx — mock 없이 createDefaultProps 만 export
// 각 테스트 파일에서 vi.mock() inline + createDefaultProps import
```

**예방**: 테스트 분할 시 `vi.mock()` 은 반드시 각 split 파일에 inline 으로 복제. mock 이 아닌 데이터(createDefaultProps, 상수 등)만 utils 파일로 분리.

**session_note**: "PLAN_discover_implement_hygiene_pilot_20260603_101216.md IMP-005 구현 시 발생. utils 파일에 vi.mock() 넣으면 hoisting 실패 → rendering 테스트 17개 실패. mock inline 복제하여 해결."

### 2.7 beforeEach/cleanup 누락 → 테스트 간 상태 오염

**증상**: 테스트 A에서 `vi.spyOn()`이나 `jest.useFakeTimers()` 설정한 값이 테스트 B에 영향을 줌. 순서 의존적 실패.

**원인**: `beforeEach`에서 mock/스파이/가짜 타이머를 설정했지만, `afterEach`나 `afterAll`에서 정리(cleanup)하지 않음. 다음 테스트가 이전 상태 그대로 상속받음.

```
❌ WRONG: beforeEach만, afterEach 없음
test('clock runs', () => {
  vi.useFakeTimers()
  render(<Component />)
  // ... 테스트
})
test('clock stops', () => {
  render(<Component />)  // fake timers가 여전히 활성 → 에러
})

✅ CORRECT: beforeEach 설정 + afterEach 정리
test('clock runs', () => {
  vi.useFakeTimers()
  render(<Component />)
})
afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

✅ CORRECT: spyOn도 cleanup
beforeEach(() => {
  spy = vi.spyOn(api, 'fetchData').mockResolvedValue(mockData)
})
afterEach(() => {
  spy.mockRestore()
  vi.clearAllMocks()
})
```

**예방**: `vi.useFakeTimers()`, `vi.spyOn()`, `localStorage.setItem()` 등 **상태를 변경하는 모든 설정**은 `afterEach`에서 반드시 정리. `vi.clearAllMocks()`는 mock 호출 기록 초기화용 — spy restore와 함께 사용.

### 2.8 vi.mock() 동적 import vs 정적 hoisting

**증상**: `vi.mock()` 이 적용되지 않거나, ESM import 시 "module has no default export" 에러.

**원인**: vitest v0.34+ 부터 `vi.mock()` hoisting 이 **정적 import**에만 적용됨. 동적 `import()` 나 **ESM default export** mock 시에는 `{ virtual: true }` 또는 `mockResolvedValue` 필요.

```
❌ WRONG: default export mock 불일치
// module.ts — export default { fn: () => {} }
vi.mock('./module', () => ({
  default: { fn: vi.fn() },  // ❌ vitest은 { fn: vi.fn() } 기대
}))

✅ CORRECT: default export mock
vi.mock('./module', () => ({
  default: vi.fn(),  // 또는
  __esModule: true,
  default: { fn: vi.fn() }
}))

✅ CORRECT: 동적 import mock (hoisting 대상 아님)
vi.mock('./module', () => ({ fn: vi.fn() }), { virtual: true })

✅ CORRECT: mockResolvedValue (Promise 반환 함수)
vi.mock('./api', () => ({
  fetchData: vi.fn().mockResolvedValue(mockData)
}))
```

**예방**: ESM default export mock 시 `__esModule: true` 플래그 포함. Promise 반환 함수는 `mockResolvedValue` 사용. hoisting 대상이 아닌 동적 import 시 `{ virtual: true }` 옵션 추가.

**session_note**: "vitest v0.34+ ESM default export mock 패턴 변경. { virtual: true } 필요 시 hoisting 비활성화됨 — import 위치 주의."

### 2.9 getByText() 중복 매칭 오류 (메시지 전역 고유성)

**증상**: `getByText('정상')` 등으로 요소를 찾을 때 `"Found multiple elements with the text: 정상"` 에러 발생하며 테스트 실패.

**원인**: 화면상에 동일한 텍스트("정상", "주의", "오류" 등 상태 배지나 라벨)가 여러 개 존재하여, 단일 요소를 기대하는 `getByText()`가 어떤 요소를 가리키는지 특정하지 못함.

```
❌ WRONG: 너무 일반적인 텍스트로 조회하여 중복 발생
const statusBadge = screen.getByText('정상')

✅ CORRECT: 특정 컴포넌트의 유니크한 텍스트로 찾거나, getAllByText + 인덱스 매칭, 또는 testId/role 사용
// 방법 1: 고유 식별 메시지 사용
const successMsg = screen.getByText('상병 S50.000 codeset 1 정상 검증')

// 방법 2: getAllByText로 배열 반환 받아 검증
const statusBadges = screen.getAllByText('정상')
expect(statusBadges[0]).toBeInTheDocument()

// 방법 3: data-testid나 container 내 범위 좁히기
const container = screen.getByTestId('status-panel')
const statusBadge = within(container).getByText('정상')
```

**예방**: 컴포넌트 상태 배지나 메시지가 겹치기 쉬운 일반 명사("정상", "오류", "대기")일 경우 `getByText` 대신 `data-testid`를 지정해 고유하게 식별하거나, `within`을 사용하여 검색 범위를 부모 컨테이너로 제한.

### 2.10 비동기 업데이트 누락 및 act(...) 경고

**증상**: `"Warning: An update to Component inside a test was not wrapped in act(...)"` 콘솔 경고가 뜨거나, 비동기 상태 변화가 화면에 반영되기 전에 단언문(assert)이 실행되어 테스트가 실패함.

**원인**: API 응답 수신, 타이머 실행 등 비동기 로직으로 인해 컴포넌트 상태가 변경되는데, 테스트 코드에서 렌더링 사이클이 완료되기를 기다리지 않고 동기식(`getByText`)으로 바로 검증했기 때문.

```
❌ WRONG: 비동기 데이터 변경을 기다리지 않고 바로 동기 검증 시도
render(<Dashboard />)
// 데이터 fetch 완료 전이므로 요소를 찾지 못해 실패
expect(screen.getByText('로딩 완료')).toBeInTheDocument()

✅ CORRECT: findBy* (내부적으로 waitFor가 내장됨)를 활용해 비동기 상태 변경 대기
render(<Dashboard />)
const status = await screen.findByText('로딩 완료') // 자동 대기 및 act 감싸기 수행
expect(status).toBeInTheDocument()

✅ CORRECT: waitFor를 이용한 다중 단언식 처리
render(<Dashboard />)
await waitFor(() => {
  expect(screen.getByText('환자 정보 수신 완료')).toBeInTheDocument()
  expect(screen.getByText('진료 시작')).toBeInTheDocument()
})
```

**예방**: 컴포넌트 내부에서 비동기 작업(API 호출, dynamic import 등)이 완료된 후 화면이 변하는 구간은 절대 `getBy*`나 `queryBy*`로 검증하지 말고, `findBy*`나 `waitFor`를 사용하여 React가 상태를 안전하게 업데이트할 시간을 주도록 조치.

---

