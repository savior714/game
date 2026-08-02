# Atomic Task Delta Template

```text
TASK_ID:
<short stable id>

FAILURE_DOMAIN:
<one observable defect>

REPRODUCTION:
<one deterministic reproduction>

HYPOTHESIS:
<one falsifiable cause and minimum change>

WRITE_SET:
- <exact path>

FORBIDDEN_SET:
- <paths or behaviors not owned>

STEPS:
1. Read the closest implementation and test.
2. Reproduce the stated failure.
3. Apply the minimum change.
4. Run only the targeted validation.
5. Stop after the single criterion is decided.
6. Commit and push according to repository AGENTS.md.

ACCEPTANCE:
<one binary criterion>

STOP:
- write-set overlap
- hypothesis rejected
- required validator unavailable
- unrelated failure observed first

REPORT:
RESULT / hypothesis verdict / changed files / targeted validation /
blocker / commit SHA / push state
```

공통 Git·runtime·완료 보고 규칙은 이 프롬프트에 다시 붙이지 않는다.
