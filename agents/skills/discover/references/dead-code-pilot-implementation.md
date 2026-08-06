# dead-code-pilot 구현 패턴

Discover Loop에 `delete_dead_code` 시나리오를 추가할 때의 구조적 패턴.

## 아키텍처

```
ruff + vulture (정적 분석)
    ↓
dead_code_report.py → DeadCodeFinding[]
    ↓
dead_code_scope.py → is_dead_code_pilot_path() (tests/·scripts/만 허용)
    ↓
discover_dead_seed.py → DiscoverCandidate(template="delete_dead_code")
    ↓
artifacts/discover/dead_code_pilot.json (큐)
    ↓
discover_validate.py → delete_dead_code && 허용 분기
verify_contract.py → normalize_verify_hint() "just discover-dead-verify" 변환
    ↓
emit_implement_blueprint.py → delete_dead_code Goal 분기
    ↓
docs/plans/PLAN_discover_implement_dead_code_queue.md (Implement Blueprint)
```

## 핵심 패턴

### 1. verify_hint && 우회

`delete_dead_code`는 ruff+vulture 두 명령을 `&&`로 연결한 verify_hint를 사용한다.
`validate_candidate()`에서 일반 템플릿은 `&&`를 금지하지만, `delete_dead_code`는
`normalize_verify_hint()`가 이를 `just discover-dead-verify <path>` 단일 러너로
변환하므로 허용한다.

```python
# discover_validate.py
if candidate.template != "delete_dead_code":
    if "&&" in verify_hint or ";" in verify_hint:
        raise ValueError("verify_hint cannot contain multiple commands")
```

```python
# verify_contract.py
if template == "delete_dead_code":
    return f"just discover-dead-verify {evidence_path}"
```

### 2. 스코프 화이트리스트

프로덕션 코드(src/, apps/)가 vulture 오탐으로 유입되는 것을 방지한다.

```python
# dead_code_scope.py
def is_dead_code_pilot_path(path: str) -> bool:
    norm = path.replace("\\", "/")
    return norm.startswith("tests/") or norm.startswith("scripts/")
```

### 3. ruff/vulture 파서 포맷

**ruff**:
```
F401 [*] `os` imported but unused
 --> scripts/foo.py:3:8
```

**vulture**:
```
scripts/foo.py:3: unused import 'os' (90% confidence)
```

### 4. emit Goal 분기

`emit_implement_blueprint.py`에서 template 기반 Goal 생성:

```python
if template == "delete_dead_code":
    dead_symbol = item.get("dead_symbol", "")
    if dead_symbol:
        goal = f"delete_dead_code — {evidence_path} 에서 {dead_symbol} 심볼을 제거한다."
    else:
        goal = f"delete_dead_code — {evidence_path} 에서 unused 심볼을 제거한다."
```

## 관련 파일

- `scripts/discover_loop/dead_code_report.py` — ruff/vulture 파서
- `scripts/discover_loop/dead_code_scope.py` — 경로 스코프
- `scripts/discover_loop/discover_dead_seed.py` — CLI 시드러너
- `scripts/discover_loop/dead_verify.py` — 검증 래퍼
- `Justfile` — `discover-dead-seed`, `discover-dead-verify` 레시피
