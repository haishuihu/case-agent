import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Empty,
  InputNumber,
  List,
  message,
  Modal,
  Progress,
  Result,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  PlayCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";

import {
  ExecutionCreateRequest,
  TestCase,
  TestExecution,
  TestResult,
  TestSuite,
  createExecution,
  getExecution,
  listCases,
  listSuites,
  startExecution,
} from "../../services/autoTest";

const STATUS_COLORS: Record<string, string> = {
  pending: "default",
  running: "processing",
  completed: "success",
  failed: "error",
  cancelled: "warning",
};

const STATUS_TEXT: Record<string, string> = {
  pending: "等待中",
  running: "执行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const RESULT_COLORS: Record<string, string> = {
  pass: "success",
  fail: "error",
  blocked: "warning",
  skipped: "default",
  pending: "default",
};

const RESULT_TEXT: Record<string, string> = {
  pass: "通过",
  fail: "失败",
  blocked: "阻塞",
  skipped: "跳过",
  pending: "等待",
};

export function ExecutionListPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(true);
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedSuite, setSelectedSuite] = useState<string | null>(null);
  const [selectedCases, setSelectedCases] = useState<string[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [cases, setCases] = useState<TestCase[]>([]);
  const [starting, setStarting] = useState(false);

  const loadExecutions = async () => {
    setLoading(true);
    try {
      const { listExecutions } = await import("../../services/autoTest");
      const data = await listExecutions();
      setExecutions(data);
    } catch {
      messageApi.error("加载执行记录失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadExecutions();
  }, []);

  const handleOpenCreate = async () => {
    try {
      const [execData, suiteData] = await Promise.all([
        import("../../services/autoTest"),
        listSuites(),
      ]);
      setSuites(suiteData);
      if (suiteData.length > 0) {
        setSelectedSuite(suiteData[0].id);
      }
      setCreateModalOpen(true);
    } catch {
      messageApi.error("加载数据失败");
    }
  };

  useEffect(() => {
    if (selectedSuite) {
      listCases({ suiteId: selectedSuite }).then(setCases).catch(console.error);
    }
  }, [selectedSuite]);

  const handleCreateAndStart = async () => {
    if (!selectedSuite || selectedCases.length === 0) {
      messageApi.warning("请选择至少一个用例");
      return;
    }

    setStarting(true);
    try {
      const execData: ExecutionCreateRequest = {
        suiteId: selectedSuite,
        caseIds: selectedCases,
        triggeredBy: "user",
        triggerSource: "manual",
      };
      const execution = await createExecution(execData);
      await startExecution(execution.id);
      messageApi.success("执行已启动");
      setCreateModalOpen(false);
      await loadExecutions();
    } catch {
      messageApi.error("启动执行失败");
    } finally {
      setStarting(false);
    }
  };

  const columns = [
    {
      title: "执行名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: TestExecution) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{name}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {record.triggeredBy ? `触发人: ${record.triggeredBy}` : "手动触发"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || "default"} icon={status === "running" ? <ClockCircleOutlined /> : undefined}>
          {STATUS_TEXT[status] || status}
        </Tag>
      ),
    },
    {
      title: "进度",
      key: "progress",
      width: 150,
      render: (_: unknown, record: TestExecution) => (
        record.status === "running" || record.status === "completed" || record.status === "failed" ? (
          <Progress
            percent={record.passRate}
            size="small"
            status={record.status === "failed" ? "exception" : undefined}
            format={(p) => `${record.passedCount}/${record.totalCases}`}
          />
        ) : <Typography.Text type="secondary">-</Typography.Text>
      ),
    },
    {
      title: "通过率",
      key: "passRate",
      width: 100,
      render: (_: unknown, record: TestExecution) => (
        <Typography.Text
          style={{ color: record.passRate >= 80 ? "var(--color-success)" : "var(--color-danger)" }}
        >
          {record.passRate.toFixed(1)}%
        </Typography.Text>
      ),
    },
    {
      title: "耗时",
      dataIndex: "durationMs",
      key: "durationMs",
      width: 100,
      render: (ms?: number) => ms ? `${(ms / 1000).toFixed(1)}s` : "-",
    },
    {
      title: "时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 160,
      render: (createdAt: string) => (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {new Date(createdAt).toLocaleString("zh-CN")}
        </Typography.Text>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 80,
      render: (_: unknown, record: TestExecution) => (
        <Button
          type="link"
          onClick={() => navigate(`/auto-test/executions/${record.id}`)}
        >
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <>
      {contextHolder}
      <div className="auto-test-page">
        <div className="workbench-intro">
          <div className="workbench-intro-main">
            <Typography.Text className="workbench-intro-eyebrow">Execution</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>
              执行记录
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              查看和管理测试执行记录
            </Typography.Paragraph>
          </div>
          <div className="workbench-intro-side">
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleOpenCreate}>
              发起执行
            </Button>
          </div>
        </div>

        <Card>
          <Table
            dataSource={executions}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>

        <Modal
          title="发起测试执行"
          open={createModalOpen}
          onOk={handleCreateAndStart}
          onCancel={() => setCreateModalOpen(false)}
          okText={starting ? "启动中..." : "启动执行"}
          cancelText="取消"
          confirmLoading={starting}
          width={700}
        >
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <div>
              <Typography.Text strong>选择套件</Typography.Text>
              <Select
                style={{ width: "100%", marginTop: 8 }}
                placeholder="选择测试套件"
                value={selectedSuite}
                onChange={(value) => {
                  setSelectedSuite(value);
                  setSelectedCases([]);
                }}
                options={suites.map(s => ({ value: s.id, label: `${s.name} (${s.caseCount} 用例)` }))}
              />
            </div>

            {selectedSuite && cases.length > 0 && (
              <div>
                <Typography.Text strong>
                  选择用例 ({selectedCases.length}/{cases.length})
                </Typography.Text>
                <div style={{ marginTop: 8, maxHeight: 300, overflow: "auto" }}>
                  <Checkbox.Group
                    value={selectedCases}
                    onChange={(values) => setSelectedCases(values as string[])}
                    style={{ width: "100%" }}
                  >
                    <Space direction="vertical" style={{ width: "100%" }}>
                      {cases.map(c => (
                        <Checkbox key={c.id} value={c.id} style={{ width: "100%" }}>
                          <Space>
                            <span>{c.title}</span>
                            <Tag color={c.caseType === "api" ? "blue" : "purple"} style={{ fontSize: 10 }}>
                              {c.caseType}
                            </Tag>
                          </Space>
                        </Checkbox>
                      ))}
                    </Space>
                  </Checkbox.Group>
                </div>
              </div>
            )}

            <Button
              type="link"
              onClick={() => setSelectedCases(cases.map(c => c.id))}
            >
              全选
            </Button>
            <Button
              type="link"
              onClick={() => setSelectedCases([])}
            >
              清空
            </Button>
          </Space>
        </Modal>
      </div>
    </>
  );
}

// Checkbox components are now imported from antd directly

export function ExecutionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(true);
  const [execution, setExecution] = useState<(TestExecution & { results: TestResult[] }) | null>(null);

  const loadExecution = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await getExecution(id);
      setExecution(data);
    } catch {
      messageApi.error("加载执行详情失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadExecution();
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!execution) {
    return (
      <Result
        status="404"
        title="执行记录不存在"
        extra={<Button onClick={() => navigate("/auto-test/executions")}>返回列表</Button>}
      />
    );
  }

  const resultColumns = [
    {
      title: "用例",
      dataIndex: "caseTitle",
      key: "caseTitle",
      render: (title: string, record: TestResult) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{title || record.caseId}</Typography.Text>
          {record.caseType && (
            <Tag color="blue" style={{ fontSize: 10 }}>{record.caseType}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: "结果",
      dataIndex: "result",
      key: "result",
      width: 80,
      render: (result: string) => (
        <Tag color={RESULT_COLORS[result] || "default"} icon={
          result === "pass" ? <CheckCircleFilled /> :
          result === "fail" ? <CloseCircleFilled /> : undefined
        }>
          {RESULT_TEXT[result] || result}
        </Tag>
      ),
    },
    {
      title: "响应码",
      dataIndex: "responseStatus",
      key: "responseStatus",
      width: 80,
      render: (status?: number) => status ? (
        <Typography.Text type={status >= 400 ? "danger" : undefined}>{status}</Typography.Text>
      ) : "-",
    },
    {
      title: "耗时",
      dataIndex: "durationMs",
      key: "durationMs",
      width: 80,
      render: (ms?: number) => ms ? `${(ms / 1000).toFixed(2)}s` : "-",
    },
    {
      title: "错误信息",
      dataIndex: "errorMessage",
      key: "errorMessage",
      render: (msg?: string) => msg ? (
        <Typography.Text type="danger" ellipsis={{ tooltip: msg }} style={{ maxWidth: 300 }}>
          {msg}
        </Typography.Text>
      ) : "-",
    },
    {
      title: "AI 分析",
      dataIndex: "aiAnalysis",
      key: "aiAnalysis",
      render: (analysis?: string) => analysis ? (
        <Typography.Text type="secondary" ellipsis={{ tooltip: analysis }} style={{ maxWidth: 200 }}>
          {analysis}
        </Typography.Text>
      ) : "-",
    },
  ];

  return (
    <>
      {contextHolder}
      <div className="auto-test-page">
        <div className="workbench-intro">
          <div className="workbench-intro-main">
            <Typography.Text className="workbench-intro-eyebrow">Execution Detail</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {execution.name}
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              执行时间: {new Date(execution.createdAt).toLocaleString("zh-CN")}
            </Typography.Paragraph>
          </div>
          <div className="workbench-intro-side">
            <Tag color={STATUS_COLORS[execution.status]} style={{ fontSize: 14, padding: "4px 12px" }}>
              {STATUS_TEXT[execution.status]}
            </Tag>
          </div>
        </div>

        {/* Stats */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={6}>
            <Card className="stat-card" size="small">
              <Statistic
                title="总用例"
                value={execution.totalCases}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card className="stat-card" size="small">
              <Statistic
                title="通过"
                value={execution.passedCount}
                valueStyle={{ color: "var(--color-success)" }}
                prefix={<CheckCircleFilled />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card className="stat-card" size="small">
              <Statistic
                title="失败"
                value={execution.failedCount}
                valueStyle={{ color: "var(--color-danger)" }}
                prefix={<CloseCircleFilled />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card className="stat-card" size="small">
              <Statistic
                title="通过率"
                value={execution.passRate}
                suffix="%"
                valueStyle={{ color: execution.passRate >= 80 ? "var(--color-success)" : "var(--color-danger)" }}
              />
            </Card>
          </Col>
        </Row>

        {/* Results Table */}
        <Card title="执行详情">
          <Table
            dataSource={execution.results}
            columns={resultColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: "暂无结果数据" }}
          />
        </Card>

        {/* AI Summary */}
        {execution.aiSummary && (
          <Card title="AI 分析摘要" style={{ marginTop: 16 }}>
            <Typography.Paragraph>{execution.aiSummary}</Typography.Paragraph>
            {execution.aiRecommendations && execution.aiRecommendations.length > 0 && (
              <>
                <Typography.Title level={5}>改进建议</Typography.Title>
                <List
                  size="small"
                  dataSource={execution.aiRecommendations}
                  renderItem={(item) => <List.Item>{item}</List.Item>}
                />
              </>
            )}
          </Card>
        )}
      </div>
    </>
  );
}
