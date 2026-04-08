import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SaveOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";

import {
  deleteKnowledgeDocument,
  getKnowledgeDocument,
  reindexKnowledgeDocument,
  updateKnowledgeDocument,
  type KnowledgeChunkItem,
  type KnowledgeDocumentDetail,
  type KnowledgeDocumentUpdatePayload,
} from "../services/api";

const DOC_TYPE_OPTIONS = [
  { value: "requirement", label: "需求文档" },
  { value: "defect", label: "缺陷记录" },
  { value: "testcase", label: "历史测试用例" },
  { value: "other", label: "其他" },
];

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

export function KnowledgeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const [doc, setDoc] = useState<KnowledgeDocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form] = Form.useForm();

  const fetchDoc = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const detail = await getKnowledgeDocument(id);
      setDoc(detail);
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "加载文档失败。");
    } finally {
      setLoading(false);
    }
  }, [id, messageApi]);

  useEffect(() => {
    void fetchDoc();
  }, [fetchDoc]);

  const handleSave = async () => {
    if (!id || !doc) return;
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload: KnowledgeDocumentUpdatePayload = {
        title: values.title,
        docType: values.docType,
        moduleTags: values.moduleTags,
        status: values.status,
        summary: values.summary || undefined,
        content: values.content,
      };
      await updateKnowledgeDocument(id, payload);
      messageApi.success("已保存。");
      setEditing(false);
      void fetchDoc();
    } catch (err) {
      if (err instanceof Error) messageApi.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    try {
      await deleteKnowledgeDocument(id);
      messageApi.success("已删除。");
      navigate("/knowledge");
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "删除失败。");
    }
  };

  const handleReindex = async () => {
    if (!id) return;
    try {
      await reindexKnowledgeDocument(id);
      messageApi.success("已提交重建索引。");
      void fetchDoc();
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "重建索引失败。");
    }
  };

  if (loading) {
    return (
      <Card loading style={{ marginTop: 16 }}>
        <div style={{ height: 200 }} />
      </Card>
    );
  }

  if (!doc) {
    return (
      <Alert type="error" showIcon message="文档未找到" style={{ marginTop: 16 }} />
    );
  }

  const chunkColumns = [
    { title: "#", dataIndex: "chunkIndex", width: 60 },
    {
      title: "分块内容",
      dataIndex: "chunkText",
      ellipsis: true,
      render: (t: string) => (
        <Typography.Paragraph
          ellipsis={{ rows: 2, expandable: true }}
          style={{ marginBottom: 0, fontSize: 13 }}
        >
          {t}
        </Typography.Paragraph>
      ),
    },
    { title: "Token", dataIndex: "tokenCount", width: 80 },
    {
      title: "Embedding",
      dataIndex: "hasEmbedding",
      width: 100,
      render: (v: boolean) => (
        <Tag color={v ? "success" : "default"}>{v ? "已生成" : "待生成"}</Tag>
      ),
    },
  ];

  return (
    <>
      {contextHolder}

      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/knowledge")}
        >
          返回列表
        </Button>
      </Space>

      <Row gutter={[20, 20]}>
        <Col xs={24} lg={editing ? 24 : 10}>
          <Card
            title="文档信息"
            extra={
              <Space>
                {!editing && (
                  <>
                    <Button
                      onClick={() => {
                        form.setFieldsValue({
                          title: doc.title,
                          docType: doc.docType,
                          moduleTags: doc.moduleTags,
                          status: doc.status,
                          summary: doc.summary ?? "",
                          content: doc.content,
                        });
                        setEditing(true);
                      }}
                    >
                      编辑
                    </Button>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={() => void handleReindex()}
                    >
                      重建索引
                    </Button>
                    <Popconfirm
                      title="确定删除此文档？"
                      onConfirm={() => void handleDelete()}
                    >
                      <Button danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </>
                )}
                {editing && (
                  <>
                    <Button onClick={() => setEditing(false)}>取消</Button>
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() => void handleSave()}
                    >
                      保存
                    </Button>
                  </>
                )}
              </Space>
            }
          >
            {editing ? (
              <Form form={form} layout="vertical">
                <Form.Item
                  name="title"
                  label="标题"
                  rules={[{ required: true }]}
                >
                  <Input />
                </Form.Item>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item name="docType" label="类型">
                      <Select options={DOC_TYPE_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="status" label="状态">
                      <Select options={STATUS_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="moduleTags" label="模块标签">
                      <Select
                        mode="tags"
                        placeholder="回车添加"
                        tokenSeparators={[","]}
                      />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item name="summary" label="摘要">
                  <Input.TextArea rows={3} placeholder="可选，检索时优先匹配摘要" />
                </Form.Item>
                <Form.Item
                  name="content"
                  label="内容"
                  rules={[{ required: true }]}
                >
                  <Input.TextArea rows={16} />
                </Form.Item>
              </Form>
            ) : (
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="标题">{doc.title}</Descriptions.Item>
                <Descriptions.Item label="类型">
                  <Tag>
                    {DOC_TYPE_OPTIONS.find((o) => o.value === doc.docType)?.label ??
                      doc.docType}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={doc.status === "active" ? "green" : "default"}>
                    {STATUS_OPTIONS.find((o) => o.value === doc.status)?.label ??
                      doc.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="模块标签">
                  {doc.moduleTags.length
                    ? doc.moduleTags.map((t) => <Tag key={t}>{t}</Tag>)
                    : "-"}
                </Descriptions.Item>
                <Descriptions.Item label="来源">
                  {doc.sourceType === "upload"
                    ? `上传 (${doc.sourceFilename ?? ""})`
                    : "手动录入"}
                </Descriptions.Item>
                <Descriptions.Item label="索引状态">
                  <Tag color={EMBEDDING_COLOR[doc.embeddingStatus] ?? "default"}>
                    {doc.embeddingStatus}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {new Date(doc.createdAt).toLocaleString("zh-CN")}
                </Descriptions.Item>
                {doc.summary && (
                  <Descriptions.Item label="摘要">
                    {doc.summary}
                  </Descriptions.Item>
                )}
              </Descriptions>
            )}
          </Card>
        </Col>

        {!editing && (
          <Col xs={24} lg={14}>
            <Card title="文档内容" style={{ marginBottom: 20 }}>
              <Typography.Paragraph
                style={{ whiteSpace: "pre-wrap", fontSize: 13, maxHeight: 400, overflow: "auto" }}
              >
                {doc.content}
              </Typography.Paragraph>
            </Card>

            <Card title={`分块预览 (${doc.chunks.length} 块)`}>
              <Table<KnowledgeChunkItem>
                rowKey="id"
                columns={chunkColumns}
                dataSource={doc.chunks}
                pagination={doc.chunks.length > 10 ? { pageSize: 10 } : false}
                size="small"
              />
            </Card>
          </Col>
        )}
      </Row>
    </>
  );
}
