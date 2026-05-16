import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Form,
  Input,
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
  HomeOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import {
  TestSuite,
  createSuite,
  deleteSuite,
  listSuites,
  updateSuite,
} from "../../services/autoTest";

export function SuiteListPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(true);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSuite, setEditingSuite] = useState<TestSuite | null>(null);
  const [form] = Form.useForm();

  const loadSuites = async () => {
    setLoading(true);
    try {
      const data = await listSuites();
      setSuites(data);
    } catch {
      messageApi.error("加载套件失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSuites();
  }, []);

  const handleCreate = () => {
    setEditingSuite(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (suite: TestSuite) => {
    setEditingSuite(suite);
    form.setFieldsValue(suite);
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSuite(id);
      messageApi.success("套件已删除");
      await loadSuites();
    } catch {
      messageApi.error("删除失败");
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingSuite) {
        await updateSuite(editingSuite.id, values);
        messageApi.success("套件已更新");
      } else {
        await createSuite(values);
        messageApi.success("套件已创建");
      }
      setModalOpen(false);
      await loadSuites();
    } catch {
      messageApi.error("保存失败");
    }
  };

  const columns = [
    {
      title: "套件名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: TestSuite) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{name}</Typography.Text>
          {record.description && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: "用例数",
      dataIndex: "caseCount",
      key: "caseCount",
      width: 100,
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "isActive",
      key: "isActive",
      width: 80,
      render: (isActive: boolean) => (
        <Tag color={isActive ? "success" : "default"}>
          {isActive ? "启用" : "禁用"}
        </Tag>
      ),
    },
    {
      title: "创建时间",
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
      width: 120,
      render: (_: unknown, record: TestSuite) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确认删除此套件？"
            description="将同时删除所有关联的用例"
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
            <Space size={4} style={{ marginBottom: 4 }}>
              <Button type="link" size="small" icon={<HomeOutlined />} onClick={() => navigate("/auto-test")}
                style={{ padding: 0, color: "var(--text-secondary)", fontSize: 12 }}>
                工作台
              </Button>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>/</Typography.Text>
              <Typography.Text style={{ fontSize: 12 }}>测试套件</Typography.Text>
            </Space>
            <Typography.Title level={4} style={{ margin: 0 }}>
              测试套件管理
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              创建和管理测试套件，组织测试用例
            </Typography.Paragraph>
          </div>
          <div className="workbench-intro-side">
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建套件
            </Button>
          </div>
        </div>

        <Card>
          <Table
            dataSource={suites}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>

        <Modal
          title={editingSuite ? "编辑套件" : "新建套件"}
          open={modalOpen}
          onOk={handleSave}
          onCancel={() => setModalOpen(false)}
          okText="保存"
          cancelText="取消"
        >
          <Form form={form} layout="vertical">
            <Form.Item
              name="name"
              label="套件名称"
              rules={[{ required: true, message: "请输入套件名称" }]}
            >
              <Input placeholder="例如：用户模块测试套件" />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea placeholder="描述套件用途" rows={3} />
            </Form.Item>
            <Form.Item name="projectId" label="项目ID">
              <Input placeholder="关联的项目ID" />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </>
  );
}
