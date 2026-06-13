# SPEC_TECH_korean_quantization_artifacts.md

# LLM 양자화 → 한글 깨짐 현상 — 원인·검출·복구

- **작성일**: 2026-06-13
- **영향 파일**: `domains/math/ui.js`, `shared/domain/milestone-tracker.js`, `shared/domain/growth-visualizer.js`
- **근본 원인**: LLM 양자화(INT4/INT8) → 토큰 확률 분포 왜곡 → 한글 음절 조합 오류

---

## 1. 현상

### 1.1 유니코드 이스케이프 (`\uXXXX`)

한글이 `\uXXXX` 형식으로 인코딩됨. 브라우저에서는 정상 표시되지만 소스 가독성·유지보수성에 나쁨.

```js
// 깨진 상태
fb.textContent = '\uc798\ud588\uc5b4\uc694! \uD83C\uDF89';

// 정상 상태
fb.textContent = '잘했어요! 🎉';
```

### 1.2 음절 조합 오류 (가장 치명적)

양자화로 인해 **잘못된 한글 음절**이 생성됨. `\uXXXX` 디코딩 후에도 깨진 상태 유지.

| 원본 (깨짐) | 정상 | 오류 유형 |
|------------|------|----------|
| `10문문 맞쳋어요` | `10문제 맞혔어요` | 자모 추가/변경 |
| `로뱁 배사 임꺽` | `로켓 발사 임무` | 완전 다른 음절 |
| `전부분정당` | `전부 정답` | 음절 병합/분리 오류 |
| `오래!` | `올라!` | 단모음 치환 |
| `므집 확제 워기` | `넉줄 확인 무기` | 자모 재배치 오류 |

### 1.3 이모지 서로게이트 페어 깨짐

이모지는 2바이트 유니코드(서로게이트 페어)를 사용하는데, 양자화 과정에서 **High/Low 서로게이트가 분리**되어 깨짐.

```
🛡️ (U+1F6E1 FE0F) → 🛡🏻 (서로게이트 분리)
😱 (U+1F631) → 😱🏻 (skin tone modifier 추가)
```

---

## 2. 근본 원인

### 2.1 토큰화 효율 차이

```
영어: "hello" → ["hello"] (1토큰, 효율 100%)
한글: "잘했어요" → ["\uc798", "\ud588", "\uc5b4\uc694"] (3토큰, 효율 33%)
```

한글은 자모 조합의 경우의 수(2만 자 이상)가 영어 알파벳(26자)보다 압도적으로 많아, **양자화된 토크나이저가 토큰을 효율적으로 분할하지 못함**.

### 2.2 양자화 → 가중치 정밀도 손실

```
FP32 가중치: 0.123456789
INT4 양자화: 0.125 (정밀도 손실 ~0.4%)
```

정밀도 손실 → **출력 확률 분포 왜곡** → 한글 음절 선택 오류.

### 2.3 확률 분포 왜곡의 구체적 영향

| 오류 유형 | 메커니즘 | 예시 |
|----------|---------|------|
| 자모 누락/추가 | 확률 임계값 하회/상승 | `문` → `문문` |
| 유사 음절 혼동 | 벡터 공간 근접성 | `정답` ↔ `정당` |
| 자모 재배치 | 토큰 경계 오류 | `로켓` → `로켫` |
| 이모지 분리 | 서로게이트 페어 분할 | `🛡️` → `🛡🏻` |

### 2.4 왜 모든 파일이 아닌 특정 파일만 깨지는가?

- **LLM 생성 파일**: 토큰화/양자화 영향 직접 받음
- **수동 작성 파일**: UTF-8 그대로 유지
- **동일 세션 내에서도**: 토큰 컨텍스트 길이에 따라 품질 저하 (context window 한계)

---

## 3. 검출 방법

### 3.1 유니코드 이스케이프 검출

```bash
# \uXXXX 패턴 검색 (모든 JS 파일)
grep -rn '\\u[0-9A-Fa-f]\{4\}' --include='*.js' .
```

### 3.2 음절 조합 오류 검출 (수동)

`\uXXXX` 디코딩 후 다음 패턴 확인:
- 중복 음절 (`문문`, `과문`)
- 비표준 자모 조합 (`켫`, `긵`, `쳋`)
- 문맥상 의미 불일치 (`배사` → `발사`, `정당` → `정답`)

### 3.3 이모지 서로게이트 페어 검출

```bash
# 서로게이트 영역(U+D800-U+DFFF) 포함 검색
grep -Pn '[\x{D800}-\x{DFFF}]' --include='*.js' .
```

---

## 4. 복구 절차

### 4.1 유니코드 이스케이프 → UTF-8 변환

**Node.js** (서로게이트 페어 지원):

```js
const fs = require('fs');

function fixUnicodeEscapes(content) {
    const result = [];
    let i = 0;
    while (i < content.length) {
        if (content[i] === '\\' && content[i+1] === 'u' && i + 5 < content.length) {
            const hex = content.substring(i+2, i+6);
            if (/^[0-9A-Fa-f]{4}$/.test(hex)) {
                const codePoint = parseInt(hex, 16);
                // High surrogate (0xD800-0xDBFF) 처리
                if (codePoint >= 0xD800 && codePoint <= 0xDBFF) {
                    if (i + 11 < content.length && 
                        content[i+6] === '\\' && content[i+7] === 'u') {
                        const nextHex = content.substring(i+8, i+12);
                        if (/^[0-9A-Fa-f]{4}$/.test(nextHex)) {
                            const low = parseInt(nextHex, 16);
                            if (low >= 0xDC00 && low <= 0xDFFF) {
                                const cp = 0x10000 + ((codePoint - 0xD800) << 10) + (low - 0xDC00);
                                result.push(String.fromCodePoint(cp));
                                i += 12;
                                continue;
                            }
                        }
                    }
                }
                result.push(String.fromCodePoint(codePoint));
                i += 6;
                continue;
            }
        }
        result.push(content[i]);
        i++;
    }
    return result.join('');
}

let content = fs.readFileSync('file.js', 'utf-8');
content = fixUnicodeEscapes(content);
fs.writeFileSync('file.js', content, 'utf-8');
```

**Perl** (단순 `\uXXXX`만):

```bash
perl -i -pe 's/\\u([0-9A-Fa-f]{4})/chr(hex($1))/ge' file.js
```

### 4.2 음절 조합 오류 교정

교정 사전을 정의하고 순차 적용:

```js
const corrections = [
    ['문문', '문제'],
    ['맞쳋어요', '맞혔어요'],
    ['로뱁 배사 임꺽', '로켓 발사 임무'],
    ['전부분정당', '전부 정답'],
    ['오래!', '올라!'],
    // ... 추가
];

for (const [broken, correct] of corrections) {
    content = content.split(broken).join(correct);
}
```

### 4.3 이모지 서로게이트 페어 복원

```js
content = content.split('🛡🏻').join('🛡️');
content = content.split('😱🏻').join('😱');
```

---

## 5. 예방 방안

| 방법 | 설명 | 효과 | 난이도 |
|------|------|------|--------|
| **양자화 해제** | FP16/FP32 모델 사용 | ★★★★★ | 낮음 |
| **한글 특화 토크나이저** | KoreanBPE 등 교체 | ★★★★☆ | 중간 |
| **Temperature ↓** | 생성 시 randomness 줄임 | ★★★☆☆ | 낮음 |
| **사후 검증 스크립트** | CI/CD에서 자동 검출 | ★★★☆☆ | 중간 |
| **수동 리뷰** | 한글 출력물 수동 확인 | ★★☆☆☆ | 높음 (노력) |

### 5.1 CI/CD 자동 검출 (권장)

```bash
#!/bin/bash
# scripts/check-korean-utf8.sh

ERRORS=0

# 1. \uXXXX 이스케이프 검출
if grep -rn '\\u[0-9A-Fa-f]\{4\}' --include='*.js' domains/ shared/ | grep -v node_modules; then
    echo "ERROR: Unicode escapes found in JS files"
    ERRORS=$((ERRORS + 1))
fi

# 2. 비표준 자모 조합 검출 (예시)
if grep -Pn '[\x{AC00}-\x{D7AF}]' --include='*.js' domains/ shared/ | grep -E '(켫|긵|쳋|문문)'; then
    echo "WARNING: Possible Korean corruption detected"
fi

exit $ERRORS
```

---

## 6. 참고 자료

- [Unicode 서로게이트 페어](https://ko.wikipedia.org/wiki/서로게이트_페어)
- [LLM Quantization](https://huggingface.co/docs/transformers/main/en/concepts_quantization)
- [BPE Tokenization](https://en.wikipedia.org/wiki/Byte_pair_encoding)

---

## 7. 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-06-13 | 초안 작성 — `math/ui.js`, `milestone-tracker.js`, `growth-visualizer.js` 복구 기록 |
