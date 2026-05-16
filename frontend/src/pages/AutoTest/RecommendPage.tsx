import {
  ExperimentOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Input,
  message,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createExecution,
  getRegressionRecommend,
  listSuites,
  RegressionRecommendItem,
  TestSuite,
} from "../../services/autoTest";

const { Title, Text, Paragraph } = Typography;

const PRIORITY_COLORS: Record<number, string> = {
  1: "#f5222d",
  2: "#fa8c16",
  3: "#1890ff",
  4: "#52c41a",
  5: "#999",
};

export default function RecommendPage() {
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<RegressionRecommendItem[]>([]);
  const [summary, setSummary] = useState("");
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [changedFiles, setChangedFiles] = useState<string[]>([]);
  const [diffContent, setDiffContent] = useState("");
  const [moduleNames, setModuleNames] = useState<string[]>([]);
  const [result, setResult] = useState<{
    totalRecommended: number;
    totalEstimatedDurationMs: number;
  } | null>(null);
  const [msg, msgContext] = message.useMessage();
  const navigate = useNavigate();

  useEffect(() => {
    listSuites().then(setSuites).catch(() => {});
  }, []);

  const handleRecommend = async () => {
    setLoading(true);
    try {
      const data = await getRegressionRecommend({
        changedFiles: changedFiles.length > 0 ? changedFiles : undefined,
        diffContent: diffContent || undefined,
        moduleNames: moduleNames.length > 0 ? moduleNames : undefined,
      });
      setRecommendations(data.recommendations);
      setSummary(data.summary);
      setResult({
        totalRecommended: data.totalRecommended,
        totalEstimatedDurationMs: data.totalEstimatedDurationMs,
      });
    } catch (e: unknown) {
      msg.error("推荐失败: " + (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (recommendations.length === 0) {
      msg.warning("无推荐用例可执行");
      return;
    }
    try {
      const caseIds = recommendations.map((r) => r.caseId);
      const firstCase = recommendations[0];
      const suite = suites.find((s) =>
        recommendations.some((r) => r.caseId === firstCase.caseId)
      );
      const exec = await createExecution({
        suiteId: suite?.id,
        caseIds,
        name: `回归推荐执行 ${new Date().toLocaleString("zh-CN")}`,
        triggeredBy: "regression_recommend",
      });
      const { startExecution } = await import("../../services/autoTest");
      await startExecution(exec.id);
      msg.success("执行已启动");
      navigate(`/auto-test/executions/${exec.id}`);
    } catch (e: unknown) {
      msg.error("启动执行失败: " + (e as Error).message);
    }
  };

  const columns = [
    {
      title: "用例名称",
      dataIndex: "caseTitle" as const,
      render: (title: string) => <Text strong>{title}</Text>,
    },
    {
      title: "优先级",
      dataIndex: "priority" as const,
      render: (p: number) => <Tag color={PRIORITY_COLORS[p] || "#999"}>P{p}</Tag>,
    },
    {
      title: "评分",
      dataIndex: "score" as const,
      render: (s: number) => {
        const percent = Math.round(s * 100);
        return (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 60, height: 6, background: "#f0f0f0", borderRadius: 3, overflow: "hidden",
            }}>
              <div style={{
                width: `${percent}%`, height: "100%",
                background: s > 0.7 ? "#52c41a" : s > 0.4 ? "#faad14" : "#ff4d4f",
                borderRadius: 3,
              }} />
            </div>
            <Text>{s.toFixed(2)}</Text>
          </div>
        );
      },
    },
    {
      title: "推荐理由",
      dataIndex: "reason" as const,
      ellipsis: true,
    },
    {
      title: "AI 分析",
      dataIndex: "aiReasoning" as const,
      ellipsis: true,
      render: (text: string) => text || "-",
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {msgContext}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>智能回归推荐</Title>
        <Text type="secondary">基于代码变更分析，AI 智能推荐需要执行的测试用例</Text>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Text strong>变更文件</Text>
            <Select
              mode="tags"
              placeholder="输入变更文件路径，按回车确认"
              style={{ width: "100%", marginTop: 4 }}
              value={changedFiles}
              onChange={(vals) => setChangedFiles(vals)}
            />
          </Col>
          <Col span={8}>
            <Text strong>影响模块</Text>
            <Select
              mode="tags"
              placeholder="输入模块名称，按回车确认"
              style={{ width: "100%", marginTop: 4 }}
              value={moduleNames}
              onChange={(vals) => setModuleNames(vals)}
            />
          </Col>
          <Col span={8} style={{ display: "flex", alignItems: "flex-end" }}>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleRecommend}
              loading={loading}
            >
              开始推荐
            </Button>
          </Col>
        </Row>
        <Row style={{ marginTop: 12 }}>
          <Col span={24}>
            <Text strong>Git Diff 内容</Text>
            <Input.TextArea
              rows={4}
              placeholder="粘贴 git diff 内容..."
              value={diffContent}
              onChange={(e) => setDiffContent(e.target.value)}
              style={{ marginTop: 4 }}
            />
          </Col>
        </Row>
      </Card>

      {result && (
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col>
              <Text strong>推荐结果：</Text>
              <Text>{summary}</Text>
            </Col>
            <Col>
              <Text type="secondary">
                预计总耗时: {Math.round((result.totalEstimatedDurationMs || 0) / 1000)}s
              </Text>
            </Col>
            <Col flex="auto" style={{ textAlign: "right" }}>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleExecute}
              >
                一键执行全部推荐用例
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      <Spin spinning={loading}>
        {recommendations.length > 0 ? (
          <Table
            columns={columns}
            dataSource={recommendations}
            rowKey="caseId"
            pagination={{ pageSize: 20 }}
          />
        ) : !loading && result ? (
          <Card><Text type="secondary">无推荐结果</Text></Card>
        ) : null}
      </Spin>
    </div>
  );
}
