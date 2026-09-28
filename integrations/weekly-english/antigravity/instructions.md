# 안티그래비티 주간 영단어 등록 에이전트 지침서

이 지침서는 사용자가 학원 시험지 사진을 업로드하고 "이번 주 시험으로 등록해줘"라고 지시했을 때 안티그래비티 에이전트가 수행해야 하는 단일 공식 표준 규약입니다.

주간 영단어 사진 등록의 에이전트 연동은 **안티그래비티 로컬 MCP 연동 하나만 정식 경로**로 사용하며, 별도의 외부 중계 함수나 제3자 액션을 일체 거치지 않습니다.

---

## 1. 정식 런타임 체인

```text
시험지 사진
→ 안티그래비티 시각 분석 (1차 패스)
→ 2차 독립 시각 대조 (2차 패스)
→ 로컬 stdio MCP (integrations/weekly-english/antigravity/mcp-server.mjs)
→ 기준 전송 계층 (scripts/register-weekly-english-set.mjs: executeIngestionFlow)
→ 실환경 수파베이스 원격 프로시저 호출 (register_weekly_english_set)
→ 정식 역조회 검증 (get_current_weekly_english_set)
→ 원문 충실도 검증 (source-fidelity verification)
→ 최종 등록 완료
```

- **표준 입출력 직결**: 로컬 stdio MCP 서버가 기준 전송 스크립트를 재사용하여 수파베이스 원격 프로시저를 직접 호출합니다.
- **단일 권위**: 모든 유효성 검증, 역조회 일치, 원문 충실도 검증은 `scripts/register-weekly-english-set.mjs`와 데이터베이스 프로시저가 단일 권위로 보장합니다.

---

## 2. 간편 1회성 환경 설정

별도의 비밀번호 데몬이나 복잡한 자격증명 관리 도구 없이, 안티그래비티 MCP 설정 파일(예: `mcp_config.json`)의 `mcpServers` 항목에 아래와 같이 등록합니다:

```json
{
  "mcpServers": {
    "weekly-english": {
      "command": "node",
      "args": [
        "/absolute/path/to/game/integrations/weekly-english/antigravity/mcp-server.mjs"
      ],
      "env": {
        "WEEKLY_AGENT_TOKEN": "weit_YOUR_TOKEN"
      }
    }
  }
}
```

- `WEEKLY_AGENT_TOKEN`: 보호자 모드 화면에서 발급받은 주간 영단어 전용 토큰을 설정합니다.
- 실제 비밀 토큰 값은 저장소 파일이나 공개 설정에 커밋하지 않습니다.

---

## 3. 핵심 목표 및 원칙

- **단일 문장 실행**: 사용자는 최초 도구 연결 이후 매주 사진 업로드와 한 문장 지시 외에 추가 작업을 하지 않아야 합니다.
- **사진 원본 보존 배제**: 사진 원본을 저장소나 서버에 업로드하지 않으며, 오직 시각 분석 입력으로만 사용합니다.
- **원문 충실성 유지**: 인쇄된 단어와 뜻 설명의 철자, 대소문자, 문장부호, 학원 측의 인쇄 오타를 에이전트가 임의로 교정하지 않습니다.
- **근거 없는 신뢰도 배제**: 임의의 신뢰도 수치(예: 93%)를 만들어 판단 근거로 삼지 않으며, 반드시 독립 2차 시각 대조와 서버 검증을 통해 판단합니다.
- **비밀 보장**: 모델의 대화 출력, 로그, 프롬프트에 주간 에이전트 토큰이 절대 평문으로 노출되어서는 안 됩니다.

---

## 4. 작업 흐름

### 1단계: 시각 분석 (1차 패스)
1. 시험지 양식 구조를 파악합니다 (상단 인쇄 시험 날짜, 좌우 단어 영역, 설명 영역, 번호 매칭).
2. 인쇄된 시험 날짜를 `YYYY-MM-DD` 형식으로 추출합니다.
3. 단어(answer)와 뜻 설명(prompt)의 짝(pair)을 추출합니다 (정상 시험지는 8~12개).

### 2단계: 자동 2차 시각 대조 (2차 패스)
1. 원본 이미지를 독립적으로 다시 읽어 다음 항목을 철저하게 대조합니다:
   - 시험 날짜
   - 전체 문항 수
   - 각 단어의 철자
   - 각 뜻 설명의 원문
   - 번호 매칭
   - 누락 또는 중복 문항 여부
2. 1차와 2차 결과가 완벽하게 일치할 때만 등록 단계로 진행합니다.

### 3단계: 도구 호출
`register_weekly_english_candidate` 도구를 호출합니다:
```json
{
  "candidate": {
    "schemaVersion": 1,
    "testDate": "2026-10-02",
    "items": [
      {
        "answer": "courage",
        "prompt": "the ability to do something frightening"
      }
    ]
  }
}
```

### 4단계: 결과 판정 및 최종 응답
- 도구 응답의 상태가 `REGISTERED_NEW`, `REGISTERED_REVISION`, `REGISTERED_CONFIRMED_REVISION`, `NO_OP` 중 하나이고,
- `readBackVerified === true` 및 `sourceFidelityVerified === true`인 경우에만 사용자에게 다음 한 문장으로 답합니다:
  > **등록 완료** (시험 날짜: YYYY-MM-DD, 총 N문항)

---

## 5. 예외 및 분기 처리

### 시각적 모호성
- 사진 해상도 저하나 얼룩 등으로 단어 철자나 번호 매칭이 불명확한 경우, **절대로 서버 등록을 호출하지 않습니다.**
- 전체 표를 다시 묻지 않고, 문제가 있는 특정 문항만 단답형으로 질문합니다.
  - 예시: *"7번 단어가 'principal'인지 'principle'인지 사진에서 명확하지 않습니다. 7번 단어만 확인해 주세요."*
- 사용자 답변으로 확인이 완료되면 해당 항목을 반영하여 등록을 진행합니다.

### 백엔드 확인 요청 (`NEEDS_CONFIRMATION`)
- 기존 세트와 동일 날짜에 다수의 단어가 변경되는 등의 사유로 도구가 `NEEDS_CONFIRMATION`을 반환한 경우:
  - 백엔드가 반환한 사유(reason)를 사용자 친화적인 최소 질문으로 전달합니다.
  - 예시: *"같은 10월 2일 시험인데 기존 세트와 5개 이상 차이가 납니다. 이 사진 내용으로 교체할까요?"*
- 사용자가 확인을 승인하면, 직전 응답에 포함되어 있던 지문 정보(`candidateFingerprint`, `expectedActiveFingerprint`, `expectedActiveRevision`)를 `confirmation` 객체에 그대로 담아 재호출합니다. (에이전트가 지문 값을 스스로 위조하거나 생성하지 않습니다.)

### 양식 불일치
- 사진이 평소 학원 시험지 구조와 완전히 달라 해석할 수 없는 경우 자동 등록하지 않고, 해석 불가능한 원인을 간결하게 설명합니다.
