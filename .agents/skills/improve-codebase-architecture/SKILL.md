---
name: improve-codebase-architecture
description: >
  Surface architectural friction; propose deepening opportunities (shallow → deep
  modules) for testability and AI-navigability. Glossary-driven (Module, Interface,
  Depth, Seam, Locality, Leverage).
license: MIT
metadata:
  version: "1.0.0"
---

<!-- Language: ko -->

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Definitions are the bullet list below (treat it as the glossary).

- **Module**: Anything with an interface and an implementation (function, class, package, slice).
- **Interface**: Everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation**: The code inside.
- **Depth**: Leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam**: Where an interface lives; a place behaviour can be altered without editing in place.
- **Adapter**: A concrete thing satisfying an interface at a seam.
- **Leverage**: What callers get from depth.
- **Locality**: What maintainers get from depth: change, bugs, knowledge concentrated in one place.

### Key Principles

- **Deletion test**: Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

## Cross-Cutting Concern → Single Entry Point

횡단 관심사(에러 바운더리, 로깅, 권한 가드, suspense)를 "각 leaf 파일" Task로 쪼개기 **전에**:

1. 실제 mount/import **진입점 1~N개**를 `rg`/import graph로 식별한다.
2. 진입점에서 일괄 적용 가능하면 **그곳만** 수정한다 (Surgical + Deep Module).
3. Blueprint Task 수·회귀면적·Verify 범위를 진입점 기준으로 재작성한다.

**Anti-pattern**: Blueprint Target만 늘리고 import graph 미확인 → phantom path·60+ 중복 패치. SSOT: [planning.md](../../core/planning.md) §0 Target Path SSOT Gate · §2.6.

## Process

### 1. Explore

Read the project's domain glossary and any ADRs in the area you're touching first.
Explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow.

### 2. Present Candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files**: Which files/modules are involved.
- **Problem**: Why the current architecture is causing friction.
- **Solution**: Plain English description of what would change.
- **Benefits**: Explained in terms of locality and leverage, and also in how tests would improve.

**Use domain vocabulary** from the project's README or spec tree.
Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

### 3. Grilling Loop

Once the user picks a candidate, drop into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects:

- **Naming**: If naming a deepened module after a new concept, document it.
- **ADR**: If the user rejects for a load-bearing reason, offer to record it as an ADR.
- **Want to explore alternative interfaces for the deepened module?** See [Interface Design](#-interface-design).

---

## Interface Design

When exploring alternative interfaces for a chosen deepening candidate, use this pattern:

### 1. Frame the problem space

- The constraints any new interface would need to satisfy.
- The dependencies it would rely on.
- A rough illustrative code sketch to ground the constraints.

### 2. Design Twice (or Thrice)

Propose radically different interfaces for the deepened module:

- **Option A (Minimal)**: 1–3 entry points max. Maximise leverage per entry point.
- **Option B (Flexible)**: Support many use cases and extension.
- **Option C (Common Case)**: Optimise for the most common caller.
- **Option D (Ports & Adapters)**: Design around ports & adapters for cross-seam dependencies.

For each option, provide:

1. Interface (types, methods, params — plus invariants, ordering, error modes)
2. Usage example showing how callers use it
3. What the implementation hides behind the seam
4. Trade-offs

### 3. Present and Compare

Contrast by **depth** (leverage at the interface), **locality** (where change concentrates), and **seam placement**.
Be opinionated — provide a strong recommendation on which design is strongest and why.
