---
version: 1.0.0
last_updated: {{DATE}}
author: Antigravity (Architect)
status: Template
tokens:
  colors:
    brand:
      primary: "{{BRAND_PRIMARY_COLOR}}"    # e.g., "#2563EB"
      secondary: "{{BRAND_SECONDARY_COLOR}}"  # e.g., "#64748B"
      accent: "{{BRAND_ACCENT_COLOR}}"
    semantic:
      success: "#059669"
      warning: "#D97706"
      error: "#DC2626"
      info: "{{BRAND_PRIMARY_COLOR}}"
    neutral:
      background: "#F3F4F6"
      surface: "#FFFFFF"
      text_primary: "#111827"
      text_secondary: "#6B7280"
      border: "#E5E7EB"
  typography:
    font_family:
      sans: "'Inter Variable', 'Inter', 'Pretendard', system-ui, sans-serif"
      mono: "'JetBrains Mono', monospace"
    weights:
      normal: 400
      medium: 500
      semibold: 600
      bold: 700
    scale:
      xs: "0.75rem"
      sm: "0.875rem"
      base: "1rem"
      lg: "1.125rem"
      xl: "1.25rem"
      "2xl": "1.5rem"
  spacing:
    base: 4
    scale: [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96]
  radii:
    none: "0"
    sm: "0.4rem"
    md: "0.5rem"
    lg: "0.75rem"
    full: "9999px"
---

# Design Specification: {{PROJECT_NAME}} (Standard v1.0)

이 문서는 프로젝트의 시각적 일관성과 사용자 경험을 정의하는 Design SSOT입니다. 모든 UI 개발은 본 명세의 토큰과 패턴을 최우선으로 따릅니다.

## 1. Visual Language

### 1.1 디자인 원칙
- **Consistent Tokens**: 모든 색상과 간격은 하드코딩하지 않고 정의된 토큰을 사용합니다.
- **Hierarchical Depth**: 카드 시스템과 그림자를 활용하여 정보의 위계를 구분합니다.
- **Semantic Feedback**: 상태에 맞는 시맨틱 컬러를 사용하여 사용자에게 명확한 피드백을 제공합니다.

---

## 2. Layout Patterns

### 2.1 Standard Grid
- **Responsive Layout**: {{LAYOUT_TYPE}} 기반의 유연한 그리드 시스템을 사용합니다.
- **Consistent Spacing**: 섹션 간 간격과 패딩은 `spacing.scale`을 준수합니다.

---

## 3. Design Lab

실시간 토큰 실험 및 목업 확인을 위한 공간입니다.

- [**Design Lab**](../../../frontend/app/design-lab/page.tsx): 정의된 토큰이 실제 UI에 어떻게 반영되는지 확인할 수 있습니다.

---
**Last Verified**: {{DATE}} by Antigravity
