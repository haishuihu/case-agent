import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Progress,
  Row,
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
  ExperimentOutlined,
  PlayCircleOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  ScheduleOutlined,
  FileTextOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import {
  DashboardStats,
  ExecutionTrend,
  FailureDistribution,
  RecentExecution,
  getDashboardStats,
  getExecutionTrends,
  getFailureDistribution,
  getRecentExecutions,
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

export function AutoTestDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentExecutions, setRecentExecutions] = useState<RecentExecution[]>([]);
  const [trends, setTrends] = useState<ExecutionTrend[]>([]);
  const [failures, setFailures] = useState<FailureDistribution[]>([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsData, recentData, trendsData, failuresData] = await Promise.all([
        getDashboardStats(),
        getRecentExecutions(5),
        getExecutionTrends(7),
        getFailureDistribution(10),
      ]);
      setStats(statsData);
      setRecentExecutions(recentData);
      setTrends(trendsData);
      setFailures(failuresData);
    } catch (e) {
      console.error("Failed to load dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  const recentColumns = [
    {
      title: "执行名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: RecentExecution) => (
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
        <Tag color={STATUS_COLORS[status] || "default"}>
          {STATUS_TEXT[status] || status}
        </Tag>
      ),
    },
    {
      title: "通过率",
      key: "passRate",
      width: 120,
      render: (_: unknown, record: RecentExecution) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong style={{ color: record.passRate >= 80 ? "var(--color-success)" : "var(--color-danger)" }}>
            {record.passRate.toFixed(1)}%
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {record.passedCount}/{record.totalCases}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "执行时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 160,
      render: (createdAt: string) => (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {new Date(createdAt).toLocaleString("zh-CN")}
        </Typography.Text>
      ),
    },
  ];

  return (
    <div className="auto-test-dashboard">
      {/* Header */}
      <div className="workbench-intro">
        <div className="workbench-intro-main">
          <Typography.Text className="workbench-intro-eyebrow">Auto Testing</Typography.Text>
          <Typography.Title level={4} style={{ margin: 0 }}>
            测试自动化工作台
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            智能回归测试、自动化执行、AI 驱动的测试推荐
          </Typography.Paragraph>
        </div>
        <div className="workbench-intro-side">
          <Tag color="blue" icon={<RocketOutlined />}>AI 驱动</Tag>
          <Tag color="purple" icon={<PlayCircleOutlined />}>自动执行</Tag>
          <Tag color="green" icon={<CheckCircleFilled />}>持续集成</Tag>
        </div>
      </div>

      {/* Quick Navigation */}
      <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6} md={3}>
          <Card hoverable size="small" onClick={() => navigate("/auto-test/suites")} style={{ textAlign: "center", cursor: "pointer" }}>
            <ApartmentOutlined style={{ fontSize: 22, color: "var(--color-primary)", marginBottom: 6 }} />
            <div><Typography.Text strong style={{ fontSize: 13 }}>测试套件</Typography.Text></div>
            <div><Typography.Text type="secondary" style={{ fontSize: 11 }}>{stats?.totalSuites ?? 0} 个</Typography.Text></div>
          </Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card hoverable size="small" onClick={() => navigate("/auto-test/cases")} style={{ textAlign: "center", cursor: "pointer" }}>
            <FileTextOutlined style={{ fontSize: 22, color: "var(--color-success)", marginBottom: 6 }} />
            <div><Typography.Text strong style={{ fontSize: 13 }}>测试用例</Typography.Text></div>
            <div><Typography.Text type="secondary" style={{ fontSize: 11 }}>{stats?.totalCases ?? 0} 个</Typography.Text></div>
          </Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card hoverable size="small" onClick={() => navigate("/auto-test/plans")} style={{ textAlign: "center", cursor: "pointer" }}>
            <ScheduleOutlined style={{ fontSize: 22, color: "var(--color-warning)", marginBottom: 6 }} />
            <div><Typography.Text strong style={{ fontSize: 13 }}>测试计划</Typography.Text></div>
            <div><Typography.Text type="secondary" style={{ fontSize: 11 }}>{stats?.totalPlans ?? 0} 个</Typography.Text></div>
          </Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card hoverable size="small" onClick={() => navigate("/auto-test/executions")} style={{ textAlign: "center", cursor: "pointer" }}>
            <PlayCircleOutlined style={{ fontSize: 22, color: "var(--color-info)", marginBottom: 6 }} />
            <div><Typography.Text strong style={{ fontSize: 13 }}>执行记录</Typography.Text></div>
            <div><Typography.Text type="secondary" style={{ fontSize: 11 }}>{stats?.totalExecutions ?? 0} 次</Typography.Text></div>
          </Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card hoverable size="small" onClick={() => navigate("/auto-test/recommend")} style={{ textAlign: "center", cursor: "pointer" }}>
            <ThunderboltOutlined style={{ fontSize: 22, color: "#722ed1", marginBottom: 6 }} />
            <div><Typography.Text strong style={{ fontSize: 13 }}>回归推荐</Typography.Text></div>
            <div><Typography.Text type="secondary" style={{ fontSize: 11 }}>AI 智能</Typography.Text></div>
          </Card>
        </Col>
      </Row>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card className="stat-card" size="small">
            <Statistic
              title="待执行"
              value={stats?.pendingCount ?? 0}
              prefix={<ExperimentOutlined style={{ color: "var(--color-info)" }} />}
              valueStyle={{ color: "var(--color-info)" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="stat-card" size="small">
            <Statistic
              title="执行中"
              value={stats?.runningCount ?? 0}
              prefix={<RocketOutlined style={{ color: "var(--color-primary)" }} />}
              valueStyle={{ color: "var(--color-primary)" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="stat-card accent" size="small">
            <Statistic
              title="今日通过"
              value={stats?.todayPassCount ?? 0}
              suffix={`/ ${stats?.todayTotalCases ?? 0}`}
              prefix={<CheckCircleFilled style={{ color: "var(--color-success)" }} />}
              valueStyle={{ color: "var(--color-success)" }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="stat-card warm" size="small">
            <Statistic
              title="今日失败"
              value={stats?.todayFailCount ?? 0}
              prefix={<CloseCircleFilled style={{ color: "var(--color-danger)" }} />}
              valueStyle={{ color: "var(--color-danger)" }}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card className="quick-action-card">
            <Row gutter={24} align="middle">
              <Col flex="auto">
                <Space direction="vertical" size={4}>
                  <Typography.Title level={5} style={{ margin: 0 }}>
                    智能回归推荐
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    基于代码变更分析，AI 智能推荐需要执行的测试用例
                  </Typography.Text>
                </Space>
              </Col>
              <Col>
                <Space>
                  <Button onClick={() => navigate("/auto-test/recommend")}>
                    查看详情
                  </Button>
                  <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => navigate("/auto-test/recommend")}>
                    一键执行
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Row gutter={[16, 16]}>
        {/* Recent Executions */}
        <Col xs={24} lg={16}>
          <Card
            title="最近执行记录"
            extra={
              <Button type="link" onClick={() => navigate("/auto-test/executions")}>
                查看全部
              </Button>
            }
          >
            <Table
              dataSource={recentExecutions}
              columns={recentColumns}
              rowKey="id"
              pagination={false}
              size="small"
              locale={{ emptyText: "暂无执行记录" }}
              onRow={(record) => ({
                style: { cursor: "pointer" },
                onClick: () => navigate(`/auto-test/executions/${record.id}`),
              })}
            />
          </Card>
        </Col>

        {/* Summary Stats */}
        <Col xs={24} lg={8}>
          <Card title="测试概览">
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <div className="summary-item">
                <Typography.Text type="secondary">测试套件</Typography.Text>
                <Typography.Text strong>{stats?.totalSuites ?? 0}</Typography.Text>
              </div>
              <div className="summary-item">
                <Typography.Text type="secondary">测试用例</Typography.Text>
                <Typography.Text strong>{stats?.totalCases ?? 0}</Typography.Text>
              </div>
              <div className="summary-item">
                <Typography.Text type="secondary">测试计划</Typography.Text>
                <Typography.Text strong>{stats?.totalPlans ?? 0}</Typography.Text>
              </div>
              <div className="summary-item">
                <Typography.Text type="secondary">执行记录</Typography.Text>
                <Typography.Text strong>{stats?.totalExecutions ?? 0}</Typography.Text>
              </div>
              <Divider />
              <div className="pass-rate-item">
                <Typography.Text type="secondary">今日通过率</Typography.Text>
                <Progress
                  percent={stats?.todayPassRate ?? 0}
                  size="small"
                  status={(stats?.todayPassRate ?? 0) >= 80 ? "success" : "exception"}
                  strokeColor={(stats?.todayPassRate ?? 0) >= 80 ? "var(--color-success)" : "var(--color-danger)"}
                />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Trend Chart */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="执行趋势 (7天)">
            {trends.length > 0 ? (
              <Row gutter={[16, 16]}>
                {trends.map((trend) => (
                  <Col xs={24} sm={12} md={8} lg={4} key={trend.date}>
                    <div className="trend-item">
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {trend.date.slice(5)}
                      </Typography.Text>
                      <div className="trend-stats">
                        <Typography.Text style={{ color: "var(--color-success)" }}>
                          {trend.passed}
                        </Typography.Text>
                        <Typography.Text style={{ color: "var(--color-danger)" }}>
                          {trend.failed}
                        </Typography.Text>
                      </div>
                      <Progress
                        percent={trend.passRate}
                        size="small"
                        showInfo={false}
                        strokeColor="var(--color-success)"
                      />
                    </div>
                  </Col>
                ))}
              </Row>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon"><RocketOutlined /></div>
                <div className="empty-state-text">暂无趋势数据</div>
              </div>
            )}
          </Card>
        </Col>

        {/* Failure Distribution */}
        <Col xs={24} lg={12}>
          <Card title="失败分布 (7天)">
            {failures.length > 0 ? (
              <div>
                {failures.map((f) => (
                  <div key={f.module} style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <Typography.Text>{f.module}</Typography.Text>
                      <Typography.Text type="secondary">
                        {f.count} 次 ({f.percentage.toFixed(1)}%)
                      </Typography.Text>
                    </div>
                    <Progress
                      percent={f.percentage}
                      size="small"
                      showInfo={false}
                      strokeColor="#ff4d4f"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon"><CheckCircleFilled style={{ color: "var(--color-success)" }} /></div>
                <div className="empty-state-text">暂无失败记录</div>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: "var(--border-light)", margin: "8px 0" }} />;
}
