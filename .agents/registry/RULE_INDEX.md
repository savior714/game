---
scope: registry
domain: core
---
<!-- Language: ko -->

# 🗂️ Agent Rule Index

이 문서는 프로젝트의 모든 에이전트 지침 및 규칙 파일의 중앙 색인입니다.

## ⚖️ Constitution (Root)
| 파일 | 설명 | 비고 |
| :--- | :--- | :--- |
| [AGENTS.md](../../AGENTS.md) | 우선순위, 전역 게이트, 레지스트리 진입점 | 헌법(요약) |
| [PROJECT_RULES.md](../../PROJECT_RULES.md) | 아키텍처 정책, 기술 스택, 품질 게이트, **§4.1 시크릿 ZERO-LEAK** | 정책 허브 |

## 🗺️ Registry & Metadata
| 파일 | 설명 | 비고 |
| :--- | :--- | :--- |
| [.agents/registry/LOAD_ORDER.md](LOAD_ORDER.md) | 규칙 파일 로딩 순서 및 Phase 정의 | 로딩 SSOT |
| [.agents/registry/CONTEXT_ROUTING.md](CONTEXT_ROUTING.md) | 경로/조건별 동적 규칙 라우팅 맵 | 라우팅 SSOT |
| [.agents/registry/WORKFLOW_AND_SKILL_INDEX.md](WORKFLOW_AND_SKILL_INDEX.md) | 슬래시 워크플로 · 프로세스 스킬 · FE 스킬 표 | 워크플로/스킬 표 SSOT |
| [.agents/registry/RULE_INDEX.md](RULE_INDEX.md) | 모든 규칙 파일의 중앙 색인 (본 문서) | 인덱스 |

## 🏗️ Core Instruction (Common)
| 파일 | 설명 | 핵심 키워드 |
| :--- | :--- | :--- |
| [.agents/core/runtime_edit_tools.md](../core/runtime_edit_tools.md) | Tri-runtime 편집 스키마·공통 패치 전제·에러 디코더·한글 우회·MCP `repo_*` 전환기 | Cursor, OpenCode, Antigravity, repo_patch |
| [.agents/core/opencode_tools.md](../core/opencode_tools.md) | OpenCode/local LLM 도구 목록·`edit` 스키마 | oldString, filePath, bash |
| [.agents/core/execution.md](../core/execution.md) | 사고 방식, 변경 원칙, 실행 흐름, 파일 접근, **§2.9 시크릿**, **§2.10 정직성** | Simplicity, Surgical, Disk First, tri-runtime edit, ZERO-LEAK |
| [.agents/core/verification.md](../core/verification.md) | Verification Matrix, Patch Integrity, Safe Edit Loop | Gate, Verify, Lint, Type |
| [.agents/core/planning.md](../core/planning.md) | Thinking Levels, Plan Gate, Blueprint Contract | /plan, DoD, Conclusion |
| [.agents/core/code_quality_lifecycle.md](../core/code_quality_lifecycle.md) | 설계·구현·리뷰·강제·테스트 시점별 품질 게이트 | D/I/R/E/T, Mock 구분, fan-in/out |
| [.agents/core/reporting.md](../core/reporting.md) | Reporting Protocol · **§1.0 세션 종료** (lint/type → spec-sync) | Concise, Turn-End, /023 |
| [.agents/core/resilience.md](../core/resilience.md) | Retry & Resilience 전략 | Retry, Timeout, Recovery |
| [.agents/core/memory_hygiene.md](../core/memory_hygiene.md) | MEMORY.md 위생 점검 및 아카이브 정책 | 200 lines, Hygiene |

## 🌐 Domain Specific Rules
| 분류 | 파일 | 설명 |
| :--- | :---: | :--- |
| **Frontend** | [.agents/domains/frontend/react.md](../domains/frontend/react.md) | PascalCase, 컴포넌트 분할, Tailwind |
| | [.agents/domains/frontend/typescript.md](../domains/frontend/typescript.md) | Strict Mode, Type Narrowing, No Any |
| **Backend** | [.agents/domains/backend/ddd.md](../domains/backend/ddd.md) | DDD 의존 방향, Bounded Context, DI |
| | [.agents/domains/backend/api_contracts.md](../domains/backend/api_contracts.md) | API 모델링, Contract-First |
| **Medical** | [.agents/domains/medical/fhir.md](../domains/medical/fhir.md) | FHIR R4 Only, KR Core 정합성 |
| | [.agents/domains/medical/emr_security.md](../domains/medical/emr_security.md) | Vault, Master Key, Audit Log |
| **Infra** | [.agents/domains/infra/docker.md](../domains/infra/docker.md) | Docker Compose dev infra, 표준 포트, 런타임 정책 |
| **Testing** | [.agents/domains/testing/tdd.md](../domains/testing/tdd.md) | Red-First, 검증 게이트, assertion 필수 |
| | [.agents/domains/testing/playwright.md](../domains/testing/playwright.md) | Playwright E2E 시나리오 및 Discovery |
| **Docs** | [.agents/domains/documentation/markdown.md](../domains/documentation/markdown.md) | 한국어 우선, Language Gate, SSOT 보존 |
| | [.agents/domains/documentation/planning_docs.md](../domains/documentation/planning_docs.md) | Unified Deep Planning 상세 프로토콜 |
| **Tech Stack** | [.agents/domains/tech-stack/zustand.md](../domains/tech-stack/zustand.md) | zustand 라이브러리 사용 지침 |

## 🧠 Adaptive & Insight
| 파일 | 설명 | 비고 |
| :--- | :--- | :--- |
| [.agents/adaptive/self_evolution.md](../adaptive/self_evolution.md) | 자기 진화 프로토콜 (개선 제안 및 반영) | Evolution |
| [.agents/adaptive/cognitive_logging.md](../adaptive/cognitive_logging.md) | Sparse-Gold 인지 로깅 정책 | /ai-log |

---
**Last Updated**: 2026-06-08
