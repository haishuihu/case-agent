import { useState, useEffect, useCallback } from "react";
import {
  Button,
  message,
  Segmented,
  Space,
  Typography,
} from "antd";
import {
  PlusOutlined,
  ArrowLeftOutlined,
} from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";

import { SubmissionForm } from "../components/submission/SubmissionForm";
import {
  createSubmission,
  generateChecklist,
  listSubmissions,
  type GenerateChecklistResponse,
  type Submission,
  type SubmissionListResponse,
} from "../services/submission";

const STATUS_FILTERS = [
  { label: "全部", value: "all" },
  { label: "待处理", value: "pending" },
  { label: "自测中", value: "self_test" },
  { label: "自测通过", value: "self_test_passed" },
  { label: "门禁通过", value: "gate_passed" },
  { label: "门禁拒绝", value: "gate_rejected" },
];

const PAGE_SIZE = 20;

export function SubmissionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get("mode");

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);

  const loadSubmissions = useCallback(async () => {
    setLoading(true);
    try {
      const params =
        statusFilter !== "all" ? { page, pageSize: PAGE_SIZE, status: statusFilter } : { page, pageSize: PAGE_SIZE };
      const result: SubmissionListResponse = await listSubmissions(params);
      setSubmissions(result.items);
      setTotal(result.total);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载提测列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    if (mode !== "create") {
      void loadSubmissions();
    }
  }, [loadSubmissions, mode]);

  const handleCreate = () => {
    navigate("/submissions?mode=create");
  };

  const handleCancel = () => {
    navigate("/submissions");
  };

  const handleSubmit = async (values: Parameters<typeof createSubmission>[0]) => {
    setSubmitting(true);
    try {
      const submission = await createSubmission(values);
      message.success("提测申请已提交");
      navigate(`/submissions/${submission.id}`);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGenerateChecklist = async (
    changeDescription: string,
    affectedModules: string[]
  ): Promise<GenerateChecklistResponse> => {
    return generateChecklist({
      submissionId: "preview",
      changeDescription,
      affectedModules,
    });
  };

  if (mode === "create") {
    return (
      <div className="submission-create-page">
        <div className="submission-page-header">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/submissions")}
          >
            返回列表
          </Button>
          <Typography.Title level={4} style={{ margin: 0 }}>
            新建提测申请
          </Typography.Title>
        </div>

        <SubmissionForm
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          loading={submitting}
          onGenerateChecklist={handleGenerateChecklist}
        />
      </div>
    );
  }

  return (
    <div className="submission-list-page">
      <div className="submission-list-header">
        <Typography.Title level={4} style={{ margin: 0 }}>
          提测申请
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          新建提测
        </Button>
      </div>

      <div className="submission-filter-bar">
        <Segmented
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(String(val));
            setPage(1);
          }}
          options={STATUS_FILTERS.map((f) => ({
            label: (
              <Space size={4}>
                <span>{f.label}</span>
                {f.value !== "all" && total > 0 && (
                  <span
                    style={{
                      fontSize: 11,
                      padding: "0 6px",
                      borderRadius: 10,
                      background: "var(--bg-inset)",
                    }}
                  >
                    {total}
                  </span>
                )}
              </Space>
            ),
            value: f.value,
          }))}
        />
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <Typography.Text type="secondary">加载中...</Typography.Text>
        </div>
      ) : submissions.length === 0 ? (
        <div className="empty-state" style={{ minHeight: 400 }}>
          <div className="empty-state-icon">
            <PlusOutlined />
          </div>
          <div className="empty-state-text">
            暂无提测申请记录
            <br />
            您的团队还没有提测记录，点击上方「新建提测」开始使用
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
            style={{ marginTop: 16 }}
          >
            新建提测
          </Button>
        </div>
      ) : (
        <div className="submission-grid">
          {submissions.map((submission) => (
            <div
              key={submission.id}
              className="submission-card"
              onClick={() => navigate(`/submissions/${submission.id}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  navigate(`/submissions/${submission.id}`);
                }
              }}
            >
              <div className="submission-card-header">
                <span
                  className="submission-type-tag"
                  style={{
                    background:
                      submission.submissionType === "feature"
                        ? "rgba(0, 113, 227, 0.1)"
                        : submission.submissionType === "bugfix"
                          ? "rgba(255, 159, 10, 0.1)"
                          : "rgba(255, 59, 48, 0.1)",
                    color:
                      submission.submissionType === "feature"
                        ? "var(--color-primary)"
                        : submission.submissionType === "bugfix"
                          ? "var(--color-warning)"
                          : "var(--color-danger)",
                    borderRadius: "var(--radius-xs)",
                    padding: "2px 8px",
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  {submission.submissionType === "feature"
                    ? "功能开发"
                    : submission.submissionType === "bugfix"
                      ? "Bug修复"
                      : "紧急提测"}
                </span>
                <span
                  className="submission-status-tag"
                  style={{
                    background:
                      submission.status === "gate_passed"
                        ? "rgba(88, 86, 214, 0.1)"
                        : submission.status === "self_test_passed"
                          ? "rgba(52, 199, 89, 0.1)"
                          : submission.status === "gate_rejected"
                            ? "rgba(255, 59, 48, 0.1)"
                            : submission.status === "self_test"
                              ? "rgba(0, 113, 227, 0.1)"
                              : "var(--bg-inset)",
                    color:
                      submission.status === "gate_passed"
                        ? "#5856d6"
                        : submission.status === "self_test_passed"
                          ? "var(--color-success)"
                          : submission.status === "gate_rejected"
                            ? "var(--color-danger)"
                            : submission.status === "self_test"
                              ? "var(--color-primary)"
                              : "var(--text-secondary)",
                    borderRadius: "var(--radius-xs)",
                    padding: "2px 8px",
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  {submission.status === "gate_passed"
                    ? "门禁通过"
                    : submission.status === "self_test_passed"
                      ? "自测通过"
                      : submission.status === "gate_rejected"
                        ? "门禁拒绝"
                        : submission.status === "self_test"
                          ? "自测中"
                          : "待处理"}
                </span>
              </div>

              <div style={{ marginTop: 12 }}>
                <Typography.Text strong style={{ fontSize: 15 }}>
                  {submission.version}
                </Typography.Text>
                <Typography.Paragraph
                  ellipsis={{ rows: 2 }}
                  type="secondary"
                  style={{ marginBottom: 0, fontSize: 13 }}
                >
                  {submission.changeDescription}
                </Typography.Paragraph>
              </div>

              {submission.affectedModules.length > 0 && (
                <div className="tag-group" style={{ marginTop: 8 }}>
                  {submission.affectedModules.slice(0, 3).map((m) => (
                    <span
                      key={m}
                      style={{
                        background: "var(--bg-inset)",
                        borderRadius: "var(--radius-xs)",
                        padding: "1px 6px",
                        fontSize: 11,
                        color: "var(--text-secondary)",
                      }}
                    >
                      {m}
                    </span>
                  ))}
                </div>
              )}

              <div
                style={{
                  marginTop: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: 12,
                  color: "var(--text-muted)",
                }}
              >
                <span>
                  {submission.submitter ?? "未知"} ·{" "}
                  {new Date(submission.createdAt).toLocaleDateString("zh-CN")}
                </span>
                {submission.checklists.length > 0 && (
                  <span style={{ color: "var(--color-primary)" }}>
                    {submission.checklists.filter((c) => c.isChecked).length}/
                    {submission.checklists.length}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
