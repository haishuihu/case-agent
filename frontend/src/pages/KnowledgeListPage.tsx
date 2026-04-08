import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import {
  BookOutlined,
  DeleteOutlined,
  EditOutlined,
  InboxOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";

import {
  createKnowledgeDocument,
  deleteKnowledgeDocument,
  getKnowledgeStats,
  listKnowledgeDocuments,
  reindexKnowledgeDocument,
  uploadKnowledgeDocument,
  type KnowledgeDocumentCreatePayload,
  type KnowledgeDocumentItem,
  type KnowledgeStatsResponse,
} from "../services/api";

const DOC_TYPE_OPTIONS = [
  { value: "requirement", label: "需求文档" },
  { value: "defect", label: "缺陷记录" },
  { value: "testcase", label: "历史测试用例" },
  { value: "other", label: "其他" },
];

const DOC_TYPE_COLOR: Record<string, string> = {
  requirement: "blue",
  defect: "red",
  testcase: "green",
  other: "default",
};

const STATUS_OPTIONS = [
  { value: "active", label: "生效中" },
  { value: "deprecated", label: "已过时" },
  { value: "archived", label: "已归档" },
];

const EMBEDDING_COLOR: Record<string, string> = {
  pending: "default",
  processing: "processing",
  completed: "success",
  failed: "error",
};

export function KnowledgeListPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const [items, setItems] = useState<KnowledgeDocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<KnowledgeStatsResponse | null>(null);

  const [filterDocType, setFilterDocType] = useState<string>();
  const [filterStatus, setFilterStatus] = useState<string>();
  const [filterSearch, setFilterSearch] = useState("");

  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [manualForm] = Form.useForm<KnowledgeDocumentCreatePayload>();

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDocType, setUploadDocType] = useState("other");
  const [uploadModuleTags, setUploadModuleTags] = useState("");

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await listKnowledgeDocuments({
        page,
        pageSize,
        docType: filterDocType,
        status: filterStatus,
        search: filterSearch || undefined,
      });
      setItems(resp.items);
      setTotal(resp.total);
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "加载知识文档列表失败。");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filterDocType, filterStatus, filterSearch, messageApi]);

  const fetchStats = useCallback(async () => {
    try {
      setStats(await getKnowledgeStats());
    } catch {
      /* stats are non-critical */
    }
  }, []);

  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    void fetchStats();
  }, [fetchStats]);

  const handleDelete = async (id: string) => {
    try {
      await deleteKnowledgeDocument(id);
      messageApi.success("已删除。");
      void fetchDocuments();
      void fetchStats();
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "删除失败。");
    }
  };

  const handleReindex = async (id: string) => {
    try {
      await reindexKnowledgeDocument(id);
      messageApi.success("已提交重建索引。");
      void fetchDocuments();
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "重建索引失败。");
    }
  };

  const handleManualCreate = async () => {
    try {
      const values = await manualForm.validateFields();
      setSubmitting(true);
      await createKnowledgeDocument(values);
      messageApi.success("知识文档已创建。");
      setManualModalOpen(false);
      manualForm.resetFields();
      void fetchDocuments();
      void fetchStats();
    } catch (err) {
      if (err instanceof Error) messageApi.error(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) {
      messageApi.warning("请选择文件。");
      return;
    }
    setSubmitting(true);
    try {
      await uploadKnowledgeDocument(uploadFile, {
        title: uploadTitle || undefined,
        docType: uploadDocType,
        moduleTags: uploadModuleTags || undefined,
      });
      messageApi.success("文档已上传入库。");
      setUploadModalOpen(false);
      setUploadFile(null);
      setUploadTitle("");
      setUploadDocType("other");
      setUploadModuleTags("");
      void fetchDocuments();
      void fetchStats();
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "上传失败。");
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ColumnsType<KnowledgeDocumentItem> = [
    {
      title: "标题",
      dataIndex: "title",
      ellipsis: true,
      render: (title: string, record) => (
        <a onClick={() => navigate(`/knowledge/${record.id}`)}>{title}</a>
      ),
    },
    {
      title: "类型",
      dataIndex: "docType",
      width: 120,
      render: (t: string) => (
        <Tag color={DOC_TYPE_COLOR[t] ?? "default"}>
          {DOC_TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t}
        </Tag>
      ),
    },
    {
      title: "模块标签",
      dataIndex: "moduleTags",
      width: 200,
      render: (tags: string[]) =>
        tags?.length ? tags.map((t) => <Tag key={t}>{t}</Tag>) : "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (s: string) => {
        const label = STATUS_OPTIONS.find((o) => o.value === s)?.label ?? s;
        return <Tag color={s === "active" ? "green" : "default"}>{label}</Tag>;
      },
    },
    {
      title: "索引",
      dataIndex: "embeddingStatus",
      width: 80,
      render: (s: string) => (
        <Tag color={EMBEDDING_COLOR[s] ?? "default"}>{s}</Tag>
      ),
    },
    {
      title: "来源",
      dataIndex: "sourceType",
      width: 80,
      render: (s: string) => (s === "upload" ? "上传" : "手动"),
    },
    {
      title: "创建时间",
      dataIndex: "createdAt",
      width: 170,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/knowledge/${record.id}`)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => void handleReindex(record.id)}
          >
            索引
          </Button>
          <Popconfirm
            title="确定删除此文档？"
            onConfirm={() => void handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      {contextHolder}

      <div className="workbench-intro">
        <div className="workbench-intro-main">
          <Typography.Text className="workbench-intro-eyebrow">
            Knowledge Base
          </Typography.Text>
          <Typography.Title level={4} style={{ margin: 0 }}>
            管理历史需求、缺陷和测试用例知识
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            上传或录入历史文档，系统自动索引后在生成测试用例时引用相关知识。
          </Typography.Paragraph>
        </div>
        {stats && (
          <div className="workbench-intro-side">
            <Tag color="blue">{stats.totalDocuments} 篇文档</Tag>
            <Tag color="green">{stats.activeDocuments} 篇生效</Tag>
            <Tag color="purple">{stats.totalChunks} 个分块</Tag>
          </div>
        )}
      </div>

      <Card
        title={
          <Space>
            <BookOutlined />
            <span>知识文档</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<UploadOutlined />}
              onClick={() => setUploadModalOpen(true)}
            >
              上传文档
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setManualModalOpen(true)}
            >
              手动录入
            </Button>
          </Space>
        }
      >
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索标题或内容"
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 220 }}
            value={filterSearch}
            onChange={(e) => {
              setFilterSearch(e.target.value);
              setPage(1);
            }}
          />
          <Select
            placeholder="文档类型"
            allowClear
            style={{ width: 140 }}
            options={DOC_TYPE_OPTIONS}
            value={filterDocType}
            onChange={(v) => {
              setFilterDocType(v);
              setPage(1);
            }}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 120 }}
            options={STATUS_OPTIONS}
            value={filterStatus}
            onChange={(v) => {
              setFilterStatus(v);
              setPage(1);
            }}
          />
        </Space>

        <Table<KnowledgeDocumentItem>
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          scroll={{ x: 1000 }}
          size="middle"
        />
      </Card>

      {/* Manual Entry Modal */}
      <Modal
        title="手动录入知识文档"
        open={manualModalOpen}
        onCancel={() => setManualModalOpen(false)}
        onOk={() => void handleManualCreate()}
        okText="创建"
        confirmLoading={submitting}
        width={640}
        destroyOnClose
      >
        <Form
          form={manualForm}
          layout="vertical"
          initialValues={{ docType: "other", moduleTags: [] }}
          preserve={false}
        >
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: "请输入标题" }]}
          >
            <Input placeholder="例如：登录模块历史缺陷汇总" />
          </Form.Item>
          <Form.Item name="docType" label="文档类型">
            <Select options={DOC_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item name="moduleTags" label="模块标签">
            <Select
              mode="tags"
              placeholder="输入后回车添加标签"
              tokenSeparators={[","]}
            />
          </Form.Item>
          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: "请输入内容" }]}
          >
            <Input.TextArea rows={10} placeholder="粘贴或输入知识文档内容" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Upload Modal */}
      <Modal
        title="上传知识文档"
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        onOk={() => void handleUpload()}
        okText="上传入库"
        confirmLoading={submitting}
        width={560}
        destroyOnClose
      >
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Upload.Dragger
            accept=".txt,.md,.pdf,.docx"
            maxCount={1}
            beforeUpload={(file) => {
              setUploadFile(file);
              return false;
            }}
            onRemove={() => setUploadFile(null)}
            fileList={
              uploadFile
                ? [{ uid: "-1", name: uploadFile.name, status: "done" as const }]
                : []
            }
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">拖拽或点击选择文件</p>
            <p className="ant-upload-hint">支持 txt、md、pdf、docx</p>
          </Upload.Dragger>
          <Input
            placeholder="文档标题（留空则使用文件名）"
            value={uploadTitle}
            onChange={(e) => setUploadTitle(e.target.value)}
          />
          <Select
            style={{ width: "100%" }}
            placeholder="文档类型"
            options={DOC_TYPE_OPTIONS}
            value={uploadDocType}
            onChange={setUploadDocType}
          />
          <Input
            placeholder="模块标签（逗号分隔，可选）"
            value={uploadModuleTags}
            onChange={(e) => setUploadModuleTags(e.target.value)}
          />
        </Space>
      </Modal>
    </>
  );
}
