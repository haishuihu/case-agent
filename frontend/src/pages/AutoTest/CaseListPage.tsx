import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";

import {
  TestCase,
  TestSuite,
  createCase,
  deleteCase,
  listCases,
  listSuites,
  updateCase,
} from "../../services/autoTest";

const PRIORITY_OPTIONS = [
  { value: 1, label: "P1 - 最高" },
  { value: 2, label: "P2 - 高" },
  { value: 3, label: "P3 - 中" },
  { value: 4, label: "P4 - 低" },
  { value: 5, label: "P5 - 最低" },
];

const STATUS_OPTIONS = [
  { value: "draft", label: "草稿" },
  { value: "active", label: "活跃" },
  { value: "deprecated", label: "已废弃" },
  { value: "archived", label: "已归档" },
];

const TYPE_OPTIONS = [
  { value: "api", label: "API 测试" },
  { value: "ui", label: "UI 测试" },
  { value: "unit", label: "单元测试" },
  { value: "integration", label: "集成测试" },
];

export function CaseListPage() {
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<TestCase[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCase, setEditingCase] = useState<TestCase | null>(null);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState({
    suiteId: undefined as string | undefined,
    status: undefined as string | undefined,
    search: "",
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [casesData, suitesData] = await Promise.all([
        listCases({ ...filters, search: filters.search || undefined }),
        listSuites(),
      ]);
      setCases(casesData);
      setSuites(suitesData);
    } catch {
      messageApi.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [filters]);

  const handleCreate = () => {
    setEditingCase(null);
    form.resetFields();
    form.setFieldsValue({
      caseType: "api",
      priority: 3,
      expectedStatus: 200,
    });
    setModalOpen(true);
  };

  const handleEdit = (c: TestCase) => {
    setEditingCase(c);
    form.setFieldsValue({
      ...c,
      headers: c.headers ? JSON.stringify(c.headers) : undefined,
      requestBody: c.requestBody ? JSON.stringify(c.requestBody) : undefined,
      expectedResponse: c.expectedResponse ? JSON.stringify(c.expectedResponse) : undefined,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteCase(id);
      messageApi.success("用例已删除");
      await loadData();
    } catch {
      messageApi.error("删除失败");
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const data: Record<string, unknown> = { ...values };
      
      if (values.headers) {
        try { data.headers = JSON.parse(values.headers as string); } catch { /* ignore */ }
      }
      if (values.requestBody) {
        try { data.requestBody = JSON.parse(values.requestBody as string); } catch { /* ignore */ }
      }
      if (values.expectedResponse) {
        try { data.expectedResponse = JSON.parse(values.expectedResponse as string); } catch { /* ignore */ }
      }
      
      if (editingCase) {
        await updateCase(editingCase.id, data as Parameters<typeof updateCase>[1]);
        messageApi.success("用例已更新");
      } else {
        await createCase(data as unknown as Parameters<typeof createCase>[0]);
        messageApi.success("用例已创建");
      }
      setModalOpen(false);
      await loadData();
    } catch {
      messageApi.error("保存失败");
    }
  };

  const columns = [
    {
      title: "用例标题",
      dataIndex: "title",
      key: "title",
      render: (title: string, record: TestCase) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{title}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {record.endpoint && `[${record.method}] ${record.endpoint}`}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "caseType",
      key: "caseType",
      width: 100,
      render: (type: string) => {
        const colors: Record<string, string> = { api: "blue", ui: "purple", unit: "green", integration: "orange" };
        return <Tag color={colors[type] || "default"}>{TYPE_OPTIONS.find(t => t.value === type)?.label || type}</Tag>;
      },
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 80,
      render: (priority: number) => {
        const colors = ["red", "orange", "blue", "cyan", "default"];
        return <Tag color={colors[priority - 1] || "default"}>P{priority}</Tag>;
      },
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (status: string) => {
        const colors: Record<string, string> = { draft: "default", active: "success", deprecated: "warning", archived: "default" };
        return <Tag color={colors[status] || "default"}>{STATUS_OPTIONS.find(s => s.value === status)?.label || status}</Tag>;
      },
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: TestCase) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="确认删除此用例？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      {contextHolder}
      <div className="auto-test-page">
        <div className="workbench-intro">
          <div className="workbench-intro-main">
            <Typography.Text className="workbench-intro-eyebrow">Test Case</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>
              测试用例管理
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              管理 API 测试用例，支持批量导入和编辑
            </Typography.Paragraph>
          </div>
          <div className="workbench-intro-side">
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建用例
            </Button>
          </div>
        </div>

        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col span={8}>
              <Input
                placeholder="搜索用例标题..."
                prefix={<SearchOutlined />}
                value={filters.search}
                onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
              />
            </Col>
            <Col span={6}>
              <Select
                placeholder="选择套件"
                allowClear
                style={{ width: "100%" }}
                value={filters.suiteId}
                onChange={(value) => setFilters(f => ({ ...f, suiteId: value }))}
                options={suites.map(s => ({ value: s.id, label: s.name }))}
              />
            </Col>
            <Col span={6}>
              <Select
                placeholder="选择状态"
                allowClear
                style={{ width: "100%" }}
                value={filters.status}
                onChange={(value) => setFilters(f => ({ ...f, status: value }))}
                options={STATUS_OPTIONS}
              />
            </Col>
          </Row>
        </Card>

        <Card>
          <Table
            dataSource={cases}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>

        <Modal
          title={editingCase ? "编辑用例" : "新建用例"}
          open={modalOpen}
          onOk={handleSave}
          onCancel={() => setModalOpen(false)}
          okText="保存"
          cancelText="取消"
          width={700}
        >
          <Form form={form} layout="vertical">
            <Row gutter={16}>
              <Col span={16}>
                <Form.Item name="suiteId" label="所属套件" rules={[{ required: true, message: "请选择套件" }]}>
                  <Select
                    placeholder="选择套件"
                    options={suites.map(s => ({ value: s.id, label: s.name }))}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="priority" label="优先级" initialValue={3}>
                  <Select options={PRIORITY_OPTIONS} />
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item name="title" label="用例标题" rules={[{ required: true, message: "请输入标题" }]}>
              <Input placeholder="例如：用户登录 - 正确账号密码" />
            </Form.Item>

            <Typography.Title level={5}>API 配置</Typography.Title>
            
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="method" label="方法">
                  <Select allowClear>
                    <Select.Option value="GET">GET</Select.Option>
                    <Select.Option value="POST">POST</Select.Option>
                    <Select.Option value="PUT">PUT</Select.Option>
                    <Select.Option value="DELETE">DELETE</Select.Option>
                    <Select.Option value="PATCH">PATCH</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={18}>
                <Form.Item name="endpoint" label="端点">
                  <Input placeholder="https://api.example.com/users/login" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="headers" label="请求头 (JSON)">
              <Input.TextArea placeholder='{"Authorization": "Bearer token"}' rows={2} />
            </Form.Item>

            <Form.Item name="requestBody" label="请求体 (JSON)">
              <Input.TextArea placeholder='{"username": "test", "password": "123456"}' rows={3} />
            </Form.Item>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="expectedStatus" label="预期状态码" initialValue={200}>
                  <InputNumber style={{ width: "100%" }} min={100} max={599} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="expectedResponse" label="预期响应 (JSON)">
              <Input.TextArea placeholder='{"code": 0, "message": "success"}' rows={3} />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </>
  );
}
