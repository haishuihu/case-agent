import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  message,
  Pagination,
  Popconfirm,
  Segmented,
  Select,
  Skeleton,
  Space,
  Tag,
  Typography,
  Tooltip,
  Modal,
  Descriptions,
} from "antd";
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  BugOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import {
  listDefects,
  deleteDefect,
  updateDefect,
  createDefect,
  createDefectFromExecution,
  type Defect,
  type DefectStatus,
  type DefectSeverity,
  type DefectPriority,
  type CreateDefectPayload,
} from "../services/defect";

const STATUS_COLORS: Record<DefectStatus, string> = {
  open: "error",
  in_progress: "processing",
  resolved: "success",
  closed: "default",
};

const STATUS_LABELS: Record<DefectStatus, string> = {
  open: "待处理",
  in_progress: "处理中",
  resolved: "已解决",
  closed: "已关闭",
};

const SEVERITY_COLORS: Record<DefectSeverity, string> = {
  critical: "red",
  high: "orange",
  medium: "gold",
  low: "blue",
};

const SEVERITY_LABELS: Record<DefectSeverity, string> = {
  critical: "致命",
  high: "高",
  medium: "中",
  low: "低",
};

const STATUS_OPTIONS: { label: string; value: string }[] = [
  { label: "全部", value: "all" },
  { label: "待处理", value: "open" },
  { label: "处理中", value: "in_progress" },
  { label: "已解决", value: "resolved" },
  { label: "已关闭", value: "closed" },
];

const SEVERITY_OPTIONS: { label: string; value: string }[] = [
  { label: "全部严重程度", value: "all" },
  { label: "致命", value: "critical" },
  { label: "高", value: "high" },
  { label: "中", value: "medium" },
  { label: "低", value: "low" },
];

const STATUS_TRANSITIONS: Record<DefectStatus, DefectStatus[]> = {
  open: ["in_progress"],
  in_progress: ["resolved"],
  resolved: ["closed", "open"],
  closed: [],
};

export function DefectListPage() {
  const [defects, setDefects] = useState<Defect[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedDefect, setSelectedDefect] = useState<Defect | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createForm] = Form.useForm<CreateDefectPayload>();
  const [fromExecModalOpen, setFromExecModalOpen] = useState(false);
  const [fromExecForm] = Form.useForm();
  const [fromExecSubmitting, setFromExecSubmitting] = useState(false);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Parameters<typeof listDefects>[0] = {
        page,
        pageSize: PAGE_SIZE,
      };
      if (statusFilter !== "all") {
        params.status = statusFilter as DefectStatus;
      }
      if (severityFilter !== "all") {
        params.severity = severityFilter as DefectSeverity;
      }
      const result = await listDefects(params);
      setDefects(result.items);
      setTotal(result.total);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载缺陷列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, severityFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await deleteDefect(id);
      message.success("缺陷已删除");
      setDefects((prev) => prev.filter((d) => d.id !== id));
    } catch {
      message.error("删除失败");
    }
  };

  const handleStatusChange = async (defectId: string, newStatus: DefectStatus) => {
    try {
      const updated = await updateDefect(defectId, { status: newStatus });
      setDefects((prev) => prev.map((d) => (d.id === defectId ? updated : d)));
      message.success(`已更新状态为"${STATUS_LABELS[newStatus]}"`);
    } catch {
      message.error("更新状态失败");
    }
  };

  const handleCreate = async (values: CreateDefectPayload) => {
    setCreateSubmitting(true);
    try {
      const newDefect = await createDefect(values);
      message.success("缺陷已创建");
      setCreateModalOpen(false);
      createForm.resetFields();
      setPage(1);
      setRefreshKey((k) => k + 1);
    } catch {
      message.error("创建缺陷失败");
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleCreateFromExecution = async (values: Record<string, unknown>) => {
    setFromExecSubmitting(true);
    try {
      const executionId = values.executionId as string;
      const additionalInfo: Partial<CreateDefectPayload> = {
        title: values.title as string,
        description: values.description as string,
        severity: values.severity as CreateDefectPayload["severity"],
        priority: values.priority as CreateDefectPayload["priority"],
        creator: values.creator as string,
      };
      await createDefectFromExecution({ executionId, ...additionalInfo });
      message.success("缺陷已从执行记录创建");
      setFromExecModalOpen(false);
      fromExecForm.resetFields();
      void handleRefresh();
    } catch {
      message.error("从执行记录创建缺陷失败");
    } finally {
      setFromExecSubmitting(false);
    }
  };

  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
    if (selectedDefect) setSelectedDefect(null);
  };

  const stats = {
    total,
    open: defects.filter((d) => d.status === "open").length,
    inProgress: defects.filter((d) => d.status === "in_progress").length,
    resolved: defects.filter((d) => d.status === "resolved").length,
    critical: defects.filter((d) => d.severity === "critical" && d.status !== "closed").length,
  };

  return (
    <div className="defect-list-page">
      <div className="defect-list-header">
        <Typography.Title level={4} style={{ margin: 0 }}>
          缺陷管理
        </Typography.Title>
        <Space>
          <Tooltip title="刷新">
            <Button icon={<ReloadOutlined />} onClick={() => void handleRefresh()} />
          </Tooltip>
          <Button icon={<BugOutlined />} onClick={() => setFromExecModalOpen(true)}>
            从执行创建
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            新建缺陷
          </Button>
        </Space>
      </div>

      {/* 统计概览 */}
      <div className="defect-stats-bar" style={{ marginBottom: 16 }}>
        <Card size="small" bodyStyle={{ padding: "12px 16px" }}>
          <Space wrap>
            <Tag icon={<BugOutlined />}>{stats.total} 缺陷总数</Tag>
            <Tag color="error">{stats.open} 待处理</Tag>
            <Tag color="processing">{stats.inProgress} 处理中</Tag>
            <Tag color="success">{stats.resolved} 已解决</Tag>
            {stats.critical > 0 && (
              <Tag color="red" icon={<BugOutlined />}>
                {stats.critical} 致命缺陷
              </Tag>
            )}
          </Space>
        </Card>
      </div>

      {/* 状态 + 严重程度筛选 */}
      <div className="defect-filter-bar" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Segmented
            value={statusFilter}
            onChange={(val) => {
              setStatusFilter(String(val));
              setPage(1);
            }}
            options={STATUS_OPTIONS}
          />
          <Select
            value={severityFilter}
            style={{ width: 140 }}
            onChange={(val) => {
              setSeverityFilter(val);
              setPage(1);
            }}
            options={SEVERITY_OPTIONS}
            placeholder="严重程度"
          />
        </Space>
      </div>

      {/* 列表 */}
      {loading && defects.length === 0 ? (
        <div style={{ padding: 40 }}>
          <Skeleton active />
        </div>
      ) : defects.length === 0 ? (
        <Empty
          description={statusFilter !== "all" ? "该状态下暂无缺陷记录" : "暂无缺陷记录"}
          style={{ padding: 80 }}
        />
      ) : (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          {defects.map((defect) => (
            <Card
              key={defect.id}
              size="small"
              hoverable
              onClick={() => setSelectedDefect(defect)}
              style={{ cursor: "pointer" }}
              title={
                <Space>
                  <BugOutlined style={{ color: "var(--color-danger)" }} />
                  <Typography.Text strong style={{ fontSize: 14 }}>
                    {defect.title}
                  </Typography.Text>
                  <Tag color={SEVERITY_COLORS[defect.severity]}>
                    {SEVERITY_LABELS[defect.severity]}
                  </Tag>
                  <Tag color={STATUS_COLORS[defect.status]}>
                    {STATUS_LABELS[defect.status]}
                  </Tag>
                </Space>
              }
              extra={
                <Space onClick={(e) => e.stopPropagation()}>
                  {STATUS_TRANSITIONS[defect.status].length > 0 && (
                    <Select
                      size="small"
                      placeholder="更新状态"
                      style={{ width: 120 }}
                      onChange={(val) => void handleStatusChange(defect.id, val as DefectStatus)}
                      options={STATUS_TRANSITIONS[defect.status].map((s) => ({
                        label: STATUS_LABELS[s],
                        value: s,
                      }))}
                    />
                  )}
                  <Popconfirm
                    title="确定要删除该缺陷吗？"
                    onConfirm={() => void handleDelete(defect.id)}
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <Button type="text" danger size="small" icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              }
            >
              <Space split={<span style={{ color: "var(--text-muted)" }}>·</span>}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(defect.createdAt).toLocaleString("zh-CN")}
                </Typography.Text>
                {defect.creator && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    创建人：{defect.creator}
                  </Typography.Text>
                )}
                {defect.assignee && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    指派给：{defect.assignee}
                  </Typography.Text>
                )}
                {defect.recommendationId && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    来源：回归推荐
                  </Typography.Text>
                )}
              </Space>
              {defect.description && (
                <Typography.Paragraph
                  ellipsis={{ rows: 2 }}
                  type="secondary"
                  style={{ marginBottom: 0, marginTop: 8, fontSize: 13 }}
                >
                  {defect.description}
                </Typography.Paragraph>
              )}
            </Card>
          ))}
        </Space>
      )}

      {/* 分页 */}
      {total > PAGE_SIZE && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <Pagination
            current={page}
            pageSize={PAGE_SIZE}
            total={total}
            onChange={(p) => setPage(p)}
            showSizeChanger={false}
          />
        </div>
      )}

      {/* 详情弹窗 */}
      <Modal
        open={!!selectedDefect}
        title={
          <Space>
            <BugOutlined style={{ color: "var(--color-danger)" }} />
            <span>缺陷详情</span>
            {selectedDefect && (
              <>
                <Tag color={SEVERITY_COLORS[selectedDefect.severity]}>
                  {SEVERITY_LABELS[selectedDefect.severity]}
                </Tag>
                <Tag color={STATUS_COLORS[selectedDefect.status]}>
                  {STATUS_LABELS[selectedDefect.status]}
                </Tag>
              </>
            )}
          </Space>
        }
        onCancel={() => setSelectedDefect(null)}
        onOk={() => setSelectedDefect(null)}
        okText="关闭"
        width={700}
        footer={
          selectedDefect && STATUS_TRANSITIONS[selectedDefect.status].length > 0 ? (
            <Space>
              <Button onClick={() => setSelectedDefect(null)}>关闭</Button>
              {STATUS_TRANSITIONS[selectedDefect.status].map((s) => (
                <Button
                  key={s}
                  type="primary"
                  icon={s === "resolved" ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
                  onClick={() => {
                    if (selectedDefect) void handleStatusChange(selectedDefect.id, s);
                    setSelectedDefect(null);
                  }}
                >
                  标记为{STATUS_LABELS[s]}
                </Button>
              ))}
            </Space>
          ) : (
            <Button onClick={() => setSelectedDefect(null)}>关闭</Button>
          )
        }
      >
        {selectedDefect && (
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="缺陷标题" span={2}>
              {selectedDefect.title}
            </Descriptions.Item>
            <Descriptions.Item label="严重程度">
              <Tag color={SEVERITY_COLORS[selectedDefect.severity]}>
                {SEVERITY_LABELS[selectedDefect.severity]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag>{selectedDefect.priority}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_COLORS[selectedDefect.status]}>
                {STATUS_LABELS[selectedDefect.status]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建人">{selectedDefect.creator ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="指派给">{selectedDefect.assignee ?? "-"}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(selectedDefect.createdAt).toLocaleString("zh-CN")}
            </Descriptions.Item>
            {selectedDefect.resolvedAt && (
              <Descriptions.Item label="解决时间">
                {new Date(selectedDefect.resolvedAt).toLocaleString("zh-CN")}
              </Descriptions.Item>
            )}
            {selectedDefect.environment && (
              <Descriptions.Item label="环境">{selectedDefect.environment}</Descriptions.Item>
            )}
            {selectedDefect.browser && (
              <Descriptions.Item label="浏览器">{selectedDefect.browser}</Descriptions.Item>
            )}
            {selectedDefect.recommendationId && (
              <Descriptions.Item label="关联回归推荐" span={2}>
                <Typography.Text type="secondary">{selectedDefect.recommendationId}</Typography.Text>
              </Descriptions.Item>
            )}
            {selectedDefect.description && (
              <Descriptions.Item label="缺陷描述" span={2}>
                <Typography.Paragraph style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>
                  {selectedDefect.description}
                </Typography.Paragraph>
              </Descriptions.Item>
            )}
            {selectedDefect.rootCause && (
              <Descriptions.Item label="根因分析" span={2}>
                <Typography.Paragraph style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>
                  {selectedDefect.rootCause}
                </Typography.Paragraph>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* 新建缺陷弹窗 */}
      <Modal
        open={createModalOpen}
        title={
          <Space>
            <BugOutlined style={{ color: "var(--color-danger)" }} />
            <span>新建缺陷</span>
          </Space>
        }
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ severity: "medium", priority: "medium" }}
        >
          <Form.Item
            name="title"
            label="缺陷标题"
            rules={[{ required: true, message: "请输入缺陷标题" }]}
          >
            <Input placeholder="请输入缺陷标题" />
          </Form.Item>

          <Form.Item name="description" label="缺陷描述">
            <Input.TextArea rows={4} placeholder="请描述缺陷内容、复现步骤、预期结果等" />
          </Form.Item>

          <Space style={{ width: "100%" }} size="middle">
            <Form.Item
              name="severity"
              label="严重程度"
              rules={[{ required: true, message: "请选择严重程度" }]}
              style={{ width: 180 }}
            >
              <Select placeholder="请选择">
                <Select.Option value="critical">
                  <Tag color="red">致命</Tag>
                </Select.Option>
                <Select.Option value="high">
                  <Tag color="orange">高</Tag>
                </Select.Option>
                <Select.Option value="medium">
                  <Tag color="gold">中</Tag>
                </Select.Option>
                <Select.Option value="low">
                  <Tag color="blue">低</Tag>
                </Select.Option>
              </Select>
            </Form.Item>

            <Form.Item name="priority" label="优先级" style={{ width: 180 }}>
              <Select placeholder="请选择">
                <Select.Option value="high">
                  <Tag color="red">高</Tag>
                </Select.Option>
                <Select.Option value="medium">
                  <Tag color="gold">中</Tag>
                </Select.Option>
                <Select.Option value="low">
                  <Tag color="blue">低</Tag>
                </Select.Option>
              </Select>
            </Form.Item>
          </Space>

          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="environment" label="环境" style={{ flex: 1 }}>
              <Input placeholder="例如：Chrome 120 / Windows 11" />
            </Form.Item>

            <Form.Item name="browser" label="浏览器" style={{ flex: 1 }}>
              <Input placeholder="例如：Chrome" />
            </Form.Item>
          </Space>

          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="creator" label="创建人" style={{ flex: 1 }}>
              <Input placeholder="请输入创建人姓名" />
            </Form.Item>

            <Form.Item name="assignee" label="指派给" style={{ flex: 1 }}>
              <Input placeholder="请输入指派人姓名" />
            </Form.Item>
          </Space>

          <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
            <Space style={{ width: "100%", justifyContent: "flex-end" }}>
              <Button
                onClick={() => {
                  setCreateModalOpen(false);
                  createForm.resetFields();
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={createSubmitting}>
                创建缺陷
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 从执行记录创建缺陷弹窗 */}
      <Modal
        open={fromExecModalOpen}
        title={
          <Space>
            <BugOutlined style={{ color: "var(--color-danger)" }} />
            <span>从执行记录创建缺陷</span>
          </Space>
        }
        onCancel={() => {
          setFromExecModalOpen(false);
          fromExecForm.resetFields();
        }}
        footer={null}
        width={560}
        destroyOnClose
      >
        <Alert
          type="info"
          message="从执行失败的用例快速创建缺陷"
          description="选择关联的执行记录 ID，系统将自动获取相关信息并预填到缺陷表单中。"
          style={{ marginBottom: 16 }}
        />
        <Form
          form={fromExecForm}
          layout="vertical"
          onFinish={handleCreateFromExecution}
          initialValues={{ severity: "medium", priority: "medium" }}
        >
          <Form.Item
            name="executionId"
            label="执行记录 ID"
            rules={[{ required: true, message: "请输入执行记录 ID" }]}
          >
            <Input placeholder="请输入回归执行记录的 recommendationId" />
          </Form.Item>

          <Form.Item
            name="title"
            label="缺陷标题"
            rules={[{ required: true, message: "请输入缺陷标题" }]}
          >
            <Input placeholder="请输入缺陷标题" />
          </Form.Item>

          <Form.Item name="description" label="缺陷描述">
            <Input.TextArea rows={3} placeholder="可选，补充缺陷描述或复现步骤" />
          </Form.Item>

          <Space style={{ width: "100%" }} size="middle">
            <Form.Item name="severity" label="严重程度" rules={[{ required: true }]} style={{ width: 160 }}>
              <Select>
                <Select.Option value="critical"><Tag color="red">致命</Tag></Select.Option>
                <Select.Option value="high"><Tag color="orange">高</Tag></Select.Option>
                <Select.Option value="medium"><Tag color="gold">中</Tag></Select.Option>
                <Select.Option value="low"><Tag color="blue">低</Tag></Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="priority" label="优先级" style={{ width: 160 }}>
              <Select>
                <Select.Option value="high"><Tag color="red">高</Tag></Select.Option>
                <Select.Option value="medium"><Tag color="gold">中</Tag></Select.Option>
                <Select.Option value="low"><Tag color="blue">低</Tag></Select.Option>
              </Select>
            </Form.Item>
          </Space>

          <Form.Item name="creator" label="创建人">
            <Input placeholder="请输入创建人姓名" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
            <Space style={{ width: "100%", justifyContent: "flex-end" }}>
              <Button onClick={() => { setFromExecModalOpen(false); fromExecForm.resetFields(); }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={fromExecSubmitting}>
                创建缺陷
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
