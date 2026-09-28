# 챗지피티 맞춤형 지피티(Custom GPT) 1회성 설정 가이드

이 문서는 사용자가 최초 1회 챗지피티(ChatGPT)에 맞춤형 액션(Custom Action)을 연결하여 매주 시험지 사진 업로드만으로 단어 등록을 완료할 수 있도록 설정하는 방법입니다.

---

## 1. 맞춤형 지피티 생성

1. [ChatGPT](https://chatgpt.com)에 로그인한 후 좌측 메뉴에서 **Explore GPTs**를 누르고 우측 상단의 **+ Create**를 클릭합니다.
2. 상단 탭에서 **Configure**를 선택합니다.
3. 기본 정보 입력:
   - **Name**: `에이든 주간 영어 등록기`
   - **Description**: `주간 영어 시험지 사진을 판독하여 에이든게임 공식 주간 시험으로 등록합니다.`
   - **Instructions**: [`instructions.md`](./instructions.md) 파일의 전체 내용을 복사하여 붙여넣습니다.

---

## 2. 액션(Action) 연결

1. 하단의 **Actions** 섹션에서 **Create new action** 버튼을 클릭합니다.
2. **Schema** 입력란에 [`openapi.yaml`](./openapi.yaml) 파일의 전체 내용을 복사하여 붙여넣습니다.
3. 스키마에 오류가 없는지 확인합니다. 다음 2개의 엔드포인트가 인식되어야 합니다:
   - `registerWeeklyEnglishCandidate` (POST /register)
   - `getCurrentWeeklyEnglishSet` (GET /current)

---

## 3. 인증(Authentication) 설정 (가장 중요)

1. Action 설정 페이지 상단의 **Authentication** 옆 연필 아이콘(Edit)을 클릭합니다.
2. 다음과 같이 설정합니다:
   - **Authentication Type**: `API Key` 선택
   - **API Key**: 발급받은 주간 에이전트 토큰 (`weit_...`) 입력
   - **Auth Type**: `Custom` 선택
   - **Custom Header Name**: `X-Aiden-Weekly-Token` 입력
3. **Save**를 눌러 저장합니다.

> [!IMPORTANT]
> - 토큰은 지피티 지침서(Instructions), 대화창, 프롬프트, 깃 저장소에 절대 직접 입력하지 않습니다.
> - 위와 같이 챗지피티의 보안 헤더 주입 기능에만 등록하여 안전하게 격리합니다.

---

## 4. 매주 사용 방법

설정이 완료된 후에는 매주 다음과 같이 간단하게 사용합니다:

1. 해당 맞춤형 지피티와의 대화창을 엽니다.
2. 학원 시험지 사진을 업로드합니다.
3. 다음 한 문장만 전송합니다:
   > **이번 주 시험으로 등록해줘**
4. 지피티가 2차 시각 대조와 서버 등록 검증을 완료한 뒤 "등록 완료" 메시지를 반환합니다.
