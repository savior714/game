# 전역 보상 인벤토리 시스템 명세 (Reward Inventory Spec)

이 문서는 모든 학습 페이지에서 공통으로 사용될 보상 저장 및 관리 시스템의 기술적 사양을 정의합니다.

## 1. 데이터 구조 (Data Schema)

`localStorage`의 `study_rewards` 키에 JSON 형태로 저장됩니다.

```json
{
  "youtube_minutes": 0,
  "snacks": 0,
  "marble_plays": 0,
  "last_updated": "2026-03-27T00:00:00Z"
}
```

## 2. 핵심 API (Core API)

`RewardSystem` 전역 객체를 통해 접근합니다.

- `RewardSystem.getState()`: 현재 보상 상태 반환
- `RewardSystem.add(type, amount)`: 특정 타입의 보상을 추가하고 UI 갱신
  - `type`: 'youtube' | 'snack' | 'marble'
- `RewardSystem.consume(type)`: 보상 사용을 시도
  - 사용 가능 여부 확인 후 차감
  - 유튜브일 경우 타이머 모달 표시
  - 마블일 경우 게임 실행 오버레이 표시
- `RewardSystem.updateUI()`: 상단 인벤토리 바의 수치와 애니메이션 업데이트

## 3. UI/UX 사양

### 3.1 인벤토리 바 (Inventory Bar)
- **위치**: 모든 페이지의 상단 (`sticky` 또는 `fixed`)
- **디자인**: 
  - 반투명 배경 (`backdrop-filter: blur(8px)`)
  - 각 보상 아이템은 아이콘 + 수치로 구성
  - 클릭 시 해당 보상을 사용할 것인지 묻는 툴팁 또는 미니 팝업 표시
- **애니메이션**: 보상이 늘어날 때 숫자가 올라가는 효과 (Counter animation)

### 3.2 선택 팝업 (Choice Popup)
- 룰렛에서 당첨된 직후 등장
- **메시지**: "보상을 획득했습니다! 지금 사용할까요?"
- **버튼**:
  - `[지금 하기]`: 즉시 보상 효과 실행 (타이머 시작 등)
  - `[나중에 하기]`: 인벤토리 아이콘으로 날아가는 애니메이션 후 저장

## 4. 유튜브 보상 정책 (Updated)
- 보상은 15분 단위로 획득하며, 인벤토리에는 **총 누적 분(Minute)**만 표시됩니다.
- **별도의 타이머 기능을 제공하지 않습니다.** 부모님이 남은 시간을 확인하고 시청 여부를 결정하는 용도로 사용됩니다.
- 시청 완료 후 "사용 기록(Deduct 15 min)" 버튼을 통해 수동으로 차감할 수 있습니다.

## 5. 디자인 고도화 원칙 (Anti-AI Slop Strategy)

천편일률적인 템플릿 기반의 AI 스타일(Glassmorphism, Excessive Roundness, Neon Gradients 등)을 지양하고, 실제 아이들이 친숙함을 느낄 수 있는 독창적인 질감을 추구합니다.

- **Texture & Feel**: 완벽한 매끄러움보다는 **종이 질감(Paper Texture)**이나 **크레파스/수채화 필치**가 느껴지는 요소들을 배치합니다.
- **Iconography**: 범용 오픈소스 아이콘(Material Design, Lucide 등)보다는, 이 프로젝트만을 위해 **직접 드로잉된 스타일의 아이콘**으로 점차 교체해 나갑니다.
- **Interaction**: 단순한 `Bounce`나 `Scale` 대신, 마치 생물처럼 움직이는 듯한 **유기적인 상호작용(Squash and Stretch)**을 지향합니다.
- **Typography**: 브라우저 기본 서체나 너무 기계적인 고딕보다는, **가독성이 높으면서도 부드러운 손글씨 느낌의 서체**를 활용합니다.
