import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import {
  createPlan,
  createTrigger,
  deletePlan,
  deleteTrigger,
  listPlans,
  listSuites,
  listTriggers,
  TestPlan,
  TestSuite,
  TriggerConfig,
  updatePlan,
  updateTrigger,
} from "../../services/autoTest";

const { Title, Text } = Typography;

const SCHEDULE_TYPES = [
  { label: "手动", value: "manual" },
  { label: "定时 (Cron)", value: "cron" },
  { label: "事件触发", value: "event" },
];

const TRIGGER_TYPES = [
  { label: "Git Push", value: "git_push" },
  { label: "定时", value: "schedule" },
  { label: "API 调用", value: "api_call" },
  { label: "CI/CD", value: "cicd" },
  { label: "提测门禁", value: "submission" },
];

const STATUS_COLORS: Record<string, string> = {
  completed: "#52c41a",
  failed: "#ff4d4f",
  running: "#1890ff",
  cancelled: "#999",
  pending: "#faad14",
};

export default function PlanListPage() {
  const [plans, setPlans] = useState<TestPlan[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<TestPlan | null>(null);
  const [triggerModalOpen, setTriggerModalOpen] = useState(false);
  const [triggers, setTriggers] = useState<TriggerConfig[]>([]);
  const [currentPlanId, setCurrentPlanId] = useState<string>("");
  const [form] = Form.useForm();
  const [triggerForm] = Form.useForm();
  const [msg, msgContext] = message.useMessage();

  const load = async () => {
    setLoading(true);
    try {
      const [plansData, suitesData] = await Promise.all([listPlans(), listSuites()]);
      setPlans(plansData);
      setSuites(suitesData);
    } catch (e: unknown) {
      msg.error("加载计划列表失败: " + (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditingPlan(null);
    form.resetFields();
    form.setFieldsValue({ scheduleType: "manual", autoExecute: false });
    setModalOpen(true);
  };

  const openEdit = (plan: TestPlan) => {
    setEditingPlan(plan);
    form.setFieldsValue(plan);
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editingPlan) {
        await updatePlan(editingPlan.id, values);
        msg.success("计划已更新");
      } else {
        await createPlan(values);
        msg.success("计划已创建");
      }
      setModalOpen(false);
      load();
    } catch (e: unknown) {
      msg.error("保存失败: " + (e as Error).message);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePlan(id);
      msg.success("计划已删除");
      load();
    } catch (e: unknown) {
      msg.error("删除失败: " + (e as Error).message);
    }
  };

  const openTriggers = async (planId: string) => {
    setCurrentPlanId(planId);
    try {
      const data = await listTriggers(planId);
      setTriggers(data);
    } catch (e: unknown) {
      msg.error("加载触发器失败: " + (e as Error).message);
    }
    setTriggerModalOpen(true);
  };

  const handleCreateTrigger = async () => {
    const values = await triggerForm.validateFields();
    try {
      await createTrigger(currentPlanId, values);
      msg.success("触发器已创建");
      triggerForm.resetFields();
      const data = await listTriggers(currentPlanId);
      setTriggers(data);
    } catch (e: unknown) {
      msg.error("创建触发器失败: " + (e as Error).message);
    }
  };

  const handleDeleteTrigger = async (id: string) => {
    try {
      await deleteTrigger(id);
      msg.success("触发器已删除");
      const data = await listTriggers(currentPlanId);
      setTriggers(data);
    } catch (e: unknown) {
      msg.error("删除触发器失败: " + (e as Error).message);
    }
  };

  const columns = [
    {
      title: "计划名称",
      dataIndex: "name" as const,
      render: (name: string, record: TestPlan) => (
        <div>
          <Text strong>{name}</Text>
          {record.description && (
            <div><Text type="secondary" style={{ fontSize: 12 }}>{record.description}</Text></div>
          )}
        </div>
      ),
    },
    {
      title: "套件",
      dataIndex: "suiteId" as const,
      render: (id: string) => suites.find((s) => s.id === id)?.name || id,
    },
    {
      title: "调度类型",
      dataIndex: "scheduleType" as const,
      render: (t: string) => SCHEDULE_TYPES.find((s) => s.value === t)?.label || t,
    },
    {
      title: "自动执行",
      dataIndex: "autoExecute" as const,
      render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: "最近执行",
      render: (_: unknown, record: TestPlan) => (
        <div>
          {record.lastExecutionStatus ? (
            <Tag color={STATUS_COLORS[record.lastExecutionStatus] || "#999"}>
              {record.lastExecutionStatus}
            </Tag>
          ) : (
            <Text type="secondary">-</Text>
          )}
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
            {record.executionCount} 次
          </Text>
        </div>
      ),
    },
    {
      title: "操作",
      render: (_: unknown, record: TestPlan) => (
        <Space>
          <Button size="small" icon={<ThunderboltOutlined />} onClick={() => openTriggers(record.id)}>
            触发器
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除此计划?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {msgContext}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>测试计划管理</Title>
          <Text type="secondary">创建和配置测试计划，管理自动化执行触发器</Text>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建计划</Button>
        </Col>
      </Row>

      <Spin spinning={loading}>
        <Table columns={columns} dataSource={plans} rowKey="id" pagination={{ pageSize: 10 }} />
      </Spin>

      <Modal
        title={editingPlan ? "编辑计划" : "新建计划"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="suiteId" label="所属套件" rules={[{ required: true, message: "请选择套件" }]}>
            <Select options={suites.map((s) => ({ label: s.name, value: s.id }))} />
          </Form.Item>
          <Form.Item name="name" label="计划名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="scheduleType" label="调度类型">
            <Select options={SCHEDULE_TYPES} />
          </Form.Item>
          <Form.Item name="autoExecute" label="自动执行" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="触发器管理"
        open={triggerModalOpen}
        onCancel={() => setTriggerModalOpen(false)}
        footer={null}
        width={700}
      >
        <div style={{ marginBottom: 16 }}>
          <Form form={triggerForm} layout="inline" onFinish={handleCreateTrigger}>
            <Form.Item name="triggerType" label="类型" rules={[{ required: true }]}>
              <Select options={TRIGGER_TYPES} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="name" label="名称">
              <Input style={{ width: 140 }} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">添加触发器</Button>
            </Form.Item>
          </Form>
        </div>
        <Table
          columns={[
            { title: "名称", dataIndex: "name", render: (n: string) => n || "-" },
            {
              title: "类型",
              dataIndex: "triggerType",
              render: (t: string) => TRIGGER_TYPES.find((tp) => tp.value === t)?.label || t,
            },
            {
              title: "状态",
              dataIndex: "enabled",
              render: (v: boolean) => (v ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag>),
            },
            {
              title: "最后触发",
              dataIndex: "lastTriggeredAt",
              render: (t: string) => (t ? new Date(t).toLocaleString("zh-CN") : "-"),
            },
            {
              title: "操作",
              render: (_: unknown, record: TriggerConfig) => (
                <Popconfirm title="确认删除此触发器?" onConfirm={() => handleDeleteTrigger(record.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              ),
            },
          ]}
          dataSource={triggers}
          rowKey="id"
          pagination={false}
        />
      </Modal>
    </div>
  );
}
