---
scope: workflow
status: active
---

# Exclusive Reservation Workflow

파일명은 과거 호환을 위해 유지한다. 일반 개발 claim이 아니라 충돌 비용이 큰 희소 자원만 예약한다.

## 기본값

- 일반 분석·구현·focused verification은 reservation 없이 병렬 실행한다.
- isolated worktree와 게시 전 최신 main 확인을 사용한다.
- 같은 파일이라는 이유만으로 자동 예약하지 않는다.
- push를 예약하지 않는다.

## Reservation 대상

- 같은 semantic hotspot/shared contract
- 같은 canonical browser/runtime identity, fixed port, profile, output directory
- 같은 generated bundle·atlas·registry·evidence·publication destination
- 같은 migration/schema 자원(해당되는 경우)

## Board

- Repository: `savior714/game`
- Issue: `#1`
- Title: `[Coordination] Exclusive Reservations`

## 형식

```text
RESERVE
WORK: <short work name>
OWNER: <short session name>
EXPIRES: <ISO-8601 UTC>
SCOPE:
- path:<exact hotspot path>
- contract:<stable contract name>
- resource:<stable runtime id>
- artifact:<stable output id>
- migration:<stable schema id>
```

GitHub comment ID가 reservation 식별자다. custom claim ID·nonce·base SHA·activation 시각을 만들지 않는다.

## 충돌

- `EXPIRES` 전이고 대응 `DONE`이 없는 reservation만 active다.
- 같은 typed scope token은 충돌한다.
- path는 같은 파일 또는 명시적으로 예약한 디렉터리 하위에서만 충돌한다.
- semantic overlap은 `contract:`로 명시한다.
- 충돌 reservation 중 먼저 게시된 comment만 유효하다.
- dependency가 있으면 metadata를 추가하지 않고 순차 실행한다.

## 실행

- exclusive mutation·long run 직전에만 board를 확인한다.
- scope 밖 exclusive 자원이 필요하면 기존 reservation을 종료하고 새 reservation을 게시한다.
- main 이동은 일반 Git preflight로 처리한다.
- unrelated 이동은 최신 main 위에 재적용하고 focused verification을 다시 실행한다.
- related 이동은 최신 상태에 맞게 변경을 조정한다.

## 종료

```text
DONE
RESERVATION: <GitHub comment ID>
```

완료·차단·포기 모두 자원을 해제한다.

## 로컬 위임

exclusive 자원이 필요한 prompt에만 다음을 전달한다.

```text
RESERVATION_COMMENT:
WORK:
OWNER:
EXPIRES:
SCOPE:
```

일반 병렬 prompt에는 reservation block을 넣지 않는다.

## 전환

이 정책 게시 전의 `CLAIM / RELEASE` comment는 역사 기록이다.
진행 중인 일반 작업은 그대로 계속하고, reservation 대상에 해당할 때만 새 `RESERVE`를 게시한다.
