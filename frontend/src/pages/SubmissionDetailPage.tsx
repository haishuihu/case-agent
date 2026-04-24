import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Button,
  Col,
  Divider,
  message,
  Modal,
  Popconfirm,
  Row,
  Skeleton,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  EditOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";

import { ChecklistPanel } from "../components/submission/ChecklistPanel";
import { GateResultPanel } from "../components/submission/GateResultPanel";
import { ImpactAnalysisPanel } from "../components/submission/ImpactAnalysisPanel";
import { RegressionRecommendPanel } from "../components/submission/RegressionRecommendPanel";
import {
  checkChecklist,
  deleteSubmission,
  generateChecklist,
  getSubmission,
  updateSubmission,
  type ChecklistCheckResponse,
  type Submission,
} from "../services/submission";
import {
  createImpactAnalysis,
  getLatestImpactBySubmission,
  type ImpactAnalysis,
} from "../services/impact";

const TYPE_META: Record<string, { label: string; color: string }> = {
  feature: { label: "功能开发", color: "blue" },
  bugfix: { label: "Bug修复", color: "orange" },
  urgent: { label: "紧急提测", color: "red" },
};

const STATUS_META: Record<string, { label: string; color: string }> = {
  pending: { label: "待处理", color: "default" },
  self_test: { label: "自测中", color: "processing" },
  self_test_passed: { label: "自测通过", color: "success" },
  gate_passed: { label: "门禁通过", color: "purple" },
  gate_rejected: { label: "门禁拒绝", color: "error" },
};

export function SubmissionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Sprint 2: 影响分析状态
  const [impactAnalysis, setImpactAnalysis] = useState<ImpactAnalysis | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const loadSubmission = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getSubmission(id);
      setSubmission(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "加载失败";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadImpact = useCallback(async () => {
    if (!id) return;
    setImpactLoading(true);
    try {
      const data = await getLatestImpactBySubmission(id);
      setImpactAnalysis(data);
    } catch {
      setImpactAnalysis(null);
    } finally {
      setImpactLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadSubmission();
    void loadImpact();
  }, [loadSubmission, loadImpact]);

  const handleAnalyze = useCallback(
    async (gitDiff: string) => {
      if (!submission) return;
      setAnalyzing(true);
      try {
        const data = await createImpactAnalysis({
          gitDiff,
          submissionId: submission.id,
          affectedModules: submission.affectedModules,
        });
        setImpactAnalysis(data);
        message.success("影响分析完成");
      } catch (err) {
        message.error(err instanceof Error ? err.message : "分析失败");
      } finally {
        setAnalyzing(false);
      }
    },
    [submission]
  );

  const handleGenerateChecklist = async (): Promise<void> => {
    if (!submission) return;
    setGenerating(true);
    try {
      await generateChecklist({
        submissionId: submission.id,
        changeDescription: submission.changeDescription,
        affectedModules: submission.affectedModules,
        gitDiff: submission.gitDiff ?? undefined,
      });
      message.success("检查清单已生成");
      await loadSubmission();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  };

  const handleCheck = async (
    checklistId: string,
    isChecked: boolean,
    result?: string
  ): Promise<ChecklistCheckResponse> => {
    if (!submission) {
      throw new Error("Submission not loaded");
    }
    try {
      const resp = await checkChecklist({
        checklistId,
        isChecked,
        checkResult: result,
        checkedBy: submission.submitter ?? undefined,
      });
      await loadSubmission();
      if (isChecked) {
        message.success("已标记为通过");
      }
      return resp;
    } catch (err) {
      message.error(err instanceof Error ? err.message : "更新失败");
      throw err;
    }
  };

  const handleStatusChange = async (status: string, reason?: string) => {
    if (!submission) return;
    setUpdating(true);
    try {
      await updateSubmission(submission.id, {
        status,
        ...(reason ? { gateRejectReason: reason } : {}),
      });
      message.success(status === "gate_passed" ? "门禁已通过" : "已标记为拒绝");
      await loadSubmission();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "更新失败");
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!submission) return;
    setDeleting(true);
    try {
      await deleteSubmission(submission.id);
      message.success("已删除提测申请");
      navigate("/submissions");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    );
  }

  if (error || !submission) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          type="error"
          message="加载失败"
          description={error ?? "提测申请不存在"}
          action={
            <Button size="small" onClick={() => navigate("/submissions")}>
              返回列表
            </Button>
          }
        />
      </div>
    );
  }

  const type = TYPE_META[submission.submissionType] ?? TYPE_META.feature;
  const status = STATUS_META[submission.status] ?? STATUS_META.pending;

  return (
    <div className="submission-detail-page">
      <div className="submission-detail-header">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/submissions")}
        >
          返回列表
        </Button>
        <Space>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，是否确认？"
            onConfirm={() => void handleDelete()}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />} loading={deleting}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      </div>

      <div className="submission-detail-title">
        <Typography.Title level={4} style={{ margin: 0 }}>
          {submission.version}
        </Typography.Title>
        <Space>
          <Tag color={type.color}>{type.label}</Tag>
          <Tag color={status.color}>{status.label}</Tag>
        </Space>
      </div>

      <Row gutter={24}>
        <Col xs={24} lg={16}>
          <div className="submission-detail-main">
            <div className="workspace-card" style={{ padding: "var(--space-lg)" }}>
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                变更信息
              </Typography.Title>
              <div className="submission-detail-field">
                <Typography.Text type="secondary">变更描述</Typography.Text>
                <Typography.Paragraph style={{ marginBottom: 0 }}>
                  {submission.changeDescription}
                </Typography.Paragraph>
              </div>

              {submission.affectedModules.length > 0 && (
                <div className="submission-detail-field">
                  <Typography.Text type="secondary">影响模块</Typography.Text>
                  <div className="tag-group">
                    {submission.affectedModules.map((m) => (
                      <Tag key={m} color="geekblue">{m}</Tag>
                    ))}
                  </div>
                </div>
              )}

              <Divider style={{ margin: "16px 0" }} />

              <Row gutter={16}>
                <Col xs={12} md={6}>
                  <div className="submission-detail-stat">
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      变更类型
                    </Typography.Text>
                    <Typography.Text strong>
                      {submission.changeType === "added"
                        ? "新增"
                        : submission.changeType === "modified"
                          ? "修改"
                          : "删除"}
                    </Typography.Text>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div className="submission-detail-stat">
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      自测用例数
                    </Typography.Text>
                    <Typography.Text strong>
                      {submission.selfTestCaseCount}
                    </Typography.Text>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div className="submission-detail-stat">
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      自测覆盖率
                    </Typography.Text>
                    <Typography.Text strong>
                      {submission.selfTestCoverage != null
                        ? `${submission.selfTestCoverage}%`
                        : "-"}
                    </Typography.Text>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div className="submission-detail-stat">
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      冒烟测试
                    </Typography.Text>
                    <Tag
                      color={
                        submission.smokeTestResult === "passed"
                          ? "success"
                          : submission.smokeTestResult === "failed"
                            ? "error"
                            : "default"
                      }
                    >
                      {submission.smokeTestResult === "passed"
                        ? "通过"
                        : submission.smokeTestResult === "failed"
                          ? "失败"
                          : "未执行"}
                    </Tag>
                  </div>
                </Col>
              </Row>

              {(submission.requirementId || submission.requirementLink) && (
                <>
                  <Divider style={{ margin: "16px 0" }} />
                  <Row gutter={16}>
                    {submission.requirementId && (
                      <Col xs={12}>
                        <div className="submission-detail-stat">
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            需求ID
                          </Typography.Text>
                          <Typography.Text>{submission.requirementId}</Typography.Text>
                        </div>
                      </Col>
                    )}
                    {submission.requirementLink && (
                      <Col xs={12}>
                        <div className="submission-detail-stat">
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            需求链接
                          </Typography.Text>
                          <Typography.Link href={submission.requirementLink} target="_blank">
                            打开链接
                          </Typography.Link>
                        </div>
                      </Col>
                    )}
                  </Row>
                </>
              )}

              {(submission.branchName || submission.gitCommitHash) && (
                <>
                  <Divider style={{ margin: "16px 0" }} />
                  <Row gutter={16}>
                    {submission.branchName && (
                      <Col xs={12}>
                        <div className="submission-detail-stat">
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            分支名
                          </Typography.Text>
                          <Typography.Text code>{submission.branchName}</Typography.Text>
                        </div>
                      </Col>
                    )}
                    {submission.gitCommitHash && (
                      <Col xs={12}>
                        <div className="submission-detail-stat">
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            Commit
                          </Typography.Text>
                          <Typography.Text code>{submission.gitCommitHash}</Typography.Text>
                        </div>
                      </Col>
                    )}
                  </Row>
                </>
              )}
            </div>

            <ChecklistPanel
              submissionId={submission.id}
              checklists={submission.checklists}
              onGenerate={handleGenerateChecklist}
              onCheck={handleCheck}
              generating={generating}
            />

            <ImpactAnalysisPanel
              submissionId={submission.id}
              impactAnalysis={impactAnalysis}
              loading={impactLoading}
              analyzing={analyzing}
              onAnalyze={handleAnalyze}
              defaultDiff={submission.gitDiff ?? undefined}
            />

            <RegressionRecommendPanel
              submissionId={submission.id}
              impactAnalysis={impactAnalysis}
            />
          </div>
        </Col>

        <Col xs={24} lg={8}>
          <div className="submission-detail-sidebar">
            <GateResultPanel
              submission={submission}
              onStatusChange={handleStatusChange}
            />

            <div className="workspace-card" style={{ padding: "var(--space-lg)", marginTop: "var(--space-md)" }}>
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                提测信息
              </Typography.Title>
              <div className="submission-detail-field">
                <Typography.Text type="secondary">提交人</Typography.Text>
                <Typography.Text>{submission.submitter ?? "-"}</Typography.Text>
              </div>
              <div className="submission-detail-field">
                <Typography.Text type="secondary">提交时间</Typography.Text>
                <Typography.Text>
                  {new Date(submission.createdAt).toLocaleString("zh-CN")}
                </Typography.Text>
              </div>
              {submission.reviewedBy && (
                <div className="submission-detail-field">
                  <Typography.Text type="secondary">审核人</Typography.Text>
                  <Typography.Text>{submission.reviewedBy}</Typography.Text>
                </div>
              )}
            </div>
          </div>
        </Col>
      </Row>
    </div>
  );
}
