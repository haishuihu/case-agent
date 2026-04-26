import { useState, useEffect, useCallback } from "react";
import {
  Button,
  Card,
  Empty,
  Input,
  List,
  message,
  Pagination,
  Segmented,
  Skeleton,
  Space,
  Tag,
  Typography,
  Tooltip,
  Popconfirm,
  Modal,
  Collapse,
  Alert,
  Progress,
  Form,
  Select,
} from "antd";
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  listReviews,
  deleteReview,
  updateReviewStatus,
  createReview,
  runAIReview,
  type CaseReview,
} from "../services/review";
import { listModels, type ModelOption } from "../services/api";

const STATUS_FILTERS = [
  { label: "全部", value: "all" },
  { label: "待评审", value: "pending" },
  { label: "评审中", value: "in_review" },
  { label: "已通过", value: "approved" },
  { label: "需修改", value: "needs_revision" },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "default",
  in_review: "processing",
  approved: "success",
  needs_revision: "error",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待评审",
  in_review: "评审中",
  approved: "已通过",
  needs_revision: "需修改",
};

const DIMENSION_LABELS: Record<string, string> = {
  completeness: "完整性",
  executability: "可执行性",
  consistency: "一致性",
  redundancy: "冗余性",
  coverage: "覆盖率",
};

function ScoreTag({ score }: { score: number | null | undefined }) {
  if (score == null) return null;
  const color = score >= 80 ? "green" : score >= 60 ? "orange" : "red";
  return <Tag color={color}>{score}</Tag>;
}

interface CreateReviewModalProps {
  open: boolean;
  initialValues?: {
    generationId?: string;
    requirementText?: string;
    generatedCases?: string;
  };
  onClose: () => void;
  onSuccess: (review: CaseReview) => void;
}

function CreateReviewModal({ open, initialValues, onClose, onSuccess }: CreateReviewModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [runAiImmediately, setRunAiImmediately] = useState(false);
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);

  useEffect(() => {
    if (open) {
      void listModels().then((opts) => setModelOptions(opts)).catch(() => {});
      form.setFieldsValue({
        caseTitle: initialValues?.requirementText?.slice(0, 80) ?? "",
        requirementText: initialValues?.requirementText ?? "",
        generatedCases: initialValues?.generatedCases ?? "",
        generationId: initialValues?.generationId ?? "",
      });
    }
  }, [open, form, initialValues]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      let review: CaseReview;
      if (runAiImmediately) {
        review = await runAIReview({
          generationId: values.generationId as string | undefined,
          caseTitle: values.caseTitle as string | undefined,
          requirementText: values.requirementText as string,
          generatedCases: values.generatedCases as string | undefined,
          modelKey: values.modelKey as string | undefined,
        });
        message.success("AI 评审已完成");
      } else {
        review = await createReview({
          generationId: values.generationId as string | undefined,
          caseTitle: values.caseTitle as string | undefined,
          requirementText: values.requirementText as string,
          generatedCases: values.generatedCases as string | undefined,
        });
        message.success("评审记录已创建");
      }
      form.resetFields();
      onSuccess(review);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title={
        <Space>
          <SafetyCertificateOutlined />
          <span>新建评审</span>
        </Space>
      }
      onCancel={onClose}
      okText={runAiImmediately ? "发起 AI 评审" : "仅创建记录"}
      cancelText="取消"
      width={640}
      confirmLoading={loading}
      onOk={() => form.submit()}
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item name="generationId" label="关联生成记录 ID">
          <Input placeholder="可选，填写后可在详情页关联到生成记录" />
        </Form.Item>
        <Form.Item name="caseTitle" label="用例标题">
          <Input placeholder="简要描述本次评审的用例集" />
        </Form.Item>
        <Form.Item
          name="requirementText"
          label="需求文本"
          rules={[{ required: true, message: "请输入需求文本" }]}
        >
          <Input.TextArea rows={4} placeholder="描述需求背景、测试范围等" />
        </Form.Item>
        <Form.Item
          name="generatedCases"
          label="生成用例内容"
          tooltip="可直接粘贴 AI 生成的用例内容，或留空后手动补充"
        >
          <Input.TextArea rows={6} placeholder="AI 生成的用例 Markdown 内容（可选）" />
        </Form.Item>
        <Form.Item name="modelKey" label="评审模型">
          <Select
            allowClear
            placeholder="默认使用生成时所用的模型"
            options={modelOptions.map((m) => ({ label: m.label, value: m.key }))}
          />
        </Form.Item>
        <Form.Item name="runAi" label="评审方式">
          <Space direction="vertical">
            <Button
              type={runAiImmediately ? "primary" : "default"}
              icon={<ThunderboltOutlined />}
              onClick={() => setRunAiImmediately(true)}
            >
              立即发起 AI 评审
            </Button>
            <Button
              type={!runAiImmediately ? "primary" : "default"}
              onClick={() => setRunAiImmediately(false)}
            >
              仅创建记录（稍后评审）
            </Button>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {runAiImmediately
                ? "将立即调用 AI 评审，耗时较长但完成后可直接查看结果"
                : "将创建评审记录，稍后可进入详情页手动发起 AI 评审"}
            </Typography.Text>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
}

interface ReviewDetailModalProps {
  review: CaseReview;
  onClose: () => void;
  onRefresh: () => void;
}

function ReviewDetailModal({ review, onClose, onRefresh }: ReviewDetailModalProps) {
  const [loading, setLoading] = useState(false);

  const handleDecision = async (decision: "approved" | "needs_revision") => {
    setLoading(true);
    try {
      await updateReviewStatus(review.id, {
        reviewStatus: decision,
        decision,
      });
      message.success(decision === "approved" ? "已标记为通过" : "已标记为需修改");
      onRefresh();
    } catch {
      message.error("更新状态失败");
    } finally {
      setLoading(false);
    }
  };

  const collapseItems = [
    {
      key: "details",
      label: (
        <Space>
          <SafetyCertificateOutlined />
          <span><strong>AI 评审详情</strong></span>
        </Space>
      ),
      children: (
        <div>
          {review.aiReviewDetails?.dimensions?.map((dim) => (
            <div key={dim.dimension} style={{ marginBottom: 12 }}>
              <Space style={{ width: "100%", justifyContent: "space-between" }}>
                <Typography.Text>{DIMENSION_LABELS[dim.dimension] ?? dim.dimension}</Typography.Text>
                <ScoreTag score={dim.score} />
              </Space>
              <Progress
                percent={dim.score}
                size="small"
                showInfo={false}
                strokeColor={dim.score >= 80 ? "#52c41a" : dim.score >= 60 ? "#faad14" : "#ff4d4f"}
                style={{ marginTop: 2 }}
              />
              {dim.description && (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {dim.description}
                </Typography.Text>
              )}
            </div>
          ))}
        </div>
      ),
    },
    {
      key: "issues",
      label: (
        <span>
          <strong>发现问题</strong>（{review.aiReviewDetails?.issues?.length ?? 0} 项）
        </span>
      ),
      children: review.aiReviewDetails?.issues && review.aiReviewDetails.issues.length > 0 ? (
        <div>
          {review.aiReviewDetails.issues.map((issue, idx) => (
            <Alert
              key={idx}
              type={issue.severity === "high" ? "error" : issue.severity === "medium" ? "warning" : "info"}
              showIcon
              style={{ marginBottom: 8 }}
              message={`[${DIMENSION_LABELS[issue.type] ?? issue.type}] ${issue.description}`}
              description={issue.recommendation ? `建议：${issue.recommendation}` : undefined}
            />
          ))}
        </div>
      ) : (
        <Typography.Text type="secondary">未发现问题</Typography.Text>
      ),
    },
    {
      key: "suggestions",
      label: <span><strong>改进建议</strong>（{review.aiReviewDetails?.suggestions?.length ?? 0} 项）</span>,
      children: review.aiReviewDetails?.suggestions && review.aiReviewDetails.suggestions.length > 0 ? (
        <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
          {review.aiReviewDetails.suggestions.map((s, i) => (
            <li key={i}><Typography.Text>{s}</Typography.Text></li>
          ))}
        </ul>
      ) : (
        <Typography.Text type="secondary">暂无建议</Typography.Text>
      ),
    },
    {
      key: "meta",
      label: <span><strong>评审信息</strong></span>,
      children: (
        <Space direction="vertical">
          <Typography.Text type="secondary">
            评审人：{review.reviewer ?? "未填写"}
          </Typography.Text>
          <Typography.Text type="secondary">
            创建时间：{new Date(review.createdAt).toLocaleString("zh-CN")}
          </Typography.Text>
          {review.updatedAt && (
            <Typography.Text type="secondary">
              更新时间：{new Date(review.updatedAt).toLocaleString("zh-CN")}
            </Typography.Text>
          )}
          {review.generationId && (
            <Typography.Text type="secondary">
              关联生成记录：{review.generationId}
            </Typography.Text>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Modal
      open
      title={
        <Space>
          <SafetyCertificateOutlined />
          <span>评审详情</span>
          <Tag color={STATUS_COLORS[review.reviewStatus]}>{STATUS_LABELS[review.reviewStatus]}</Tag>
          {review.overallScore != null && (
            <Tag color={review.overallScore >= 80 ? "green" : review.overallScore >= 60 ? "orange" : "red"}>
              {review.overallScore}/100
            </Tag>
          )}
        </Space>
      }
      onCancel={onClose}
      onOk={onClose}
      okText="关闭"
      width={680}
      footer={
        review.reviewStatus !== "approved" && review.reviewStatus !== "needs_revision" ? (
          <Space>
            <Button onClick={onClose}>关闭</Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              loading={loading}
              onClick={() => void handleDecision("approved")}
            >
              标记为通过
            </Button>
            <Button
              danger
              icon={<ClockCircleOutlined />}
              loading={loading}
              onClick={() => void handleDecision("needs_revision")}
            >
              标记为需修改
            </Button>
          </Space>
        ) : (
          <Button onClick={onClose}>关闭</Button>
        )
      }
    >
      {review.caseTitle && (
        <Typography.Title level={5}>{review.caseTitle}</Typography.Title>
      )}
      {review.generatedCases && (
        <Alert
          type="info"
          message="评审用例内容"
          description={
            <Typography.Paragraph
              ellipsis={{ rows: 4 }}
              style={{ marginBottom: 0, fontSize: 12, fontFamily: "monospace" }}
            >
              {review.generatedCases}
            </Typography.Paragraph>
          }
          style={{ marginBottom: 12 }}
        />
      )}
      <Collapse items={collapseItems} defaultActiveKey={["details"]} />
    </Modal>
  );
}

export function ReviewListPage() {
  const [searchParams] = useSearchParams();
  const [reviews, setReviews] = useState<CaseReview[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedReview, setSelectedReview] = useState<CaseReview | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const prefillFromQuery = {
    generationId: searchParams.get("generationId") ?? undefined,
    requirementText: searchParams.get("requirementText") ?? undefined,
    generatedCases: searchParams.get("generatedCases") ?? undefined,
  };

  // Auto-open create modal when arriving with pre-fill data
  useEffect(() => {
    if (prefillFromQuery.generationId || prefillFromQuery.generatedCases) {
      setCreateModalOpen(true);
    }
  }, []);

  const PAGE_SIZE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Parameters<typeof listReviews>[0] = {
        page,
        pageSize: PAGE_SIZE,
      };
      if (statusFilter !== "all") {
        params.status = statusFilter;
      }
      const result = await listReviews(params);
      setReviews(result.items);
      setTotal(result.total);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载评审列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, refreshKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await deleteReview(id);
      message.success("评审记录已删除");
      setReviews((prev) => prev.filter((r) => r.id !== id));
    } catch {
      message.error("删除失败");
    }
  };

  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
    if (selectedReview) setSelectedReview(null);
  };

  const handleCreateSuccess = (review: CaseReview) => {
    setCreateModalOpen(false);
    setSelectedReview(review);
    void handleRefresh();
  };

  const overallStats = {
    total,
    pending: reviews.filter((r) => r.reviewStatus === "pending").length,
    inReview: reviews.filter((r) => r.reviewStatus === "in_review").length,
    approved: reviews.filter((r) => r.reviewStatus === "approved").length,
    needsRevision: reviews.filter((r) => r.reviewStatus === "needs_revision").length,
    avgScore:
      reviews.length > 0
        ? Math.round(
            reviews
              .filter((r) => r.overallScore != null)
              .reduce((sum, r) => sum + (r.overallScore ?? 0), 0) /
              reviews.filter((r) => r.overallScore != null).length
          )
        : null,
  };

  return (
    <div className="review-list-page">
      <div className="review-list-header">
        <Typography.Title level={4} style={{ margin: 0 }}>
          用例评审
        </Typography.Title>
        <Space>
          <Tooltip title="刷新">
            <Button icon={<ReloadOutlined />} onClick={() => void handleRefresh()} />
          </Tooltip>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            新建评审
          </Button>
        </Space>
      </div>

      {/* 统计概览 */}
      <div className="review-stats-bar">
        <Card size="small" bodyStyle={{ padding: "12px 16px" }}>
          <Space wrap>
            <Tag icon={<SafetyCertificateOutlined />}>{overallStats.total} 评审记录</Tag>
            <Tag color="default">{overallStats.pending} 待评审</Tag>
            <Tag color="processing">{overallStats.inReview} 评审中</Tag>
            <Tag color="success">{overallStats.approved} 已通过</Tag>
            <Tag color="error">{overallStats.needsRevision} 需修改</Tag>
            {overallStats.avgScore != null && (
              <Tag
                color={overallStats.avgScore >= 80 ? "green" : overallStats.avgScore >= 60 ? "orange" : "red"}
              >
                平均分 {overallStats.avgScore}
              </Tag>
            )}
          </Space>
        </Card>
      </div>

      {/* 状态筛选 */}
      <div className="review-filter-bar">
        <Segmented
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(String(val));
            setPage(1);
          }}
          options={STATUS_FILTERS.map((f) => ({ label: f.label, value: f.value }))}
        />
      </div>

      {/* 列表 */}
      {loading && reviews.length === 0 ? (
        <div style={{ padding: 40 }}>
          <Skeleton active />
        </div>
      ) : reviews.length === 0 ? (
        <Empty
          description={statusFilter !== "all" ? "该状态下暂无评审记录" : "暂无评审记录"}
          style={{ padding: 80 }}
        >
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            新建评审
          </Button>
        </Empty>
      ) : (
        <List
          dataSource={reviews}
          renderItem={(review) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="delete"
                  title="确定要删除该评审记录吗？"
                  onConfirm={() => void handleDelete(review.id)}
                  okText="删除"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                >
                  <Button type="text" danger size="small" icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 8,
                      background: "var(--bg-inset)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 18,
                      color: "var(--text-secondary)",
                    }}
                  >
                    <SafetyCertificateOutlined />
                  </div>
                }
                title={
                  <Space>
                    <Typography.Text strong>{review.caseTitle ?? "未命名评审"}</Typography.Text>
                    <Tag color={STATUS_COLORS[review.reviewStatus]}>
                      {STATUS_LABELS[review.reviewStatus]}
                    </Tag>
                    {review.overallScore != null && (
                      <Tag
                        color={
                          review.overallScore >= 80 ? "green" : review.overallScore >= 60 ? "orange" : "red"
                        }
                      >
                        {review.overallScore}/100
                      </Tag>
                    )}
                  </Space>
                }
                description={
                  <Space direction="vertical" size={2}>
                    {review.generatedCases && (
                      <Typography.Paragraph
                        ellipsis={{ rows: 1 }}
                        type="secondary"
                        style={{ marginBottom: 0, fontSize: 12 }}
                      >
                        {review.generatedCases.slice(0, 120)}
                        {review.generatedCases.length > 120 ? "..." : ""}
                      </Typography.Paragraph>
                    )}
                    <Space size="small">
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(review.createdAt).toLocaleString("zh-CN")}
                      </Typography.Text>
                      {review.reviewer && (
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          · {review.reviewer}
                        </Typography.Text>
                      )}
                      {review.aiReviewSummary && (
                        <Typography.Text
                          type="secondary"
                          style={{ fontSize: 12 }}
                          ellipsis={{ tooltip: review.aiReviewSummary }}
                        >
                          · {review.aiReviewSummary}
                        </Typography.Text>
                      )}
                    </Space>
                  </Space>
                }
                onClick={() => setSelectedReview(review)}
                style={{ cursor: "pointer" }}
              />
            </List.Item>
          )}
        />
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
      {selectedReview && (
        <ReviewDetailModal
          review={selectedReview}
          onClose={() => setSelectedReview(null)}
          onRefresh={handleRefresh}
        />
      )}

      {/* 新建评审弹窗 */}
      <CreateReviewModal
        open={createModalOpen}
        initialValues={prefillFromQuery}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
}
