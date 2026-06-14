---
ssot_check: AGENTS.md §2.3, scripts/agent/orchestration/
project_status_link: .agents/workflows/plan.md
architectural_goal: Structured 5-phase multi-agent orchestration with typed contracts
---

# SPEC_orchestration.md — Multi-Agent Orchestration Pipeline

## Scope

Define executable data contracts and phase logic for the 5-phase multi-agent
orchestration pattern described in `AGENTS.md` §2.3.

Each phase is a **standalone module** with clear input/output types.
Agents implement phases by calling the module functions and passing results
to the next phase.

## Architecture

```
WorkSpec ──→ [Analyzer] ──→ list[TaskSpec] ──→ [Dispatcher] ──→ list[DiffResult]
                                                                                ↓
OrchestrationResult ← [FinalAuditor] ←─ list[DiffResult] ──→ [Auditor] ←─ list[AuditReport]
                ↑                       ↑                        ↑
                └── list[AuditReport] ←─┘                        │
                ┌────────────────────────────────────────────────┘
                │
list[DiffResult] ← [Fixer] ←── list[AuditReport] (with HIGH findings)
```

## Component Contracts

### 1. Analyzer (`scripts/agent/orchestration/analyzer.py`)

**Purpose**: Decompose WorkSpec into independent TaskSpecs.

| Direction | Type | Description |
|-----------|------|-------------|
| INPUT | `WorkSpec` | Full scope: description, file_groups, success_criteria |
| OUTPUT | `list[TaskSpec]` | One TaskSpec per FileGroup |

**Rules**:
- Each `FileGroup` → exactly one `TaskSpec`
- Task IDs: sequential (`T1`, `T2`, ...)
- Dependencies: empty by default (all groups independent)
- Scope: domain-isolated (each TaskSpec mentions only its own domain)
- Validation: unique task IDs, no circular dependencies

**Function signature**:
```python
def analyze(work_spec: WorkSpec) -> list[TaskSpec]: ...
def estimate_parallelism(task_specs: list[TaskSpec]) -> int: ...
```

---

### 2. Dispatcher (`scripts/agent/orchestration/dispatcher.py`)

**Purpose**: Build dispatch instructions and parse subagent results.

| Direction | Type | Description |
|-----------|------|-------------|
| INPUT | `list[TaskSpec]` | From Analyzer |
| OUTPUT | `list[DiffResult]` | One per TaskSpec |

**Rules**:
- Each TaskSpec → one `task` tool call with `subagent_type="general"`
- Prompt includes: target paths, goal, scope boundary, AGENTS.md rules
- Results parsed from subagent text output (git diff summary)
- Validation: every TaskSpec has a corresponding DiffResult

**Function signatures**:
```python
def build_dispatch_instructions(task_specs: list[TaskSpec]) -> list[dict]: ...
def parse_results(raw_outputs: list[dict]) -> list[DiffResult]: ...
def validate_dispatch_results(task_specs, diff_results) -> list[str]: ...
```

---

### 3. Auditor (`scripts/agent/orchestration/auditor.py`)

**Purpose**: Audit each DiffResult against the checklist.

| Direction | Type | Description |
|-----------|------|-------------|
| INPUT | `list[DiffResult]` | From Dispatcher |
| OUTPUT | `list[AuditReport]` | One per DiffResult (1:1) |

**Checklist** (from AGENTS.md §2.3 Phase 3):
1. **Korean/encoding** (`KOREAN_ENCODING`): edit tool failure on Korean content
2. **Message uniqueness** (`QUERY_SELECTOR_UNIQUENESS`): duplicate text breaking querySelector
3. **Context Route Gate** (`CONTEXT_ROUTE_GATE`): `just route` procedure compliance
4. **Partial Edit rules** (`PARTIAL_EDIT_RULES`): oldString ≠ newString, single match

**Function signatures**:
```python
def audit(diff_results: list[DiffResult]) -> list[AuditReport]: ...
def has_blocking_issues(reports: list[AuditReport]) -> bool: ...
def summary(reports: list[AuditReport]) -> str: ...
```

---

### 4. Fixer (`scripts/agent/orchestration/fixer.py`)

**Purpose**: Group audit findings by file and produce fix instructions.

| Direction | Type | Description |
|-----------|------|-------------|
| INPUT | `list[AuditReport]` | From Auditor |
| OUTPUT | `list[DiffResult]` | Updated results after fixes |

**Rules**:
- Multiple findings in same file → one subagent handles all
- Retry only once (max_fix_retries=1)
- Only fix HIGH/MEDIUM findings (LOW noted but not auto-fixed)

**Function signatures**:
```python
def build_fix_requests(reports: list[AuditReport]) -> list[dict]: ...
def apply_fixes(fix_instructions, raw_outputs) -> list[DiffResult]: ...
def should_retry(reports: list[AuditReport]) -> bool: ...
```

---

### 5. FinalAuditor (`scripts/agent/orchestration/final_auditor.py`)

**Purpose**: Produce the final OrchestrationResult.

| Direction | Type | Description |
|-----------|------|-------------|
| INPUT | `list[DiffResult]`, `list[AuditReport]` | From previous phases |
| OUTPUT | `OrchestrationResult` | Final status and summary |

**Rules**:
- FAILED/BLOCKED tasks → `OrchestrationStatus.FAILED`
- HIGH findings remaining → `OrchestrationStatus.IN_PROGRESS`
- All clear → `OrchestrationStatus.COMPLETED`

**Function signatures**:
```python
def final_audit(task_results, audit_reports, success_criteria) -> OrchestrationResult: ...
def is_orchestration_successful(result) -> bool: ...
```

---

### 6. PipelineOrchestrator (`scripts/agent/orchestration/__init__.py`)

**Purpose**: Coordinate the 5-phase pipeline.

**Function signature**:
```python
class PipelineOrchestrator:
    def __init__(self, max_fix_retries: int = 1): ...
    def run(self, work_spec, dispatch_fn=None, fix_dispatch_fn=None) -> OrchestrationResult: ...
    def get_log(self) -> list[str]: ...
```

**Usage**:
```python
from scripts.agent.orchestration import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
result = orchestrator.run(
    work_spec=WorkSpec(...),
    dispatch_fn=lambda instructions: [...],  # agent runtime: task() calls
    fix_dispatch_fn=lambda instructions: [...],  # agent runtime: task() calls
)
```

---

## Data Contracts (spec.py)

All data types live in `scripts/agent/orchestration/spec.py`:

| Type | Purpose |
|------|---------|
| `WorkSpec` | Phase 1 input — full scope |
| `FileGroup` | Independent file group (domain directory) |
| `TaskSpec` | Phase 1 output / Phase 2 input — single subagent task |
| `DiffResult` | Phase 2 output / Phase 3 input — subagent execution result |
| `AuditReport` | Phase 3 output / Phase 4 input — audit findings for one task |
| `AuditFinding` | Single issue with category, severity, evidence, suggested fix |
| `FixRequest` | Phase 4 instruction — what to fix and how |
| `OrchestrationResult` | Phase 5 output — final pipeline result |

**Enums**:
- `TaskStatus`: TODO, RUNNING, DONE, FAILED, BLOCKED
- `AuditSeverity`: HIGH, MEDIUM, LOW
- `AuditCategory`: KOREAN_ENCODING, QUERY_SELECTOR_UNIQUENESS, CONTEXT_ROUTE_GATE, PARTIAL_EDIT_RULES, FILE_OVERLAP, MISSING_VERIFICATION, GENERAL
- `OrchestrationStatus`: PENDING, IN_PROGRESS, COMPLETED, FAILED

---

## Test Coverage

| Test file | Covers |
|-----------|--------|
| `tests/test_orchestration_spec.py` | All data classes, validation helpers, enums |
| `tests/test_orchestration_analyzer.py` | Phase 1: analyze(), estimate_parallelism() |
| `tests/test_orchestration_auditor.py` | Phase 3: all 4 checklist checkers, audit(), helpers |
| `tests/test_orchestration_pipeline.py` | Dispatcher, Fixer, FinalAuditor, PipelineOrchestrator integration |

## Agent Implementation Guide

When an agent needs to execute the orchestration pattern:

1. **Read** `scripts/agent/orchestration/spec.py` for data types
2. **Read** the phase module it needs (analyzer, dispatcher, etc.)
3. **Call** the phase function with appropriate input
4. **Pass** output to the next phase
5. The agent runtime handles actual `task()` tool calls; the modules handle
   data transformation and validation

Each module is **independent** — an agent can read just the one it needs
plus `spec.py` for types. No module depends on another except through
the typed data contracts in `spec.py`.
