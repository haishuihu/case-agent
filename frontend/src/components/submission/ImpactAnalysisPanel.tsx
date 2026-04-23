import { useState, useCallback } from "react";
import {
  Alert,
  Button,
  Card,
  Divider,
  Empty,
  List,
  Progress,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  Collapse,
  Tooltip,
} from "antd";
import {
  BarChartOutlined,
  CheckCircleFilled,
  InfoCircleFilled,
  RadarChartOutlined,
  WarningFilled,
  NodeCollapseOutlined,
  ApiOutlined,
  BranchesOutlined,
} from "@ant-design/icons";
import type { ImpactAnalysis, VisualizationData } from "../../services/impact";
import { getImpactVisualization } from "../../services/impact";
import { DiffInput } from "./DiffInput";
import { DependencyGraph } from "../visualization/DependencyGraph";

const RISK_META: Record<string, { label: string; color: string }> = {
  high: { label: "高风险", color: "red" },
  medium: { label: "中风险", color: "orange" },
  low: { label: "低风险", color: "default" },
};

const CONFIDENCE_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  high: { label: "高", color: "success", icon: <CheckCircleFilled /> },
  medium: { label: "中", color: "warning", icon: <WarningFilled /> },
  low: { label: "低", color: "default", icon: <InfoCircleFilled /> },
};

interface ImpactAnalysisPanelProps {
  submissionId: string;
  impactAnalysis: ImpactAnalysis | null;
  loading?: boolean;
  analyzing?: boolean;
  onAnalyze: (gitDiff: string) => Promise<void>;
  defaultDiff?: string;
}

export function ImpactAnalysisPanel({
  submissionId,
  impactAnalysis,
  loading,
  analyzing,
  onAnalyze,
  defaultDiff,
}: ImpactAnalysisPanelProps) {
  const [diffValue, setDiffValue] = useState("");
  const [error, setError] = useState<string>();

  const handleAnalyze = useCallback(async () => {
    if (!diffValue.trim()) {
      setError("请先粘贴 Git Diff 内容");
      return;
    }
    setError(undefined);
    await onAnalyze(diffValue);
  }, [diffValue, onAnalyze]);

  if (loading) {
    return (
      <Card className="impact-panel">
        <div style={{ textAlign: "center", padding: 40 }}>
          <Spin />
          <Typography.Text type="secondary" style={{ display: "block", marginTop: 16 }}>
            加载影响分析结果...
          </Typography.Text>
        </div>
      </Card>
    );
  }

  if (!impactAnalysis) {
    return (
      <Card className="impact-panel">
        <div className="impact-panel-header">
          <Typography.Title level={5} style={{ margin: 0 }}>
            影响分析
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            基于代码变更智能分析影响范围
          </Typography.Text>
        </div>
        <Divider style={{ margin: "12px 0" }} />
        <Empty
          image={<RadarChartOutlined style={{ fontSize: 48, color: "var(--border-card)" }} />}
          description={
            <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
              暂无影响分析结果
            </Typography.Paragraph>
          }
        >
          <Typography.Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 16, textAlign: "center" }}>
            粘贴 Git Diff 内容，系统将自动分析变更影响并推荐回归测试范围
          </Typography.Paragraph>
          <DiffInput
            value={diffValue}
            onChange={setDiffValue}
            onAnalyze={handleAnalyze}
            loading={analyzing}
            error={error}
            defaultDiff={defaultDiff}
          />
        </Empty>
      </Card>
    );
  }

  const confidenceMeta = CONFIDENCE_META[impactAnalysis.confidenceLevel] ?? CONFIDENCE_META.low;

  return (
    <Card className="impact-panel">
      <div className="impact-panel-header">
        <div className="impact-panel-title">
          <Typography.Title level={5} style={{ margin: 0 }}>
            影响分析
          </Typography.Title>
          <Space size={4}>
            {confidenceMeta.icon}
            <Typography.Text style={{ fontSize: 12 }}>置信度: {confidenceMeta.label}</Typography.Text>
          </Space>
        </div>
        <Button
          icon={<RadarChartOutlined />}
          onClick={() => {
            setDiffValue("");
          }}
          loading={analyzing}
        >
          重新分析
        </Button>
      </div>

      <Divider style={{ margin: "12px 0" }} />

      {/* 变更统计 */}
      <div className="impact-stats">
        <Statistic
          title="变更文件"
          value={impactAnalysis.changedFiles.length}
          prefix={<BarChartOutlined />}
        />
        <Statistic
          title="新增行"
          value={impactAnalysis.addedLines}
          valueStyle={{ color: "var(--color-success)" }}
        />
        <Statistic
          title="删除行"
          value={impactAnalysis.deletedLines}
          valueStyle={{ color: "var(--color-danger)" }}
        />
        <Statistic
          title="受影响模块"
          value={impactAnalysis.impactedModules.length}
          valueStyle={{ color: impactAnalysis.impactedModules.some((m) => m.riskLevel === "high") ? "var(--color-danger)" : undefined }}
        />
      </div>

      {/* 变更文件列表 */}
      {impactAnalysis.changedFiles.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            变更文件
          </Typography.Text>
          <List
            size="small"
            dataSource={impactAnalysis.changedFiles.slice(0, 5)}
            renderItem={(file) => (
              <List.Item style={{ padding: "4px 0" }}>
                <Space>
                  <Tag color={file.status === "added" ? "green" : file.status === "deleted" ? "red" : "blue"} style={{ marginRight: 0 }}>
                    {file.status === "added" ? "+" : file.status === "deleted" ? "-" : "~"}
                  </Tag>
                  <Typography.Text style={{ fontSize: 12 }}>{file.filename}</Typography.Text>
                  {file.additions > 0 && (
                    <Typography.Text type="success" style={{ fontSize: 11 }}>
                      +{file.additions}
                    </Typography.Text>
                  )}
                  {file.deletions > 0 && (
                    <Typography.Text type="danger" style={{ fontSize: 11 }}>
                      -{file.deletions}
                    </Typography.Text>
                  )}
                </Space>
              </List.Item>
            )}
            style={{ marginTop: 4 }}
          />
          {impactAnalysis.changedFiles.length > 5 && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              ...还有 {impactAnalysis.changedFiles.length - 5} 个文件
            </Typography.Text>
          )}
        </div>
      )}

      {/* 影响摘要 */}
      {impactAnalysis.summary && (
        <Alert
          type="info"
          showIcon={false}
          message={impactAnalysis.summary}
          style={{ marginTop: 16, background: "rgba(0, 113, 227, 0.05)", borderColor: "rgba(0, 113, 227, 0.2)" }}
        />
      )}

      {/* 低置信度警告 */}
      {impactAnalysis.confidenceLevel === "low" && (
        <Alert
          type="warning"
          showIcon
          icon={<InfoCircleFilled />}
          message="分析置信度较低，建议人工复核影响范围的准确性"
          style={{ marginTop: 12 }}
        />
      )}

      {/* 受影响模块 */}
      {impactAnalysis.impactedModules.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            受影响模块
          </Typography.Text>
          <div className="module-list" style={{ marginTop: 8 }}>
            {impactAnalysis.impactedModules.map((m) => {
              const meta = RISK_META[m.riskLevel] ?? RISK_META.low;
              return (
                <Card
                  key={m.id}
                  size="small"
                  className={`module-card ${m.riskLevel}-risk`}
                  style={{ marginBottom: 8 }}
                >
                  <div className="module-card-header">
                    <Space>
                      <Typography.Text strong>{m.moduleName}</Typography.Text>
                      <Tag color={meta.color}>{meta.label}</Tag>
                      {m.moduleType === "direct" && (
                        <Tag color="blue" style={{ marginRight: 0 }}>直接影响</Tag>
                      )}
                      {m.moduleType === "indirect" && (
                        <Tag color="purple" style={{ marginRight: 0 }}>间接影响</Tag>
                      )}
                      {m.moduleType === "api" && (
                        <Tag color="cyan" style={{ marginRight: 0 }}>API变更</Tag>
                      )}
                    </Space>
                  </div>
                  {m.impactDescription && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {m.impactDescription}
                    </Typography.Text>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* 风险点 */}
      {impactAnalysis.riskPoints.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            风险提示
          </Typography.Text>
          {impactAnalysis.riskPoints.map((point, i) => (
            <Alert
              key={i}
              type="warning"
              showIcon
              icon={<WarningFilled />}
              message={point}
              style={{ marginTop: 8 }}
            />
          ))}
        </div>
      )}

      {/* API 破坏性变更 */}
      {impactAnalysis.apiBreakingChanges.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            API 破坏性变更
          </Typography.Text>
          {impactAnalysis.apiBreakingChanges.map((api, i) => (
            <Alert
              key={i}
              type="error"
              showIcon
              message={api}
              style={{ marginTop: 8 }}
            />
          ))}
        </div>
      )}

      {/* 可视化依赖关系图 */}
      <VisualizationSection analysisId={impactAnalysis.id} />

      {/* 分析时间 */}
      <Typography.Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 12 }}>
        分析时间: {new Date(impactAnalysis.createdAt).toLocaleString("zh-CN")}
      </Typography.Text>
    </Card>
  );
}

// ── 可视化模块关系图 ───────────────────────────────────────

function VisualizationSection({ analysisId }: { analysisId: string }) {
  const [vizData, setVizData] = useState<VisualizationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(false);
  const [showD3, setShowD3] = useState(true);

  const loadVisualization = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getImpactVisualization(analysisId);
      setVizData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载可视化数据失败");
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (keys: string[]) => {
    if (keys.includes("viz") && !vizData && !loading) {
      await loadVisualization();
    }
    setActive(keys.includes("viz"));
  };

  const RISK_COLORS: Record<string, string> = {
    high: "#ff4d4f",
    medium: "#faad14",
    low: "#52c41a",
  };

  const TYPE_COLORS: Record<string, string> = {
    direct: "#1890ff",
    indirect: "#722ed1",
    api: "#13c2c2",
  };

  return (
    <Collapse
      items={[{
        key: "viz",
        label: (
          <Space>
            <NodeCollapseOutlined />
            <span style={{ fontSize: 13 }}>模块依赖关系图</span>
            {vizData && (
              <Tag color="blue">{vizData.totalNodes} 节点 / {vizData.totalEdges} 边</Tag>
            )}
          </Space>
        ),
        extra: vizData ? (
          <Space size={4}>
            <Button
              type="text"
              size="small"
              style={{ fontSize: 11 }}
              onClick={(e) => { e.stopPropagation(); setShowD3(!showD3); }}
            >
              {showD3 ? "切换表格" : "切换图谱"}
            </Button>
          </Space>
        ) : null,
        children: (
          <div>
            {loading && (
              <div style={{ textAlign: "center", padding: 16 }}>
                <Spin size="small" />
                <Typography.Text type="secondary" style={{ marginLeft: 8 }}>加载中...</Typography.Text>
              </div>
            )}
            {error && <Alert type="error" message={error} style={{ marginTop: 8 }} />}
            {vizData && showD3 && vizData.nodes.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                {/* D3 交互式图谱 */}
                <DependencyGraph data={vizData} width={580} height={360} />
              </div>
            )}
            {vizData && !showD3 && (
              <>
                {/* 表格视图：模块节点 */}
                <Alert
                  type="info"
                  message={vizData.summary}
                  style={{ marginBottom: 12 }}
                />
                <Typography.Text strong style={{ fontSize: 12 }}>模块节点</Typography.Text>
                <List
                  size="small"
                  dataSource={vizData.nodes}
                  renderItem={(node) => (
                    <List.Item style={{ padding: "4px 0" }}>
                      <Space>
                        <div style={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          backgroundColor: node.isDirect ? RISK_COLORS[node.riskLevel] ?? "#faad14" : TYPE_COLORS[node.moduleType] ?? "#722ed1",
                          flexShrink: 0,
                        }} />
                        <Typography.Text strong={node.isDirect} style={{ fontSize: 12 }}>
                          {node.name}
                        </Typography.Text>
                        <Tag color={node.isDirect ? "red" : "purple"} style={{ marginRight: 0, fontSize: 11 }}>
                          {node.isDirect ? "变更" : node.moduleType}
                        </Tag>
                        <Tag color={RISK_COLORS[node.riskLevel] ?? "default"} style={{ marginRight: 0, fontSize: 11 }}>
                          {node.riskLevel === "high" ? "高风险" : node.riskLevel === "medium" ? "中风险" : "低风险"}
                        </Tag>
                      </Space>
                    </List.Item>
                  )}
                  style={{ marginTop: 4, marginBottom: 12 }}
                />
                {/* 表格视图：调用关系 */}
                {vizData.edges.length > 0 && (
                  <>
                    <Typography.Text strong style={{ fontSize: 12 }}>调用关系</Typography.Text>
                    <List
                      size="small"
                      dataSource={vizData.edges.slice(0, 10)}
                      renderItem={(edge) => {
                        const sourceNode = vizData.nodes.find((n) => n.id === edge.source);
                        const targetNode = vizData.nodes.find((n) => n.id === edge.target);
                        return (
                          <List.Item style={{ padding: "2px 0" }}>
                            <Space style={{ fontSize: 12 }}>
                              <BranchesOutlined style={{ color: "#8c8c8c" }} />
                              <Typography.Text>{sourceNode?.name ?? edge.source}</Typography.Text>
                              <ApiOutlined style={{ color: "#8c8c8c" }} />
                              <Typography.Text>{targetNode?.name ?? edge.target}</Typography.Text>
                              <Tag style={{ marginRight: 0, fontSize: 11 }}>{edge.relationType}</Tag>
                            </Space>
                          </List.Item>
                        );
                      }}
                      style={{ marginTop: 4 }}
                    />
                  </>
                )}
              </>
            )}
            {vizData && vizData.nodes.length === 0 && (
              <Empty description="暂无可视化数据" />
            )}
          </div>
        ),
      }]}
      onChange={handleToggle}
      style={{ marginTop: 12 }}
    />
  );
}
