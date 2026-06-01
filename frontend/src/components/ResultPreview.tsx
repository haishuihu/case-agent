import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { TestCaseCard } from "./TestCaseCard";
import {
  CopyOutlined,
  FileMarkdownOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  DashboardOutlined,
  AppstoreOutlined,
  TableOutlined,
  ReadOutlined,
  SearchOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  FireOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

import {
  downloadGenerationExport,
  type ExportFormat,
  type GenerateResult,
  type TaskStatusPayload,
  type TestCaseItem,
} from "../services/api";
import { GenerationProgress } from "./GenerationProgress";

interface ResultPreviewProps {
  result: GenerateResult | null;
  loading?: boolean;
  taskStatus?: TaskStatusPayload | null;
  onCancelTask?: () => void;
  cancellingTask?: boolean;
  // Edit mode props
  editable?: boolean;
  selectedCaseIds?: Set<string>;
  onToggleSelect?: (caseId: string) => void;
  onEditCase?: (tc: TestCaseItem) => void;
  onDeleteCase?: (tc: TestCaseItem) => void;
  onCreateCase?: (moduleName: string) => void;
  onBatchDelete?: () => void;
}

const PRIORITY_COLORS: Record<string, string> = {
  P0: "#DC2626",
  P1: "#F97316",
  P2: "#2563EB",
  P3: "#6B7280",
};

const PRIORITY_LABELS: Record<string, string> = {
  P0: "冒烟",
  P1: "核心",
  P2: "重要",
  P3: "边缘",
};

function groupByModule(cases: TestCaseItem[]): Map<string, TestCaseItem[]> {
  const groups = new Map<string, TestCaseItem[]>();
  for (const c of cases) {
    const key = c.module || "未分组";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(c);
  }
  return groups;
}

const STAT_CARD_META = [
  { key: "caseCount", label: "总用例数", tone: "accent" },
  { key: "moduleCount", label: "模块数", tone: "default" },
  { key: "categoryCount", label: "覆盖类别数", tone: "default" },
  { key: "smokeCount", label: "冒烟用例", tone: "warm" },
] as const;


export function ResultPreview({
  result,
  loading,
  taskStatus,
  onCancelTask,
  cancellingTask,
  editable,
  selectedCaseIds,
  onToggleSelect,
  onEditCase,
  onDeleteCase,
  onCreateCase,
  onBatchDelete,
}: ResultPreviewProps) {
  const [messageApi, contextHolder] = message.useMessage();
  const [priorityFilter, setPriorityFilter] = useState<string | undefined>(
    undefined
  );
  const [moduleFilter, setModuleFilter] = useState<string | undefined>(
    undefined
  );
  const [searchText, setSearchText] = useState("");
  const markdown = result?.markdown ?? "";

  const filteredCases = useMemo(() => {
    if (!result) return [];
    let cases = result.cases;
    if (priorityFilter) {
      cases = cases.filter((c) => c.priority === priorityFilter);
    }
    if (moduleFilter) {
      cases = cases.filter((c) => c.module === moduleFilter);
    }
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      cases = cases.filter(
        (c) =>
          c.summary.toLowerCase().includes(q) ||
          (c.confirmationNote ?? "").toLowerCase().includes(q)
      );
    }
    return cases;
  }, [result, priorityFilter, moduleFilter, searchText]);

  const moduleOptions = useMemo(() => {
    if (!result) return [];
    const modules = new Set(result.cases.map((c) => c.module).filter(Boolean));
    return Array.from(modules).map((m) => ({ value: m, label: m }));
  }, [result]);


  const smokeCases = useMemo(
    () => (result ? result.cases.filter((c) => c.priority === "P0") : []),
    [result]
  );
  const confirmationCount = useMemo(
    () => filteredCases.filter((c) => Boolean(c.confirmationNote)).length,
    [filteredCases]
  );

  const overviewStats = result
    ? {
        caseCount: result.metadata.caseCount,
        moduleCount: Object.keys(result.metadata.moduleCounts).length,
        categoryCount: Object.keys(result.metadata.categoryCounts).length,
        smokeCount: smokeCases.length,
      }
    : null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(markdown);
    messageApi.success("测试用例已复制到剪贴板");
  };

  const handleExport = async (format: ExportFormat) => {
    if (!result) return;
    const { blob, filename } = await downloadGenerationExport(
      result.generationId,
      format
    );
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
    messageApi.success(`已导出 ${filename}`);
  };

  // ── Overview Tab ──────────────────────────────────────────
  const overviewTab = result && (
    <div className="result-workspace">
      <div className="overview-hero">
        <div className="overview-hero-main">
          <Typography.Text className="overview-hero-eyebrow">
            Generation Overview
          </Typography.Text>
          <Typography.Title level={4} style={{ margin: "8px 0 10px", fontFamily: "var(--font-display)" }}>
            已生成 {result.metadata.caseCount} 条结构化测试用例
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 14 }}>
            当前结果已按模块、优先级和覆盖类别整理，可继续用表格视图筛选，也可直接导出为文档格式进行评审
          </Typography.Paragraph>
        </div>
        <div className="overview-hero-side">
          {result.modelName ? <Tag color="blue">{result.modelName}</Tag> : null}
          <Tag color="green">{result.attachmentCount} 份参考文件</Tag>
        </div>
      </div>

      <div className="overview-stats">
        {STAT_CARD_META.map((item) => (
          <div
            key={item.key}
            className={`stat-card${item.tone === "accent" ? " accent" : ""}${item.tone === "warm" ? " warm" : ""}`}
          >
            <div className="stat-value">
              {overviewStats ? overviewStats[item.key] : 0}
            </div>
            <div className="stat-label">{item.label}</div>
          </div>
        ))}
      </div>

      <div className="overview-panels">
        <div className="overview-panel">
          <div className="tag-group-label">优先级分布</div>
          <div className="tag-group">
            {Object.entries(result.metadata.priorityCounts).map(([p, count]) => (
              <Tag key={p} color={PRIORITY_COLORS[p] ?? "default"}>
                {p} {PRIORITY_LABELS[p] ?? ""} · {count} 条
              </Tag>
            ))}
          </div>
        </div>

        <div className="overview-panel">
          <div className="tag-group-label">模块分布</div>
          <div className="tag-group">
            {Object.entries(result.metadata.moduleCounts).map(([mod, count]) => (
              <Tag key={mod} color="geekblue">
                {mod} · {count}
              </Tag>
            ))}
          </div>
        </div>
      </div>

      <div className="generation-summary generation-summary-block" style={{ marginTop: 16 }}>
        <Space size="large" wrap>
          {result.modelName && (
            <span>
              模型：<strong>{result.modelName}</strong>
            </span>
          )}
          {result.attachmentCount > 0 && (
            <span>参考文件：{result.attachmentCount} 份</span>
          )}
          <span>
            生成时间：
            {new Date(result.createdAt).toLocaleString("zh-CN")}
          </span>
        </Space>
      </div>

      {/* Review questions */}
      {result.metadata.reviewQuestions.length > 0 && (
        <div className="risk-section" style={{ marginTop: 16 }}>
          <Typography.Text strong className="risk-section-title">
            <ExclamationCircleOutlined
              style={{ color: "var(--color-warning)", marginRight: 6 }}
            />
            需求待确认问题（{result.metadata.reviewQuestions.length} 项）
          </Typography.Text>
          {result.metadata.reviewQuestions.map((q) => (
            <Alert
              key={q.id}
              type="warning"
              showIcon
              message={
                <span>
                  <Tag style={{ fontSize: 11 }}>{q.questionType}</Tag>
                  {q.description}
                </span>
              }
              description={
                q.suggestion ? (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    建议：{q.suggestion}
                  </Typography.Text>
                ) : undefined
              }
              style={{ background: "#fffbe6" }}
            />
          ))}
        </div>
      )}

      {/* Warnings / Truncation */}
      {result.metadata.truncated && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="本次生成存在不完整批次"
          description={
            result.metadata.incompleteCategories.length
              ? `可能受输出长度或模型返回格式影响：${result.metadata.incompleteCategories.join("、")}`
              : "模型在部分批次可能被截断，请根据需要重新生成或切换模型。"
          }
          style={{ marginTop: 12 }}
        />
      )}
      {result.metadata.warnings.length > 0 && (
        <Alert
          type="info"
          showIcon
          message="生成提示"
          description={result.metadata.warnings.join("；")}
          style={{ marginTop: 8 }}
        />
      )}
    </div>
  );

  // ── Filter Bar ────────────────────────────────────────────
  const filterBar = (
    <div className="table-workbench-toolbar">
      <div className="filter-toolbar">
        <Select
          allowClear
          placeholder="优先级"
          value={priorityFilter}
          onChange={setPriorityFilter}
          style={{ width: 120 }}
          size="small"
          options={[
            { value: "P0", label: "P0 冒烟" },
            { value: "P1", label: "P1 核心" },
            { value: "P2", label: "P2 重要" },
            { value: "P3", label: "P3 边缘" },
          ]}
        />
        <Select
          allowClear
          placeholder="模块"
          value={moduleFilter}
          onChange={setModuleFilter}
          style={{ width: 160 }}
          size="small"
          options={moduleOptions}
        />
        <Input
          allowClear
          placeholder="搜索标题 / ID"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 180 }}
          size="small"
        />
        <span className="filter-count">
          {filteredCases.length} / {result?.cases.length ?? 0} 条
        </span>
      </div>
      <div className="table-workbench-metrics">
        <div className="table-metric-pill">
          <span className="table-metric-label">当前结果</span>
          <strong>{filteredCases.length}</strong>
        </div>
        <div className="table-metric-pill">
          <span className="table-metric-label">P0</span>
          <strong>{filteredCases.filter((c) => c.priority === "P0").length}</strong>
        </div>
        <div className="table-metric-pill">
          <span className="table-metric-label">待确认</span>
          <strong>{confirmationCount}</strong>
        </div>
        <div className="table-metric-pill">
          <span className="table-metric-label">模块</span>
          <strong>{new Set(filteredCases.map((c) => c.module).filter(Boolean)).size}</strong>
        </div>
      </div>
    </div>
  );

  // ── Smoke Panel ───────────────────────────────────────────
  const smokePanel = smokeCases.length > 0 && (
    <div className="smoke-panel">
      <div className="smoke-panel-title">
        <FireOutlined />
        冒烟测试用例（P0）· {smokeCases.length} 条
      </div>
      <TestCaseCard cases={smokeCases} searchText={searchText} />
    </div>
  );

  // ── Convert to UI Automation ──────────────────────────────
  const [convertOpen, setConvertOpen] = useState(false);
  const [convertSuiteId, setConvertSuiteId] = useState<string>("");
  const [convertSuites, setConvertSuites] = useState<{ id: string; name: string }[]>([]);
  const [convertEnvs, setConvertEnvs] = useState<{ id: string; name: string; baseUrl: string }[]>([]);
  const [convertEnvId, setConvertEnvId] = useState<string>("");
  const [convertBaseUrl, setConvertBaseUrl] = useState<string>("");
  const [convertLoading, setConvertLoading] = useState(false);
  const [convertMsg, convertMsgCtx] = message.useMessage();

  const handleConvertToUI = async () => {
    setConvertLoading(true);
    try {
      const { listSuites, listEnvironments } = await import("../services/autoTest");
      const [suites, envs] = await Promise.all([listSuites(), listEnvironments()]);
      if (suites.length === 0) {
        convertMsg.warning("请先在自动化测试模块中创建测试套件");
        return;
      }
      setConvertSuites(suites.map((s) => ({ id: s.id, name: s.name })));
      setConvertSuiteId(suites[0].id);
      setConvertEnvs(envs.map((e) => ({ id: e.id, name: e.name, baseUrl: e.baseUrl || "" })));
      if (envs.length > 0) {
        setConvertEnvId(envs[0].id);
        setConvertBaseUrl(envs[0].baseUrl || "");
      }
      setConvertOpen(true);
    } catch (e: unknown) {
      convertMsg.error("加载套件列表失败: " + (e as Error).message);
    } finally {
      setConvertLoading(false);
    }
  };

  const doConvert = async () => {
    if (!result || !convertSuiteId) return;
    setConvertLoading(true);
    try {
      const { convertCasesFromGeneration } = await import("../services/autoTest");
      const created = await convertCasesFromGeneration(
        result.generationId,
        convertSuiteId,
        undefined,
        convertBaseUrl || undefined,
      );
      convertMsg.success(`已转换 ${created.length} 个用例到 UI 自动化套件`);
      setConvertOpen(false);
    } catch (e: unknown) {
      convertMsg.error("转换失败: " + (e as Error).message);
    } finally {
      setConvertLoading(false);
    }
  };

  // ── Export Bar ────────────────────────────────────────────
  const exportBar = result && (
    <div className="export-bar">
      <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>
        复制
      </Button>
      <Button
        size="small"
        icon={<FileMarkdownOutlined />}
        onClick={() => handleExport("md")}
      >
        Markdown
      </Button>
      <Button
        size="small"
        icon={<FileTextOutlined />}
        onClick={() => handleExport("csv")}
      >
        CSV
      </Button>
      <Button
        size="small"
        icon={<FileExcelOutlined />}
        onClick={() => handleExport("xlsx")}
      >
        Excel
      </Button>
      <div className="export-bar-divider" />
      <Button
        size="small"
        type="primary"
        icon={<ThunderboltOutlined />}
        onClick={handleConvertToUI}
        loading={convertLoading}
      >
        AI 转 UI 自动化
      </Button>
    </div>
  );

  // ── Convert Modal ──────────────────────────────────────────
  const convertModal = (
    <Modal
      title="转换为 UI 自动化用例"
      open={convertOpen}
      onOk={doConvert}
      onCancel={() => setConvertOpen(false)}
      confirmLoading={convertLoading}
      okText="开始转换"
      cancelText="取消"
      width={520}
    >
      {convertMsgCtx}
      <div style={{ marginBottom: 16 }}>
        <Typography.Text>
          将当前生成的 <Tag color="blue">{result?.metadata.caseCount ?? 0}</Tag> 条自然语言测试用例，
          通过 AI 转换为结构化的 UI 自动化用例。
        </Typography.Text>
      </div>
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <div>
          <Typography.Text strong>目标测试套件：</Typography.Text>
          <Select
            value={convertSuiteId || undefined}
            onChange={(v) => setConvertSuiteId(v)}
            style={{ width: "100%", marginTop: 4 }}
            placeholder="选择目标测试套件"
            options={convertSuites.map((s) => ({ label: s.name, value: s.id }))}
          />
        </div>
        <div>
          <Typography.Text strong>目标测试环境：</Typography.Text>
          <Select
            value={convertEnvId || undefined}
            onChange={(v) => {
              setConvertEnvId(v);
              const env = convertEnvs.find((e) => e.id === v);
              setConvertBaseUrl(env?.baseUrl || "");
            }}
            style={{ width: "100%", marginTop: 4 }}
            placeholder="选择测试环境（可选，用于设置 base URL）"
            allowClear
            options={convertEnvs.map((e) => ({ label: `${e.name} (${e.baseUrl})`, value: e.id }))}
          />
        </div>
        <div>
          <Typography.Text strong>目标站点地址：</Typography.Text>
          <Input
            value={convertBaseUrl}
            onChange={(e) => setConvertBaseUrl(e.target.value)}
            style={{ marginTop: 4 }}
            placeholder="例如 https://staging.example.com"
          />
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            AI 生成的页面路径（如 /login）会拼接此地址构成完整 URL
          </Typography.Text>
        </div>
      </Space>
    </Modal>
  );

  // ── Empty / Loading State ─────────────────────────────────
  if (!result) {
    return (
      <>
        {contextHolder}
        <Card className="workspace-card result-card" style={{ minHeight: 400 }}>
          <div className="empty-state" style={{ minHeight: 340 }}>
            {loading ? (
              taskStatus ? (
                <GenerationProgress
                  taskStatus={taskStatus}
                  onCancel={onCancelTask}
                  cancelling={cancellingTask}
                />
              ) : (
                <>
                  <div className="empty-state-icon">
                    <DashboardOutlined spin />
                  </div>
                  <div className="empty-state-text">
                    AI 正在多阶段生成测试用例，请稍候...
                  </div>
                </>
              )
            ) : (
              <>
                <div className="empty-state-icon">
                  <CheckCircleOutlined />
                </div>
                <div className="empty-state-text">
                  在左侧填写需求摘要或上传参考文件后，结果将展示在此处
                </div>
              </>
            )}
          </div>
        </Card>
      </>
    );
  }

  // ── Main Tabbed Result View ───────────────────────────────
  return (
    <>
      {contextHolder}
      {convertMsgCtx}
      {convertModal}
      <Card
        className="workspace-card result-card"
        title={
          <Space wrap>
            <DashboardOutlined />
            <span>生成结果</span>
            <Tag color="green">{result.metadata.caseCount} 条用例</Tag>
          </Space>
        }
        extra={exportBar}
      >
        <Tabs
          items={[
            {
              key: "overview",
              label: (
                <span>
                  <DashboardOutlined /> 总览
                </span>
              ),
              children: overviewTab,
            },
            {
              key: "table",
              label: (
                <span>
                  <TableOutlined /> 表格
                </span>
              ),
              children: (
                <>
                  {filterBar}
                  <TestCaseCard cases={filteredCases} searchText={searchText} />
                </>
              ),
            },
            {
              key: "module",
              label: (
                <span>
                  <AppstoreOutlined /> 模块
                </span>
              ),
              children: (
                <>
                  {filterBar}
                  {/* Bulk delete bar */}
                  {editable && selectedCaseIds && selectedCaseIds.size > 0 && (
                    <div style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "10px 16px", background: "#FEF2F2", border: "1px solid #FECACA",
                      borderRadius: 8, marginBottom: 12,
                    }}>
                      <span style={{ fontSize: 13, color: "#DC2626", fontWeight: 500 }}>
                        已选 {selectedCaseIds.size} 条用例
                      </span>
                      <Popconfirm
                        title={`确认删除选中的 ${selectedCaseIds.size} 条用例？`}
                        onConfirm={onBatchDelete}
                        okText="确认删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <Button danger size="small">删除选中 ({selectedCaseIds.size})</Button>
                      </Popconfirm>
                    </div>
                  )}
                  {smokePanel}
                  {Array.from(groupByModule(filteredCases).entries()).map(
                    ([mod, cases]) => (
                      <div key={mod} className="module-group">
                        <div className="module-group-header">
                          <span className="module-group-name">{mod}</span>
                          <Tag>{cases.length} 条</Tag>
                          {["P0", "P1", "P2", "P3"].map((p) => {
                            const n = cases.filter((c) => c.priority === p).length;
                            return n > 0 ? (
                              <Tag key={p} color={PRIORITY_COLORS[p]} style={{ fontSize: 11 }}>
                                {p}:{n}
                              </Tag>
                            ) : null;
                          })}
                        </div>
                        <TestCaseCard
                          cases={cases}
                          searchText={searchText}
                          editable={editable}
                          selectedIds={selectedCaseIds}
                          onToggleSelect={onToggleSelect}
                          onEdit={onEditCase}
                          onDelete={onDeleteCase}
                        />
                        {editable && (
                          <div
                            onClick={() => onCreateCase?.(mod)}
                            style={{
                              padding: "10px 16px", borderTop: "1px dashed #E9D5FF",
                              display: "flex", alignItems: "center", gap: 8,
                              fontSize: 13, color: "#7C3AED", cursor: "pointer",
                              transition: "background 150ms",
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = "#FAF5FF")}
                            onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                          >
                            + 新增用例
                          </div>
                        )}
                      </div>
                    )
                  )}
                </>
              ),
            },
            {
              key: "markdown",
              label: (
                <span>
                  <ReadOutlined /> 文档
                </span>
              ),
              children: (
                <div className="markdown-document">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {markdown}
                  </ReactMarkdown>
                </div>
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}
