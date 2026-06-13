# CSS 변수 순환 참조 디버깅

## 문제 현상

CSS에서 `var(--token)`이 서로를 참조하며 무한 루프가 발생하면, 브라우저는 해당 값을 해석하지 못하고:
- 기존 값 유지 (fallback)
- 또는 `0` / `none` 등 기본값으로 처리

## EMR 프로젝트에서의 발견 사례

### 발생 위치
- **tokens.css** line 119: `--radius: var(--radius-md);`
- **globals.css** line 31: `--radius-md: calc(var(--radius) - 2px);`

### 체인 분석
```
--radius-md (globals.css)
  → calc(var(--radius) - 2px)
    → var(--radius) (tokens.css)
      → var(--radius-md) (tokens.css)
        → ... 무한 루프
```

### 증상
- `border-radius: var(--radius-md)` 설정해도 모서리가 둥글지 않음
- 브라우저 DevTools에서 `--radius-md` 값이 `[calculation]` 또는 `invalid`로 표시됨
- 기존 하드코딩된 16px이 그대로 유지되는 것처럼 보임

## 해결 방법

### 1. 하드코딩된 픽셀 값 사용 (권장)
```css
border-radius: 8px; /* var(--radius-md) 대신 직접 값 */
```

### 2. 토큰 체인 재구성
순환이 발생하지 않도록 변수 의존성 그래프를 DAG(Directed Acyclic Graph)로 유지.

### 3. 디버깅 방법
```bash
# 브라우저 DevTools에서 확인
:root { --test: var(--radius-md); }
/* console.log(getComputedStyle(document.documentElement).getPropertyValue('--test')) */
```

## 관련 파일
- `apps/renderer/src/styles/tokens.css`
- `apps/renderer/src/styles/globals.css`