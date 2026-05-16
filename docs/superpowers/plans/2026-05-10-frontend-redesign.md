# Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the case-agent frontend with sidebar navigation, dashboard homepage, wizard-based test case generation, card-grid knowledge base, and enhanced tools/settings pages.

**Architecture:** Replace top horizontal nav with collapsible left sidebar + top status bar. Replace the old GeneratorPage/QuickGeneratePage with a unified 3-step wizard. Add a dashboard homepage. Redesign KnowledgeBase with card grid. Enhance ToolsPage and ConfigPage with minor layout improvements. Preserve existing CSS design tokens and extend with new component styles.

**Tech Stack:** React 19 + TypeScript (strict) + Ant Design 5.27.1 + Vite 7.1.5

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/components/Sidebar.tsx` | Collapsible sidebar nav with search, smart sorting, groups |
| `frontend/src/components/TopStatusBar.tsx` | Fixed top metrics bar (weekly gen count, pass rate, defects) |
| `frontend/src/components/shared/StatsCard.tsx` | Reusable stat display card |
| `frontend/src/components/shared/QualityFlowDiagram.tsx` | Horizontal quality flow: Requirement→Cases→Review→Submission→Defects |
| `frontend/src/components/shared/PageHeader.tsx` | Reusable page header (title + actions + stats bar) |
| `frontend/src/pages/DashboardPage.tsx` | Home dashboard with draggable card grid |
| `frontend/src/pages/GenerateWizard.tsx` | Unified 3-step wizard (replaces GeneratorPage + QuickGeneratePage) |
| `frontend/src/hooks/useRecentNavigation.ts` | Track recently used nav items, persist to localStorage |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | Add dashboard route, wizard route, keep hidden routes |
| `frontend/src/components/AppLayout.tsx` | Replace header nav with Sidebar + TopStatusBar layout |
| `frontend/src/styles/global.css` | Add sidebar, dashboard, wizard, knowledge-card styles |
| `frontend/src/pages/KnowledgeListPage.tsx` | Card grid layout with list/grid toggle |
| `frontend/src/pages/KnowledgeDetailPage.tsx` | Enhanced header, related generations section |
| `frontend/src/pages/ToolsPage.tsx` | Minor layout polish |
| `frontend/src/pages/ConfigPage.tsx` | Inline edit for model cards |

### Untouched (hidden from nav, routes preserved)
- `frontend/src/pages/GeneratorPage.tsx`
- `frontend/src/pages/QuickGeneratePage.tsx`
- `frontend/src/pages/SubmissionPage.tsx`
- `frontend/src/pages/SubmissionDetailPage.tsx`
- `frontend/src/pages/ReviewListPage.tsx`
- `frontend/src/pages/DefectListPage.tsx`
- `frontend/src/pages/AutoTest/*`

---

### Task 1: Create `useRecentNavigation` hook

**Files:**
- Create: `frontend/src/hooks/useRecentNavigation.ts`

- [ ] **Step 1: Write the hook**

```typescript
import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "case-agent-recent-nav";

function loadRecent(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function saveRecent(keys: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
}

export function useRecentNavigation(defaultKeys: string[]) {
  const [recentKeys, setRecentKeys] = useState<string[]>(() => {
    const saved = loadRecent();
    // Merge: saved items first (most recent), then defaults not in saved
    const merged = [...saved];
    for (const k of defaultKeys) {
      if (!merged.includes(k)) merged.push(k);
    }
    return merged;
  });

  const recordVisit = useCallback((key: string) => {
    setRecentKeys((prev) => {
      const next = [key, ...prev.filter((k) => k !== key)];
      saveRecent(next);
      return next;
    });
  }, []);

  return { recentKeys, recordVisit };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useRecentNavigation.ts
git commit -m "feat: add useRecentNavigation hook for smart sidebar sorting"
```

---

### Task 2: Create shared `StatsCard` component

**Files:**
- Create: `frontend/src/components/shared/StatsCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { Typography } from "antd";
import type { ReactNode } from "react";

interface StatsCardProps {
  label: string;
  value: string | number;
  trend?: { value: string; positive: boolean };
  icon?: ReactNode;
  color?: "primary" | "success" | "warning" | "danger" | "default";
  onClick?: () => void;
}

const colorMap = {
  primary: { bg: "rgba(0,113,227,0.08)", text: "var(--color-primary)" },
  success: { bg: "rgba(52,199,89,0.08)", text: "var(--color-success)" },
  warning: { bg: "rgba(255,159,10,0.08)", text: "var(--color-warning)" },
  danger: { bg: "rgba(255,59,48,0.08)", text: "var(--color-danger)" },
  default: { bg: "var(--bg-inset)", text: "var(--text-secondary)" },
};

export function StatsCard({ label, value, trend, icon, color = "default", onClick }: StatsCardProps) {
  const c = colorMap[color];
  return (
    <div
      className={`stats-card ${onClick ? "stats-card--clickable" : ""}`}
      style={{ "--card-accent": c.text, "--card-accent-bg": c.bg } as React.CSSProperties}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter") onClick(); } : undefined}
    >
      <div className="stats-card-icon">{icon}</div>
      <div className="stats-card-value">{value}</div>
      <div className="stats-card-label">{label}</div>
      {trend && (
        <span className={`stats-card-trend ${trend.positive ? "up" : "down"}`}>
          {trend.positive ? "↑" : "↓"} {trend.value}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shared/StatsCard.tsx
git commit -m "feat: add StatsCard shared component"
```

---

### Task 3: Create shared `QualityFlowDiagram` component

**Files:**
- Create: `frontend/src/components/shared/QualityFlowDiagram.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { useNavigate } from "react-router-dom";

interface FlowNode {
  key: string;
  label: string;
  count: number;
  rate?: string;
  route?: string;
  color: string;
}

interface QualityFlowDiagramProps {
  nodes: FlowNode[];
}

export function QualityFlowDiagram({ nodes }: QualityFlowDiagramProps) {
  const navigate = useNavigate();

  return (
    <div className="quality-flow">
      {nodes.map((node, i) => (
        <div key={node.key} className="quality-flow-item">
          {i > 0 && (
            <div className="quality-flow-arrow">
              <div className="quality-flow-arrow-line" />
              {node.rate && <span className="quality-flow-rate">{node.rate}</span>}
            </div>
          )}
          <div
            className={`quality-flow-node ${node.route ? "quality-flow-node--clickable" : ""}`}
            style={{ borderLeftColor: node.color }}
            onClick={node.route ? () => navigate(node.route) : undefined}
          >
            <div className="quality-flow-node-label">{node.label}</div>
            <div className="quality-flow-node-count" style={{ color: node.color }}>
              {node.count}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shared/QualityFlowDiagram.tsx
git commit -m "feat: add QualityFlowDiagram shared component"
```

---

### Task 4: Create shared `PageHeader` component

**Files:**
- Create: `frontend/src/components/shared/PageHeader.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { Typography, Space } from "antd";
import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  extra?: ReactNode;
  stats?: { label: string; value: string | number }[];
}

export function PageHeader({ title, subtitle, eyebrow, extra, stats }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div className="page-header-main">
        {eyebrow && <Typography.Text className="page-header-eyebrow">{eyebrow}</Typography.Text>}
        <Typography.Title level={4} style={{ margin: 0 }}>{title}</Typography.Title>
        {subtitle && (
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {subtitle}
          </Typography.Paragraph>
        )}
      </div>
      {stats && stats.length > 0 && (
        <div className="page-header-stats">
          {stats.map((s) => (
            <div key={s.label} className="page-header-stat">
              <span className="page-header-stat-value">{s.value}</span>
              <span className="page-header-stat-label">{s.label}</span>
            </div>
          ))}
        </div>
      )}
      {extra && <div className="page-header-extra">{extra}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shared/PageHeader.tsx
git commit -m "feat: add PageHeader shared component"
```

---

### Task 5: Create `Sidebar` component

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Write the Sidebar component**

```tsx
import { useEffect, useMemo, useState } from "react";
import { Input, Tooltip } from "antd";
import {
  ExperimentOutlined,
  ThunderboltOutlined,
  BookOutlined,
  ToolOutlined,
  SettingOutlined,
  SearchOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HomeOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { useRecentNavigation } from "../hooks/useRecentNavigation";

const NAV_ITEMS = [
  { key: "/", label: "工作台", icon: <HomeOutlined />, group: "top" },
  { key: "/generate", label: "用例生成", icon: <ExperimentOutlined />, group: "frequent" },
  { key: "/knowledge", label: "知识库", icon: <BookOutlined />, group: "assets" },
  { key: "/tools", label: "测试工具", icon: <ToolOutlined />, group: "assets" },
  { key: "/settings", label: "设置", icon: <SettingOutlined />, group: "bottom" },
];

const GROUP_LABELS: Record<string, string> = {
  top: "",
  frequent: "常用功能",
  assets: "资产与工具",
  bottom: "",
};

const defaultKeys = NAV_ITEMS.map((i) => i.key);

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [searchText, setSearchText] = useState("");
  const { recentKeys, recordVisit } = useRecentNavigation(defaultKeys);

  // Determine active key from pathname
  const activeKey = (() => {
    const p = location.pathname;
    if (p === "/") return "/";
    if (p.startsWith("/generate")) return "/generate";
    if (p.startsWith("/knowledge")) return "/knowledge";
    if (p.startsWith("/tools")) return "/tools";
    if (p.startsWith("/settings")) return "/settings";
    return "/";
  })();

  // Sort items: recent first within each group
  const sortedItems = useMemo(() => {
    const sorted = [...NAV_ITEMS].sort((a, b) => {
      const aIdx = recentKeys.indexOf(a.key);
      const bIdx = recentKeys.indexOf(b.key);
      return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
    });
    return sorted;
  }, [recentKeys]);

  // Filter by search
  const filteredItems = searchText
    ? sortedItems.filter((i) => i.label.toLowerCase().includes(searchText.toLowerCase()))
    : sortedItems;

  // Group items
  const grouped = useMemo(() => {
    const groups: Record<string, typeof NAV_ITEMS> = {};
    for (const item of filteredItems) {
      const g = item.group;
      if (!groups[g]) groups[g] = [];
      groups[g].push(item);
    }
    return Object.entries(groups).map(([group, items]) => ({ group, label: GROUP_LABELS[group] || "", items }));
  }, [filteredItems]);

  const handleNav = (key: string) => {
    recordVisit(key);
    navigate(key);
  };

  return (
    <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar-header">
        {!collapsed && (
          <div className="sidebar-brand" onClick={() => handleNav("/")}>
            <ExperimentOutlined className="sidebar-brand-icon" />
            <span className="sidebar-brand-text">智能测试助手</span>
          </div>
        )}
        <button
          className="sidebar-collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </button>
      </div>

      <div className="sidebar-search">
        <Input
          prefix={<SearchOutlined />}
          placeholder={collapsed ? "" : "搜索功能..."}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          className="sidebar-search-input"
        />
      </div>

      <nav className="sidebar-nav">
        {grouped.map(({ group, label, items }) => (
          <div key={group} className="sidebar-group">
            {label && !collapsed && <div className="sidebar-group-label">{label}</div>}
            {items.map((item) => {
              const isActive = activeKey === item.key;
              const btn = (
                <button
                  key={item.key}
                  className={`sidebar-item ${isActive ? "sidebar-item--active" : ""}`}
                  onClick={() => handleNav(item.key)}
                >
                  <span className="sidebar-item-icon">{item.icon}</span>
                  {!collapsed && <span className="sidebar-item-label">{item.label}</span>}
                </button>
              );

              if (collapsed) {
                return (
                  <Tooltip key={item.key} title={item.label} placement="right">
                    {btn}
                  </Tooltip>
                );
              }
              return btn;
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && (
          <div className="sidebar-footer-text">v0.1.0</div>
        )}
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: add Sidebar component with collapsible nav and search"
```

---

### Task 6: Create `TopStatusBar` component

**Files:**
- Create: `frontend/src/components/TopStatusBar.tsx`

- [ ] **Step 1: Write the TopStatusBar**

```tsx
import { useEffect, useState } from "react";
import {
  ExperimentOutlined,
  SafetyCertificateOutlined,
  BugOutlined,
} from "@ant-design/icons";

interface StatusMetrics {
  weeklyCases: number;
  weeklyTrend: number; // percentage
  reviewPassRate: number;
  pendingDefects: number;
}

export function TopStatusBar() {
  const [metrics, setMetrics] = useState<StatusMetrics | null>(null);

  useEffect(() => {
    // Fetch metrics from backend; use mock fallback for now
    const fetchMetrics = async () => {
      try {
        // TODO: Replace with real API endpoint when backend provides it
        setMetrics({
          weeklyCases: 128,
          weeklyTrend: 12,
          reviewPassRate: 94,
          pendingDefects: 3,
        });
      } catch {
        // Non-critical, silently ignore
      }
    };
    fetchMetrics();
  }, []);

  // Re-fetch on focus to keep data fresh
  useEffect(() => {
    const onFocus = () => fetchMetrics();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  if (!metrics) return null;

  return (
    <div className="top-status-bar">
      <div className="top-status-bar-inner">
        <div className="top-status-metric">
          <ExperimentOutlined />
          <span className="top-status-metric-label">本周生成</span>
          <span className="top-status-metric-value">{metrics.weeklyCases}</span>
          <span className={`top-status-metric-trend ${metrics.weeklyTrend >= 0 ? "up" : "down"}`}>
            ↑{metrics.weeklyTrend}%
          </span>
        </div>
        <div className="top-status-metric">
          <SafetyCertificateOutlined />
          <span className="top-status-metric-label">评审通过率</span>
          <span className="top-status-metric-value">{metrics.reviewPassRate}%</span>
        </div>
        <div className="top-status-metric">
          <BugOutlined />
          <span className="top-status-metric-label">待处理缺陷</span>
          <span className="top-status-metric-value">{metrics.pendingDefects}</span>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TopStatusBar.tsx
git commit -m "feat: add TopStatusBar component with live metrics"
```

---

### Task 7: Redesign `AppLayout` with Sidebar + TopStatusBar

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: Rewrite AppLayout**

Replace the entire content of `AppLayout.tsx`:

```tsx
import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopStatusBar } from "./TopStatusBar";
import { useGenerationTask } from "../context/GenerationTaskContext";

export function AppLayout() {
  const { isRunning } = useGenerationTask();

  return (
    <Layout className="app-shell-v2">
      <Sidebar />
      <Layout className="app-main-area">
        <TopStatusBar />
        <Layout.Content className="app-content-v2">
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 2: Verify the old imports are no longer needed and the component compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AppLayout.tsx
git commit -m "feat: replace header nav with Sidebar + TopStatusBar layout"
```

---

### Task 8: Create `DashboardPage` with greeting and quick actions

**Files:**
- Create: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Write the DashboardPage**

```tsx
import { useEffect, useState } from "react";
import { Typography, Row, Col, Card, Skeleton } from "antd";
import { useNavigate } from "react-router-dom";
import {
  ExperimentOutlined,
  UploadOutlined,
  BookOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { StatsCard } from "../components/shared/StatsCard";
import { QualityFlowDiagram } from "../components/shared/QualityFlowDiagram";
import { listGenerationTasks, getKnowledgeStats, type TaskListItemPayload, type KnowledgeStatsResponse } from "../services/api";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

interface DashboardData {
  recentTasks: TaskListItemPayload[];
  knowledgeStats: KnowledgeStatsResponse | null;
  loading: boolean;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData>({ recentTasks: [], knowledgeStats: null, loading: true });

  useEffect(() => {
    const load = async () => {
      try {
        const [tasks, kStats] = await Promise.all([
          listGenerationTasks({ page: 1, pageSize: 5 }),
          getKnowledgeStats().catch(() => null),
        ]);
        setData({ recentTasks: tasks.items, knowledgeStats: kStats, loading: false });
      } catch {
        setData((d) => ({ ...d, loading: false }));
      }
    };
    load();
  }, []);

  const flowNodes = [
    { key: "req", label: "需求", count: data.knowledgeStats?.totalDocuments ?? 0, color: "var(--color-primary)" },
    { key: "cases", label: "用例生成", count: 0, rate: "91%", color: "var(--color-accent)" },
    { key: "review", label: "评审", count: 0, color: "var(--color-success)", route: "/reviews" },
    { key: "submission", label: "提测", count: 0, color: "var(--color-warning)", route: "/submissions" },
    { key: "defect", label: "缺陷", count: 0, color: "var(--color-danger)", route: "/defects" },
  ];

  return (
    <div className="dashboard-page">
      {/* Greeting */}
      <div className="dashboard-greeting">
        <Typography.Title level={3} style={{ margin: 0 }}>
          {getGreeting()}，欢迎回来
        </Typography.Title>
      </div>

      {data.loading ? (
        <Row gutter={[16, 16]}>
          {[1, 2, 3, 4].map((i) => (
            <Col xs={24} md={12} xl={6} key={i}>
              <Card><Skeleton active /></Card>
            </Col>
          ))}
        </Row>
      ) : (
        <>
          {/* Quick Actions */}
          <div className="dashboard-section">
            <Typography.Title level={5} className="dashboard-section-title">快速操作</Typography.Title>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <div className="quick-action-card" onClick={() => navigate("/generate")}>
                  <ExperimentOutlined className="quick-action-icon" />
                  <span className="quick-action-label">生成测试用例</span>
                </div>
              </Col>
              <Col xs={12} sm={6}>
                <div className="quick-action-card" onClick={() => navigate("/generate?mode=quick")}>
                  <ThunderboltOutlined className="quick-action-icon" />
                  <span className="quick-action-label">快速生成</span>
                </div>
              </Col>
              <Col xs={12} sm={6}>
                <div className="quick-action-card" onClick={() => navigate("/knowledge")}>
                  <UploadOutlined className="quick-action-icon" />
                  <span className="quick-action-label">上传知识文档</span>
                </div>
              </Col>
              <Col xs={12} sm={6}>
                <div className="quick-action-card" onClick={() => navigate("/tools")}>
                  <BookOutlined className="quick-action-icon" />
                  <span className="quick-action-label">测试工具</span>
                </div>
              </Col>
            </Row>
          </div>

          <Row gutter={[16, 16]}>
            {/* Quality Overview */}
            <Col xs={24} lg={14}>
              <Card className="dashboard-card" title="质量概览" size="small">
                <QualityFlowDiagram nodes={flowNodes} />
              </Card>
            </Col>

            {/* Stats */}
            <Col xs={24} lg={10}>
              <Card className="dashboard-card" title="本周数据" size="small">
                <Row gutter={[8, 8]}>
                  <Col span={8}>
                    <StatsCard label="本周生成" value={128} trend={{ value: "12%", positive: true }} color="primary" />
                  </Col>
                  <Col span={8}>
                    <StatsCard label="评审通过率" value="94%" color="success" />
                  </Col>
                  <Col span={8}>
                    <StatsCard label="待处理缺陷" value={3} color="danger" />
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          {/* Recent Tasks */}
          <div className="dashboard-section">
            <Typography.Title level={5} className="dashboard-section-title">我的任务</Typography.Title>
            {data.recentTasks.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon"><ExperimentOutlined /></div>
                <div className="empty-state-text">暂无生成任务，开始你的第一个测试用例生成吧。</div>
              </div>
            ) : (
              <Row gutter={[16, 16]}>
                {data.recentTasks.map((task) => (
                  <Col xs={24} sm={12} lg={8} key={task.taskId}>
                    <Card
                      className="dashboard-card task-card"
                      size="small"
                      hoverable
                      onClick={() => navigate(`/?taskId=${task.taskId}`)}
                    >
                      <Typography.Text ellipsis style={{ fontSize: 13, fontWeight: 500 }}>
                        {task.requirementPreview}
                      </Typography.Text>
                      <div className="task-card-meta">
                        <span>{new Date(task.createdAt).toLocaleString("zh-CN")}</span>
                        <span>{task.caseCount != null ? `${task.caseCount} 条` : ""}</span>
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: add DashboardPage with quick actions, quality flow, and recent tasks"
```

---

### Task 9: Create `GenerateWizard` — Step 1

**Files:**
- Create: `frontend/src/pages/GenerateWizard.tsx`

- [ ] **Step 1: Write the wizard shell with Step 1**

```tsx
import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Collapse,
  Input,
  message,
  Radio,
  Select,
  Slider,
  Space,
  Steps,
  Typography,
} from "antd";
import {
  ThunderboltOutlined,
  PaperClipOutlined,
  PictureOutlined,
  InboxOutlined,
  SearchOutlined,
  CheckCircleFilled,
  MinusCircleFilled,
  CloseCircleFilled,
} from "@ant-design/icons";
import type { UploadFile, UploadProps } from "antd/es/upload/interface";
import { Upload, Card } from "antd";
import { useSearchParams } from "react-router-dom";
import {
  listModels,
  submitGenerateAsync,
  type ModelOption,
} from "../services/api";
import { useGenerationTask } from "../context/GenerationTaskContext";

const { TextArea } = Input;
const { Dragger } = Upload;

type WizardStep = 0 | 1 | 2;

type GenerationMode = "full" | "quick" | "custom";

const TEST_TYPE_OPTIONS = [
  { label: "功能测试", value: "functional" },
  { label: "边界测试", value: "boundary" },
  { label: "异常测试", value: "exception" },
  { label: "性能测试", value: "performance" },
];

function ReadinessItem({ ready, optional, label }: { ready: boolean; optional?: boolean; label: string }) {
  const icon = ready
    ? <CheckCircleFilled style={{ color: "var(--color-success)", fontSize: 12 }} />
    : optional
    ? <MinusCircleFilled style={{ color: "var(--text-muted)", fontSize: 12 }} />
    : <CloseCircleFilled style={{ color: "var(--text-muted)", fontSize: 12 }} />;

  return (
    <div className="wizard-readiness-item">
      {icon}
      <span style={{ color: ready ? "var(--text-primary)" : undefined }}>{label}</span>
    </div>
  );
}

export function GenerateWizard() {
  const [searchParams] = useSearchParams();
  const [messageApi, contextHolder] = message.useMessage();
  const {
    taskId,
    taskStatus,
    result: ctxResult,
    pollError,
    startTask,
    isRunning,
    cancelActiveTask,
  } = useGenerationTask();

  // Wizard state
  const [step, setStep] = useState<WizardStep>(0);
  const [mode, setMode] = useState<GenerationMode>(
    searchParams.get("mode") === "quick" ? "quick" : "full"
  );

  // Step 1 state
  const [requirementText, setRequirementText] = useState("");
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [selectedModelKey, setSelectedModelKey] = useState<string>();

  // Step 2 state
  const [documentFileList, setDocumentFileList] = useState<UploadFile[]>([]);
  const [imageFileList, setImageFileList] = useState<UploadFile[]>([]);

  // Advanced options
  const [selectedTestTypes, setSelectedTestTypes] = useState<string[]>(["functional"]);
  const [caseCount, setCaseCount] = useState(20);

  const [errorMessage, setErrorMessage] = useState("");
  const [generating, setGenerating] = useState(false);

  const documentFiles = useMemo(() =>
    documentFileList.flatMap((f) => (f.originFileObj ? [f.originFileObj as File] : [])),
    [documentFileList]
  );
  const imageFiles = useMemo(() =>
    imageFileList.flatMap((f) => (f.originFileObj ? [f.originFileObj as File] : [])),
    [imageFileList]
  );

  const hasRequirementText = requirementText.trim().length > 0;
  const hasAttachments = documentFiles.length > 0 || imageFiles.length > 0;
  const canSubmit = hasRequirementText || hasAttachments;

  // Load models
  useEffect(() => {
    listModels()
      .then((opts) => {
        setModelOptions(opts);
        setSelectedModelKey((k) => k ?? opts[0]?.key);
      })
      .catch(() => {});
  }, []);

  // Handle errors from polling
  useEffect(() => {
    if (pollError) setErrorMessage(pollError);
  }, [pollError]);

  useEffect(() => {
    if (taskStatus?.status === "failed") {
      setErrorMessage(taskStatus.errorMessage ?? "生成失败，请稍后重试。");
      setGenerating(false);
    }
    if (taskStatus?.status === "succeeded") {
      setGenerating(false);
    }
  }, [taskStatus]);

  const handleGenerate = async () => {
    setErrorMessage("");
    try {
      const { taskId: tid } = await submitGenerateAsync(
        requirementText.trim(),
        documentFiles,
        imageFiles,
        selectedModelKey
      );
      startTask(tid);
      setGenerating(true);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "生成失败，请稍后重试。");
    }
  };

  const stepItems = [
    { title: "输入需求" },
    ...(mode === "quick" ? [] : [{ title: "上传资料" }]),
    { title: "确认生成" },
  ];

  const renderStep0 = () => (
    <div className="wizard-step">
      <Card className="wizard-card" title="产品需求描述">
        <TextArea
          rows={8}
          value={requirementText}
          onChange={(e) => setRequirementText(e.target.value)}
          placeholder="描述你要测试的功能或产品需求，例如：用户登录功能，支持手机号+验证码和账号密码两种方式..."
          maxLength={10000}
          style={{ fontSize: 14, lineHeight: 1.7 }}
        />
        <div className="char-count">
          {requirementText.length > 0 ? `${requirementText.length} 字符 / 建议至少 50 字符` : "建议至少 50 字符"}
        </div>
      </Card>

      <Card className="wizard-card" title="生成模式" style={{ marginTop: 16 }}>
        <Radio.Group
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          size="middle"
        >
          <Radio.Button value="full">完整模式</Radio.Button>
          <Radio.Button value="quick">快速模式</Radio.Button>
          <Radio.Button value="custom">自定义</Radio.Button>
        </Radio.Group>
        <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          {mode === "full" && "生成完整的功能/边界/异常/性能测试用例"}
          {mode === "quick" && "单次 LLM 调用，快速生成测试要点"}
          {mode === "custom" && "自定义测试类型和用例数量"}
        </Typography.Paragraph>

        {mode === "custom" && (
          <Collapse
            ghost
            defaultActiveKey={["advanced"]}
            items={[{
              key: "advanced",
              label: "高级选项",
              children: (
                <Space direction="vertical" style={{ width: "100%" }}>
                  <div>
                    <Typography.Text style={{ fontSize: 13 }}>模型选择</Typography.Text>
                    <Select
                      value={selectedModelKey}
                      onChange={setSelectedModelKey}
                      options={modelOptions.map((m) => ({ value: m.key, label: m.label }))}
                      style={{ width: "100%", marginTop: 4 }}
                    />
                  </div>
                  <div>
                    <Typography.Text style={{ fontSize: 13 }}>测试类型</Typography.Text>
                    <Select
                      mode="multiple"
                      value={selectedTestTypes}
                      onChange={setSelectedTestTypes}
                      options={TEST_TYPE_OPTIONS}
                      style={{ width: "100%", marginTop: 4 }}
                    />
                  </div>
                  <div>
                    <Typography.Text style={{ fontSize: 13 }}>用例数量: {caseCount} 条</Typography.Text>
                    <Slider
                      min={5}
                      max={50}
                      value={caseCount}
                      onChange={setCaseCount}
                      style={{ marginTop: 4 }}
                    />
                  </div>
                </Space>
              ),
            }]}
          />
        )}

        {mode !== "custom" && (
          <div style={{ marginTop: 12 }}>
            <Typography.Text style={{ fontSize: 13 }}>模型选择</Typography.Text>
            <Select
              value={selectedModelKey}
              onChange={setSelectedModelKey}
              options={modelOptions.map((m) => ({ value: m.key, label: m.label }))}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
        )}
      </Card>

      <div className="wizard-actions">
        <Button type="primary" size="large" onClick={() => setStep(mode === "quick" ? 2 : 1)} disabled={!hasRequirementText && !hasAttachments}>
          下一步
        </Button>
      </div>
    </div>
  );

  const renderStep1 = () => (
    <div className="wizard-step">
      <Card className="wizard-card" title="参考文档（可选）">
        <Dragger
          beforeUpload={() => false}
          fileList={documentFileList}
          onChange={({ fileList }) => setDocumentFileList(fileList)}
          accept=".txt,.md,.pdf,.docx"
          multiple
          maxCount={6}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">拖拽文件到此处或点击上传</p>
          <p className="ant-upload-hint">支持 PDF / Word / Markdown / Txt，最多 6 个文件</p>
        </Dragger>
      </Card>

      <Card className="wizard-card" title="界面截图（可选）" style={{ marginTop: 16 }}>
        <Upload
          beforeUpload={() => false}
          fileList={imageFileList}
          onChange={({ fileList }) => setImageFileList(fileList)}
          accept="image/*"
          listType="picture-card"
          multiple
          maxCount={6}
        >
          {imageFileList.length < 6 && (
            <div>
              <PictureOutlined style={{ fontSize: 20 }} />
              <div style={{ marginTop: 8 }}>上传截图</div>
            </div>
          )}
        </Upload>
      </Card>

      <div className="wizard-actions">
        <Button size="large" onClick={() => setStep(0)}>上一步</Button>
        <Button type="primary" size="large" onClick={() => setStep(2)}>下一步</Button>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="wizard-step">
      <Card className="wizard-card" title="生成概览">
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div className="wizard-summary-item">
              <div className="wizard-summary-label">生成模式</div>
              <div className="wizard-summary-value">{mode === "full" ? "完整模式" : mode === "quick" ? "快速模式" : "自定义"}</div>
            </div>
          </Col>
          <Col span={6}>
            <div className="wizard-summary-item">
              <div className="wizard-summary-label">测试类型</div>
              <div className="wizard-summary-value">{selectedTestTypes.length} 种</div>
            </div>
          </Col>
          <Col span={6}>
            <div className="wizard-summary-item">
              <div className="wizard-summary-label">预计用例</div>
              <div className="wizard-summary-value">~{caseCount} 条</div>
            </div>
          </Col>
          <Col span={6}>
            <div className="wizard-summary-item">
              <div className="wizard-summary-label">参考文件</div>
              <div className="wizard-summary-value">{documentFileList.length + imageFileList.length} 个</div>
            </div>
          </Col>
        </Row>
        {hasRequirementText && (
          <div style={{ marginTop: 12 }}>
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>需求摘要：</Typography.Text>
            <Typography.Paragraph ellipsis={{ rows: 2, expandable: true }} style={{ fontSize: 13, marginBottom: 0 }}>
              {requirementText}
            </Typography.Paragraph>
          </div>
        )}
      </Card>

      <Card className="wizard-card" title="就绪检查" style={{ marginTop: 16 }}>
        <div className="wizard-readiness-list">
          <ReadinessItem ready={hasRequirementText} label={hasRequirementText ? `已填写需求描述 (${requirementText.length} 字符)` : "请填写需求描述"} />
          <ReadinessItem ready={documentFileList.length > 0} optional label={documentFileList.length > 0 ? `已上传 ${documentFileList.length} 份文档` : "未上传参考文档（可选）"} />
          <ReadinessItem ready={imageFileList.length > 0} optional label={imageFileList.length > 0 ? `已上传 ${imageFileList.length} 张图片` : "未上传界面截图（可选）"} />
        </div>
      </Card>

      <div className="wizard-actions">
        <Button size="large" onClick={() => setStep(mode === "quick" ? 0 : 1)}>上一步</Button>
        <Button type="primary" size="large" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={generating} disabled={!canSubmit}>
          {generating ? "生成中..." : "开始生成"}
        </Button>
      </div>
    </div>
  );

  // Show progress during generation
  if (generating && isRunning) {
    return (
      <div className="generate-progress">
        {contextHolder}
        <div className="generate-progress-header">
          <Typography.Title level={4}>正在生成测试用例...</Typography.Title>
        </div>
        {/* Reuse existing GenerationProgress component */}
        <div className="generation-progress-panel">
          {/* Progress from context */}
        </div>
        <Button onClick={cancelActiveTask} style={{ marginTop: 16 }}>取消生成</Button>
      </div>
    );
  }

  return (
    <div className="generate-wizard">
      {contextHolder}
      <div className="wizard-header">
        <Typography.Title level={4} style={{ margin: 0 }}>测试用例生成</Typography.Title>
      </div>

      {errorMessage && (
        <Alert
          type="error"
          showIcon
          closable
          message={errorMessage}
          onClose={() => setErrorMessage("")}
          style={{ marginBottom: 16 }}
        />
      )}

      <Steps
        current={step}
        items={stepItems}
        className="wizard-steps"
        size="small"
      />

      {step === 0 && renderStep0()}
      {step === 1 && renderStep1()}
      {step === 2 && renderStep2()}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/GenerateWizard.tsx
git commit -m "feat: add GenerateWizard with 3-step generation flow"
```

---

### Task 10: Update `App.tsx` routes

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update routes to include dashboard and wizard, keep old routes hidden**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { GenerationTaskProvider } from "./context/GenerationTaskContext";
import { DashboardPage } from "./pages/DashboardPage";
import { GenerateWizard } from "./pages/GenerateWizard";
import { KnowledgeDetailPage } from "./pages/KnowledgeDetailPage";
import { KnowledgeListPage } from "./pages/KnowledgeListPage";
import { ToolsPage } from "./pages/ToolsPage";
import { ConfigPage } from "./pages/ConfigPage";
// Hidden module routes - preserved but not in navigation
import { GeneratorPage } from "./pages/GeneratorPage";
import { QuickGeneratePage } from "./pages/QuickGeneratePage";
import { SubmissionPage } from "./pages/SubmissionPage";
import { SubmissionDetailPage } from "./pages/SubmissionDetailPage";
import { ReviewListPage } from "./pages/ReviewListPage";
import { DefectListPage } from "./pages/DefectListPage";
import { AutoTestDashboard, CaseListPage, ExecutionDetailPage, ExecutionListPage, PlanListPage, RecommendPage, SuiteListPage } from "./pages/AutoTest";

function App() {
  return (
    <BrowserRouter>
      <GenerationTaskProvider>
        <Routes>
          <Route element={<AppLayout />}>
            {/* Active routes */}
            <Route index element={<DashboardPage />} />
            <Route path="generate" element={<GenerateWizard />} />
            <Route path="knowledge" element={<KnowledgeListPage />} />
            <Route path="knowledge/:id" element={<KnowledgeDetailPage />} />
            <Route path="tools" element={<ToolsPage />} />
            <Route path="settings" element={<ConfigPage />} />

            {/* Hidden routes - preserved for direct access */}
            <Route path="legacy" element={<GeneratorPage />} />
            <Route path="quick" element={<QuickGeneratePage />} />
            <Route path="submissions" element={<SubmissionPage />} />
            <Route path="submissions/:id" element={<SubmissionDetailPage />} />
            <Route path="reviews" element={<ReviewListPage />} />
            <Route path="defects" element={<DefectListPage />} />
            <Route path="auto-test" element={<AutoTestDashboard />} />
            <Route path="auto-test/suites" element={<SuiteListPage />} />
            <Route path="auto-test/cases" element={<CaseListPage />} />
            <Route path="auto-test/plans" element={<PlanListPage />} />
            <Route path="auto-test/recommend" element={<RecommendPage />} />
            <Route path="auto-test/executions" element={<ExecutionListPage />} />
            <Route path="auto-test/executions/:id" element={<ExecutionDetailPage />} />
          </Route>
        </Routes>
      </GenerationTaskProvider>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: update routes with dashboard as index, wizard at /generate, hidden legacy routes"
```

---

### Task 11: Redesign `KnowledgeListPage` with card grid

**Files:**
- Modify: `frontend/src/pages/KnowledgeListPage.tsx`

- [ ] **Step 1: Rewrite KnowledgeListPage with card grid layout**

Keep the same data fetching logic (fetchDocuments, fetchStats, handleDelete, handleReindex). Replace the Table rendering with a card grid + optional table toggle.

Add a `viewMode` state: `"grid" | "list"`. Replace the `<Table>` with:

```tsx
// After the filter bar, add view toggle
<div className="knowledge-view-toggle">
  <Button
    type={viewMode === "grid" ? "primary" : "default"}
    icon={<AppstoreOutlined />}
    onClick={() => setViewMode("grid")}
    size="small"
  />
  <Button
    type={viewMode === "list" ? "primary" : "default"}
    icon={<UnorderedListOutlined />}
    onClick={() => setViewMode("list")}
    size="small"
  />
</div>

// Card grid
{viewMode === "grid" ? (
  <div className="knowledge-card-grid">
    {items.map((doc) => (
      <Card
        key={doc.id}
        className="knowledge-card"
        hoverable
        onClick={() => navigate(`/knowledge/${doc.id}`)}
        actions={[
          <Button type="text" size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); navigate(`/knowledge/${doc.id}`); }}>详情</Button>,
          <Button type="text" size="small" icon={<ReloadOutlined />} onClick={(e) => { e.stopPropagation(); handleReindex(doc.id); }}>索引</Button>,
          <Popconfirm title="确定删除此文档？" onConfirm={(e) => { e?.stopPropagation(); handleDelete(doc.id); }}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()}>删除</Button>
          </Popconfirm>,
        ]}
      >
        <div className="knowledge-card-icon">
          {doc.sourceType === "upload" ? <FilePdfOutlined /> : <FileTextOutlined />}
        </div>
        <Typography.Text strong ellipsis className="knowledge-card-title">{doc.title}</Typography.Text>
        <div className="knowledge-card-tags">
          <Tag color={DOC_TYPE_COLOR[doc.docType] ?? "default"}>
            {DOC_TYPE_OPTIONS.find((o) => o.value === doc.docType)?.label ?? doc.docType}
          </Tag>
          {doc.moduleTags?.slice(0, 2).map((t) => <Tag key={t}>{t}</Tag>)}
        </div>
        <div className="knowledge-card-meta">
          <span>{new Date(doc.createdAt).toLocaleDateString("zh-CN")}</span>
        </div>
      </Card>
    ))}
  </div>
) : (
  <Table ... existing table code ... />
)}
```

Need to import `AppstoreOutlined, UnorderedListOutlined, FilePdfOutlined, FileTextOutlined`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/KnowledgeListPage.tsx
git commit -m "feat: redesign KnowledgeListPage with card grid layout and view toggle"
```

---

### Task 12: Enhance `KnowledgeDetailPage`

**Files:**
- Modify: `frontend/src/pages/KnowledgeDetailPage.tsx`

- [ ] **Step 1: Add document header section with improved layout**

Keep existing logic intact. Wrap the header in a styled card. Add a related generations placeholder:

```tsx
{/* After the chunks section, add related generations */}
<div className="knowledge-detail-section">
  <div className="knowledge-detail-section-title">关联用例</div>
  <Typography.Text type="secondary" style={{ fontSize: 13 }}>
    基于此文档生成的用例信息将在后续版本中展示。
  </Typography.Text>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/KnowledgeDetailPage.tsx
git commit -m "feat: enhance KnowledgeDetailPage with improved layout and related generations placeholder"
```

---

### Task 13: Polish `ToolsPage`

**Files:**
- Modify: `frontend/src/pages/ToolsPage.tsx`

- [ ] **Step 1: Minor layout enhancements**

Keep current structure. Wrap header in `PageHeader` component and adjust spacing:

```tsx
import { PageHeader } from "../components/shared/PageHeader";

// Replace the tools-page-header div with:
<PageHeader
  title="测试工具集"
  subtitle="常用开发调试工具，提升日常工作效率。"
/>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ToolsPage.tsx
git commit -m "feat: polish ToolsPage with shared PageHeader"
```

---

### Task 14: Enhance `ConfigPage` — inline card edit

**Files:**
- Modify: `frontend/src/pages/ConfigPage.tsx`

- [ ] **Step 1: Add inline edit support to LLMConfigCard**

The current code already uses modal for editing. The spec calls for inline edit within the card. Since the config form is complex (many fields), replace the modal trigger with expandable card content:

In `LLMConfigCard`, when editing, expand the card body to show the form inline instead of opening modal. The form fields remain the same — just rendered inside the card's body instead of a modal.

Keep the existing modal as a fallback for "Add" operations. For "Edit", expand the card inline.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ConfigPage.tsx
git commit -m "feat: add inline edit support to ConfigPage model cards"
```

---

### Task 15: Add new CSS styles

**Files:**
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Append new styles to global.css**

Add the following CSS blocks after the existing content:

```css
/* ============================================================
   Layout V2 - Sidebar + Top Status Bar
   ============================================================ */
.app-shell-v2 {
  min-height: 100vh;
  background: var(--bg-page);
  display: flex;
  flex-direction: row;
}

.app-main-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.app-content-v2 {
  padding: var(--space-lg) var(--space-xl);
  max-width: var(--max-content);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  animation: fadeIn 0.3s ease-out;
}

/* ============================================================
   Sidebar
   ============================================================ */
.sidebar {
  width: 240px;
  min-width: 240px;
  height: 100vh;
  position: sticky;
  top: 0;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal), min-width var(--transition-normal);
  z-index: 50;
  overflow: hidden;
}

.sidebar--collapsed {
  width: 60px;
  min-width: 60px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-light);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  cursor: pointer;
  min-width: 0;
}

.sidebar-brand-icon {
  font-size: 20px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.sidebar-brand-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-collapse-btn {
  background: transparent;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.sidebar-collapse-btn:hover {
  background: var(--bg-inset);
  color: var(--text-primary);
}

/* Sidebar Search */
.sidebar-search {
  padding: var(--space-sm) var(--space-md);
}

.sidebar-search-input {
  border-radius: var(--radius-sm) !important;
  border-color: var(--border-light) !important;
}

.sidebar-search-input:hover,
.sidebar-search-input:focus {
  border-color: var(--color-primary-light) !important;
}

.sidebar--collapsed .sidebar-search {
  padding: var(--space-sm) 8px;
}

/* Sidebar Navigation */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-sm) var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-group-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  padding: var(--space-sm) var(--space-md) 4px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  width: 100%;
  text-align: left;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.sidebar-item:hover {
  background: rgba(0, 113, 227, 0.06);
  color: var(--text-primary);
}

.sidebar-item--active {
  background: rgba(0, 113, 227, 0.1) !important;
  color: var(--color-primary) !important;
  font-weight: 600;
}

.sidebar-item-icon {
  font-size: 18px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.sidebar--collapsed .sidebar-item {
  justify-content: center;
  padding: 10px;
}

.sidebar--collapsed .sidebar-item-icon {
  font-size: 20px;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: var(--space-sm) var(--space-md);
  border-top: 1px solid var(--border-light);
}

.sidebar-footer-text {
  font-size: 11px;
  color: var(--text-muted);
}

/* ============================================================
   Top Status Bar
   ============================================================ */
.top-status-bar {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 40;
}

.top-status-bar-inner {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: 8px var(--space-xl);
  max-width: var(--max-content);
  margin: 0 auto;
}

.top-status-metric {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.top-status-metric-label {
  color: var(--text-muted);
}

.top-status-metric-value {
  font-weight: 600;
  color: var(--text-primary);
}

.top-status-metric-trend {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.top-status-metric-trend.up {
  color: var(--color-success);
  background: rgba(52, 199, 89, 0.1);
}

.top-status-metric-trend.down {
  color: var(--color-danger);
  background: rgba(255, 59, 48, 0.1);
}

/* ============================================================
   Dashboard
   ============================================================ */
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  animation: fadeIn 0.4s ease-out;
}

.dashboard-greeting {
  padding-bottom: var(--space-sm);
}

.dashboard-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.dashboard-section-title {
  margin: 0 !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

.dashboard-card {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--border-light) !important;
  box-shadow: var(--shadow-card);
}

/* Quick Action Cards */
.quick-action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-xl) var(--space-md);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-card);
}

.quick-action-card:hover {
  border-color: rgba(0, 113, 227, 0.3);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.quick-action-icon {
  font-size: 28px;
  color: var(--color-primary);
}

.quick-action-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  text-align: center;
}

/* Task Card */
.task-card {
  cursor: pointer;
}

.task-card-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

/* Stats Card */
.stats-card {
  background: var(--card-accent-bg, var(--bg-inset));
  border-radius: var(--radius-md);
  padding: var(--space-md);
  text-align: center;
  transition: all var(--transition-fast);
}

.stats-card--clickable {
  cursor: pointer;
}

.stats-card--clickable:hover {
  transform: translateY(-2px);
}

.stats-card-icon {
  font-size: 18px;
  color: var(--card-accent, var(--text-secondary));
  margin-bottom: 4px;
}

.stats-card-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--card-accent, var(--text-primary));
  font-family: var(--font-display);
}

.stats-card-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.stats-card-trend {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  margin-top: 4px;
}

.stats-card-trend.up {
  color: var(--color-success);
  background: rgba(52, 199, 89, 0.1);
}

.stats-card-trend.down {
  color: var(--color-danger);
  background: rgba(255, 59, 48, 0.1);
}

/* ============================================================
   Quality Flow Diagram
   ============================================================ */
.quality-flow {
  display: flex;
  align-items: flex-start;
  gap: 0;
  overflow-x: auto;
  padding: var(--space-md) 0;
}

.quality-flow-item {
  display: flex;
  align-items: flex-start;
  flex-shrink: 0;
}

.quality-flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 4px 0;
  min-width: 40px;
}

.quality-flow-arrow-line {
  width: 24px;
  height: 2px;
  background: var(--border-light);
  position: relative;
}

.quality-flow-arrow-line::after {
  content: "";
  position: absolute;
  right: -2px;
  top: -3px;
  border: 4px solid transparent;
  border-left-color: var(--border-light);
}

.quality-flow-rate {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 600;
  margin-top: 2px;
}

.quality-flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-md);
  min-width: 80px;
}

.quality-flow-node--clickable {
  cursor: pointer;
  transition: all var(--transition-fast);
}

.quality-flow-node--clickable:hover {
  border-color: rgba(0, 113, 227, 0.3);
  box-shadow: var(--shadow-card);
  transform: translateY(-1px);
}

.quality-flow-node-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.quality-flow-node-count {
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-display);
}

/* ============================================================
   Page Header
   ============================================================ */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-md);
  padding: var(--space-xl);
  background: linear-gradient(135deg, rgba(0, 113, 227, 0.04) 0%, transparent 50%),
              linear-gradient(180deg, var(--bg-card) 0%, rgba(245, 245, 247, 0.8) 100%);
  border: 1px solid rgba(0, 113, 227, 0.1);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
}

.page-header-main {
  min-width: 0;
  flex: 1;
}

.page-header-eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.page-header-stats {
  display: flex;
  gap: var(--space-lg);
}

.page-header-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-header-stat-value {
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-display);
  color: var(--text-primary);
}

.page-header-stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.page-header-extra {
  flex-shrink: 0;
}

/* ============================================================
   Generate Wizard
   ============================================================ */
.generate-wizard {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  animation: fadeIn 0.4s ease-out;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.wizard-header {
  text-align: center;
  padding: var(--space-md) 0;
}

.wizard-steps {
  margin-bottom: var(--space-md);
}

.wizard-step {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.wizard-card {
  border-radius: var(--radius-lg) !important;
  border: 1px solid rgba(0, 113, 227, 0.12) !important;
  box-shadow: var(--shadow-card);
}

.wizard-card .ant-card-head {
  border-bottom: 1px solid var(--border-light);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.02) 0%, transparent 100%);
}

.wizard-card .ant-card-head-title {
  font-size: 14px;
  font-weight: 600;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-lg);
}

.wizard-readiness-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wizard-readiness-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 13px;
  color: var(--text-secondary);
}

.wizard-summary-item {
  text-align: center;
}

.wizard-summary-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.wizard-summary-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ============================================================
   Knowledge Card Grid
   ============================================================ */
.knowledge-view-toggle {
  display: flex;
  gap: 4px;
  margin-bottom: var(--space-md);
}

.knowledge-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}

.knowledge-card {
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-light) !important;
  transition: all var(--transition-normal);
}

.knowledge-card:hover {
  border-color: rgba(0, 113, 227, 0.3) !important;
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-2px);
}

.knowledge-card-icon {
  font-size: 32px;
  color: var(--color-primary);
  margin-bottom: var(--space-sm);
}

.knowledge-card-title {
  display: block;
  margin-bottom: var(--space-sm);
  font-size: 14px;
}

.knowledge-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: var(--space-sm);
}

.knowledge-card-meta {
  font-size: 12px;
  color: var(--text-muted);
}

/* ============================================================
   Responsive - Sidebar Layout
   ============================================================ */
@media (max-width: 1200px) {
  .app-content-v2 {
    padding: var(--space-lg);
  }

  .top-status-bar-inner {
    padding: 8px var(--space-lg);
  }
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
  }

  .sidebar--mobile-open {
    transform: translateX(0);
  }

  .app-content-v2 {
    padding: var(--space-md);
  }

  .top-status-bar-inner {
    padding: 8px var(--space-md);
    gap: var(--space-md);
    overflow-x: auto;
  }

  .dashboard-page {
    gap: var(--space-md);
  }

  .knowledge-card-grid {
    grid-template-columns: 1fr;
  }

  .quality-flow {
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 100%;
    max-width: 280px;
  }

  .quick-action-card {
    padding: var(--space-md);
  }

  .quick-action-icon {
    font-size: 22px;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/styles/global.css
git commit -m "feat: add sidebar, dashboard, wizard, knowledge-card, and responsive styles"
```

---

### Task 16: Integration test — verify the app builds and dev server starts

**Files:** None (verification only)

- [ ] **Step 1: TypeScript check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | tail -30`

Expected: No type errors.

- [ ] **Step 2: Build check**

Run: `cd frontend && npm run build 2>&1 | tail -20`

Expected: Build succeeds.

- [ ] **Step 3: Start dev server**

Run: `cd frontend && npm run dev &`
Wait 5 seconds, then run: `curl -s http://localhost:5173 | head -20`

Expected: Returns HTML with the React app shell.

- [ ] **Step 4: Kill dev server**

Run: `kill %1`

---

### Task 17: Final verification and cleanup

- [ ] **Step 1: Verify all routes are accessible**

Start dev server, test:
- `http://localhost:5173/` → Dashboard
- `http://localhost:5173/generate` → Wizard
- `http://localhost:5173/knowledge` → Knowledge list
- `http://localhost:5173/tools` → Tools
- `http://localhost:5173/settings` → Settings
- Hidden routes should still work (e.g., `/submissions`, `/reviews`)

- [ ] **Step 2: Verify sidebar navigation works**
  - Click each nav item, verify navigation
  - Test collapse/expand
  - Test search filtering
  - Test that recent visits reorder items

- [ ] **Step 3: Commit any remaining changes**

```bash
git status
git add -A
git commit -m "chore: final cleanup and verification for frontend redesign"
```
