# Frontend Redesign Spec

## Overview

Redesign the case-agent frontend to improve usability, aesthetics, and data visualization.
**Scope**: Home dashboard, test case generation (wizard), knowledge base, test tools, settings.
**Out of scope**: Submission management, review management, defect management, auto-test (hidden, unchanged).

## Tech Constraints

- React 19 + TypeScript (strict)
- Ant Design 5.27.1 + Pro Layout 7.22.7
- Vite 7.1.5
- Existing CSS variable design system (Apple-inspired) to be preserved and extended

---

## 1. Navigation Architecture

### Sidebar (replaces horizontal top nav)

- **Left sidebar**, collapsible to icon-only mode (40px), expand on hover
- **Global search bar** at top: fuzzy search across feature names, recent tasks, knowledge base entries (Command Palette style)
- **Flat entry list with smart sorting**: most recently used items float to top automatically
- **Three visual groups** separated by dividers:
  - Frequent (用例生成, 快速生成)
  - Assets & Tools (知识库, 测试工具)
  - Bottom-pinned (设置)
- **Hidden modules**: 提测申请, 用例评审, 缺陷管理, 自动化测试 are removed from nav (routes preserved but not shown)

### Top Status Bar (all pages)

- Fixed, always visible, does not scroll
- Shows key metrics: weekly generation count (with trend %), review pass rate, pending defect count
- Clicking a metric navigates to the corresponding module
- Data from backend stats endpoint

---

## 2. Home Dashboard

### Layout

- Greeting row: time-based greeting + last active timestamp
- Draggable card grid (3 cols large, 2 cols medium, 1 col small)

### Cards

1. **Quick Actions**: 3-4 large icon buttons for high-frequency operations (generate test cases, create submission, upload knowledge doc)
2. **My Tasks**: recent generation tasks with status and progress bars, clickable to navigate
3. **Quality Overview**: end-to-end quality flow (Requirement → Cases → Review → Submission → Defects) as a horizontal mini-flow diagram showing counts and conversion rates at each stage
4. **Todo Items**: aggregated pending items across modules (defects to confirm, submissions to review, cases to supplement)
5. **Recent Activity**: timeline of recent operations

### State
- Empty state for first-time users: guided setup flow
- Loading state: skeleton cards

---

## 3. Test Case Generation (Wizard)

Unifies the current 用例生成 and 快速生成 into a single 3-step wizard.

### Step 1 — Input Requirement

- Large textarea for requirement description, character counter (min 50 recommended)
- Generation mode selector: 完整模式 / 快速模式 / 自定义 (radio cards with descriptions)
- Collapsible advanced options: model picker, test type multi-select, case count slider

### Step 2 — Upload Materials

- Drag-and-drop upload zone for reference docs (PDF/Word/Markdown/Txt)
- Screenshot upload with thumbnail preview grid (click to enlarge)
- Knowledge base search and multi-select association
- All fields optional

### Step 3 — Confirm & Generate

- Generation summary card: mode, test types, estimated case count, file count, requirement excerpt
- Readiness checklist with green check / yellow warning icons
- Optional items marked with warning but don't block generation
- "Start Generate" CTA button

### Generation Progress

- Inline progress (no page navigation)
- Step-based progress indicator: Parse docs → Extract test points → Generate functional cases → Generate boundary cases → Generate exception cases → Generate performance cases
- AI thought process panel showing current reasoning
- Auto-transition to results view on completion

### Result View

- Result hero: total count, time elapsed, success indicator
- Overview cards: case type distribution (colored bar cards), priority pie chart, coverage gauge
- Filter toolbar: search, priority filter, type filter, status filter + export buttons
- Case table with inline edit capability (click to edit row directly)
- Pagination

### Mode Differences

- **完整模式**: full 3-step wizard
- **快速模式**: merged Step 2+3, fewer options visible

---

## 4. Knowledge Base

### List Page

- Card grid layout (with list/grid toggle)
- Each card: file type icon, title, module tags, file size, relative time, view/delete actions
- Stats bar: total docs, weekly new, total size
- Filter bar: search, module filter, type filter
- Drag-to-upload support on the page

### Detail Page

- Document header: title, module, type, size, timestamps, action buttons (download, edit info, delete)
- Document preview: inline PDF/Word preview, rendered Markdown/text
- Related generations section: list of generation tasks that used this document, with case counts and links

---

## 5. Test Tools

### Layout

- Tab-based tool switching (no route navigation, preserves tool state)
- Each tool wrapped in a unified card container

### Current Tools

- **Timestamp Converter**: left-right dual column layout (timestamp→date, date→timestamp), copy buttons
- **JSON Formatter**: textarea input → formatted output with syntax highlighting, validation feedback, copy button

### Extensibility

- "+ More Tools" tab placeholder for future tools
- New tools follow the same card wrapper pattern

---

## 6. Settings

### Layout

- Tab navigation: 模型配置, 通用设置 (placeholder)

### Model Configuration

- Card-based model list (one card per model)
- Active model highlighted with blue left border
- Inline edit: expand form within card, no modal
- Test connection: inline loading state and result display
- Add model button at bottom of each category (LLM, Vision, Evaluation)
- Categories: LLM Models, Vision Models, Evaluation Models — all same card structure

---

## 7. Shared Component Patterns

### List Pages (通用模式)
- Page header with title + action buttons
- Data overview bar (total, status breakdown)
- Filter toolbar (search, status, date range, priority)
- Data table or card grid
- Pagination

### Charts & Visualization
| Scenario | Chart Type |
|----------|-----------|
| Case type distribution | Donut/rose chart |
| Priority distribution | Bar chart |
| Review trend | Line chart (7/30 day) |
| Defect distribution | Heatmap (module × severity) |
| Generation efficiency | Sparkline + trend arrow |

### Quality Flow Diagram (reusable)
- Horizontal flow: Requirement → Cases → Review → Submission → Defects
- Each node shows count and conversion rate
- Color gradient from blue (construction) to red (issue discovery)
- Clickable nodes navigate to respective modules

---

## 8. State Handling

| State | Pattern |
|-------|---------|
| Loading | Skeleton cards/tables, shimmer animation |
| Empty | Centered illustration + description + CTA |
| Error | Inline Alert with retry button |
| Not found | 404 page with back-to-home link |

## 9. Responsive Breakpoints

- ≥1200px: sidebar expanded, 3-col dashboard, full table
- 768-1199px: sidebar collapsed, 2-col dashboard, condensed table
- <768px: sidebar overlay/drawer, 1-col, stacked filters
