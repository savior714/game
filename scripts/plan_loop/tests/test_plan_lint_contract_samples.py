from scripts.plan_loop.plan_lint import lint_plan_text
from scripts.plan_loop.tests.plan_lint_rules_compat import _minimal_blueprint_body

def test_missing_mandatory_sections():
    # DoD 섹션이 누락된 계획서
    content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: None
- Project Status Link: None
- Architectural Goal: None

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

#### Task 1.1: Fix it [Level: Low]
- Task-ID: [T1] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: fix
- Diagnostics: none
- Verify: test
- Conclusion: done
- Dependency: none
"""
    issues, _warnings = lint_plan_text(content)
    # 현재 린터는 DoD, Meta, Risk, Impact 등을 필수로 체크하지 않거나 순서를 체크하지 않음
    # "Definition of Done (DoD)" 섹션 누락을 잡아내지 못할 것으로 예상
    assert any("Definition of Done" in issue for issue in issues), "Should detect missing DoD section"

def test_incorrect_section_order():
    # 순서가 뒤바뀐 섹션 (Sketch가 Diagnosis보다 먼저 옴)
    content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: None
- Project Status Link: None
- Architectural Goal: None

## 📜 Conceptual Sketch
Sketch...

## 🔍 Diagnosis & Findings
Symptoms...

#### Task 1.1: Fix it [Level: Low]
- Task-ID: [T1] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: fix
- Diagnostics: none
- Verify: test
- Conclusion: done
- Dependency: none

## ✅ Definition of Done (DoD)
1. Done.
"""
    issues, _warnings = lint_plan_text(content)
    # 현재 린터는 순서를 체크하지 않음
    assert any("order" in issue.lower() for issue in issues), "Should detect incorrect section order"

def test_placeholder_in_task_fields():
    content = _minimal_blueprint_body(with_contract=False, with_scope=False)
    content = (
        content.replace("**Goal**: fix", "**Goal**: [목표 이름]")
        .replace(
            "**Verify**: `just lint`",
            "**Verify**: [물리적 증거 확보 명령어 (just lint/ty/test 등)]",
        )
        .replace(
            "**Conclusion**: [판정 — 비개발자용 요약. 검증 결과]",
            "**Conclusion**: [완료 시 기입]",
        )
    )
    issues, _warnings = lint_plan_text(content)
    assert any("placeholder" in issue.lower() for issue in issues), (
        "Should detect placeholders in task fields"
    )

def test_generic_uppercase_placeholder():
    # [TBD] 와 같은 일반적인 대문자 플레이스홀더
    content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: [TBD]
- Project Status Link: None
- Architectural Goal: None

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

#### Task 1.1: Fix it [Level: Low]
- Task-ID: [T1] | Status: todo | RetryPolicy: none
- Action: Edit
- Target: file.py
- Goal: fix
- Diagnostics: none
- Verify: test
- Conclusion: done
- Dependency: none

## ✅ Definition of Done (DoD)
1. Done.
"""
    issues, _warnings = lint_plan_text(content)
    # [TBD]는 현재 _is_placeholder_value에서 re.fullmatch(r"\[[A-Z_\s-]+\]", normalized)에 의해 잡힐 것임
    # 하지만 doc_meta 체크 로직이 이를 제대로 호출하는지 확인 필요
    assert any("placeholder" in issue.lower() or "missing/empty" in issue.lower() for issue in issues)


def test_conclusion_csf_hint_allowed_when_todo():
    content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Fix [Level: Low]
- Task-ID: [T1] | Status: todo | RetryPolicy: none
- **Action**: Edit | **Target**: a.py
- **Goal**: fix lint
- **Diagnostics**: none
- **Verify**: just lint
- **Conclusion**: [해결 건수/잔여 건수 요약]
- **Dependency**: None

## 🔁 Conclusion & Summary
- **Roll-up**: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
    issues, _warnings = lint_plan_text(content)
    assert not any("Conclusion" in i and "placeholder" in i.lower() for i in issues)


def test_conclusion_placeholder_rejected_when_done():
    content = _minimal_blueprint_body(with_contract=False, with_scope=False)
    content = content.replace("Status: todo", "Status: done").replace(
        "**Conclusion**: [판정 — 비개발자용 요약. 검증 결과]",
        "**Conclusion**: [해결 건수/잔여 건수 요약]",
    )
    issues, _warnings = lint_plan_text(content)
    assert any(
        "Conclusion" in i and ("csf hint" in i.lower() or "placeholder" in i.lower())
        for i in issues
    )


def test_premature_measured_conclusion_rejected_when_todo():
    content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Fix [Unit: Atomic]
- Task-ID: [T1] | Status: todo | RetryPolicy: none
- **MCP**: desktop-commander
- **Pre-read**: paths <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[rule]` `.agents/core/execution.md`
- **Action**: Edit | **Target**: a.py
- **Goal**: fix lint
- **Diagnostics**: none
- **Verify**: just lint
- **Conclusion**: [통과 — 구현 완료. 테스트 11건 전원 Green.]
- **Dependency**: None

## 🔁 Conclusion & Summary
- **Roll-up**: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
    issues, _warnings = lint_plan_text(content)
    assert any("post-Verify measured text" in i for i in issues)


def test_csf_slot_conclusion_allowed_when_todo():
    content = """
# 🗺️ Project Blueprint: Test
## 문서 메타
- SSOT Check: ok
- Project Status Link: ok
- Architectural Goal: ok

## 🔍 Diagnosis & Findings
Symptoms...

## 🏗️ Architectural Deepening
Deepening...

## 📜 Conceptual Sketch
Sketch...

## 🛡️ Risk & Strategy
- **Risk**: x | **Strategy**: y

## 🔍 Impact Scope
| f | 1 | r | n |

## 🛠️ Step-by-Step Execution Plan
#### Task 1.1: Fix [Unit: Atomic]
- Task-ID: [T1] | Status: todo | RetryPolicy: none
- **MCP**: desktop-commander
- **Pre-read**: paths <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[rule]` `.agents/core/execution.md`
- **Action**: Edit | **Target**: a.py
- **Goal**: fix lint
- **Diagnostics**: none
- **Verify**: just lint
- **Conclusion**: [판정 — 비개발자용 요약. 검증 결과]
- **Dependency**: None

## 🔁 Conclusion & Summary
- **Roll-up**: ok

## ✅ Definition of Done (DoD)
1. Done.
"""
    issues, _warnings = lint_plan_text(content)
    assert not any("post-Verify measured text" in i for i in issues)
    assert not any("Conclusion must be a CSF slot" in i for i in issues)
