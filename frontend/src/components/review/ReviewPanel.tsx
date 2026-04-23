import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Collapse,
  Divider,
  Input,
  List,
  Progress,
  Result,
  Select,
  Skeleton,
  Space,
  Spin,
  Tag,
  Typography,
  Modal,
  Tooltip,
  message,
} from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CommentOutlined,
  DislikeOutlined,
  LikeOutlined,
  QuestionCircleOutlined,
  SafetyCertificateOutlined,
  SolutionOutlined,
  ThunderboltOutlined,
  UserSwitchOutlined,
} from "@ant-design/icons";
import {
  type CaseReview,
  type ReviewComment,
  createReview,
  runAIReview,
  addComment,
  updateReviewStatus,
  listComments,
} from "../../services/review";

interface ReviewPanelProps {
  requirementText: string;
  documentFiles: File[];
  imageFiles: File[];
  modelKey?: string;
  generatedCases?: string;
  caseTitle?: string;
  generationId?: string;
}

type ReviewPhase = "idle" | "creating" | "reviewing" | "done" | "error";

const DIMENSION_LABELS: Record<string, string> = {
  missing_coverage: "覆盖缺失",
  executability: "可执行性",
  consistency: "一致性",
  redundancy: "冗余性",
  boundary: "边界条件",
  error_handling: "异常处理",
  data_validation: "数据校验",
  integration: "集成场景",
  completeness: "完整性",
  coverage: "覆盖率",
};

const SEVERITY_COLORS: Record<string, string> = {
  high: "red",
  medium: "orange",
  low: "blue",
};

const STATUS_OPTIONS = [
  { value: "pending", label: "待评审" },
  { value: "in_review", label: "评审中" },
  { value: "approved", label: "已通过" },
  { value: "needs_revision", label: "需修改" },
];

const DIMENSION_WEIGHTS: Record<string, number> = {
  completeness: 25,
  executability: 25,
  consistency: 20,
  redundancy: 15,
  coverage: 15,
};

function computeOverall(
  details: CaseReview["aiReviewDetails"]
): number | null {
  if (!details) return null;
  const dims = details.dimensions;
  if (!dims || dims.length === 0) return null;
  const scores: Record<string, number> = {};
  for (const d of dims) {
    scores[d.dimension] = d.score;
  }
  let total = 0;
  let weightSum = 0;
  for (const [dim, weight] of Object.entries(DIMENSION_WEIGHTS)) {
    if (scores[dim] !== undefined) {
      total += scores[dim] * (weight / 100);
      weightSum += weight;
    }
  }
  return weightSum > 0 ? Math.round(total / (weightSum / 100)) : null;
}

export function ReviewPanel({
  requirementText,
  documentFiles,
  imageFiles,
  modelKey,
  generatedCases,
  caseTitle,
  generationId,
}: ReviewPanelProps) {
  const [phase, setPhase] = useState<ReviewPhase>("idle");
  const [review, setReview] = useState<CaseReview | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [commentInput, setCommentInput] = useState("");
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [reviewerName, setReviewerName] = useState<string>("");
  const [decisionLoading, setDecisionLoading] = useState(false);

  const handleRunReview = async () => {
    setPhase("creating");
    setErrorMessage("");
    try {
      const result = await runAIReview({
        requirementText,
        generatedCases,
        caseTitle,
        generationId,
        modelKey,
      });
      setReview(result);
      setPhase("done");
      setComments(result.comments || []);
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "评审失败，请稍后重试。");
      setPhase("error");
    }
  };

  const handleReset = () => {
    setPhase("idle");
    setReview(null);
    setErrorMessage("");
    setCommentInput("");
    setComments([]);
    setShowCommentForm(false);
  };

  const handleAddComment = async () => {
    if (!review || !commentInput.trim()) return;
    try {
      const comment = await addComment(review.id, {
        author: reviewerName || undefined,
        content: commentInput,
      });
      setComments((prev) => [...prev, comment]);
      setCommentInput("");
      message.success("评论已添加");
    } catch (e) {
      message.error("添加评论失败");
    }
  };

  const handleDecision = async (decision: "approved" | "needs_revision") => {
    if (!review) return;
    setDecisionLoading(true);
    try {
      const status = decision === "approved" ? "approved" : "needs_revision";
      const updated = await updateReviewStatus(review.id, {
        reviewStatus: status,
        decision,
        reviewer: reviewerName || undefined,
        reviewerComment: commentInput || undefined,
      });
      setReview(updated);
      message.success(decision === "approved" ? "评审已通过" : "已标记为需修改");
      setCommentInput("");
    } catch (e) {
      message.error("更新状态失败");
    } finally {
      setDecisionLoading(false);
    }
  };

  const canRun = requirementText.trim().length > 0 || documentFiles.length > 0 || imageFiles.length > 0 || generatedCases;

  // ── Idle state ─────────────────────────────────────────────
  if (phase === "idle") {
    return (
      <Card size="small" style={{ marginTop: 16 }}>
        <Space style={{ width: "100%", justifyContent: "space-between" }}>
          <div>
            <Typography.Text strong>
              <SafetyCertificateOutlined style={{ marginRight: 6 }} />
              用例评审
            </Typography.Text>
            <Typography.Paragraph
              type="secondary"
              style={{ marginBottom: 0, fontSize: 13, marginTop: 4 }}
            >
              AI 多维度评审 + 人工评审协作
            </Typography.Paragraph>
          </div>
          <Button
            type="default"
            icon={<ThunderboltOutlined />}
            onClick={() => void handleRunReview()}
            disabled={!canRun}
          >
            开始评审
          </Button>
        </Space>
      </Card>
    );
  }

  // ── Creating / Reviewing state ─────────────────────────────
  if (phase === "creating" || phase === "reviewing") {
    return (
      <Card size="small" style={{ marginTop: 16 }}>
        <Space style={{ width: "100%", justifyContent: "center" }} direction="vertical" align="center">
          <Spin size="large" />
          <Typography.Text type="secondary">
            {phase === "creating" ? "正在创建评审记录..." : "AI 正在评审测试用例，请稍候..."}
          </Typography.Text>
        </Space>
      </Card>
    );
  }

  // ── Error state ────────────────────────────────────────────
  if (phase === "error") {
    return (
      <Card size="small" style={{ marginTop: 16 }}>
        <Result
          status="error"
          title="评审失败"
          subTitle={errorMessage}
          extra={
            <Space>
              <Button onClick={() => void handleReset()}>重新评审</Button>
              <Button type="primary" onClick={() => void handleRunReview()}>
                重试
              </Button>
            </Space>
          }
        />
      </Card>
    );
  }

  // ── Done state ─────────────────────────────────────────────
  const r = review!;
  const overallScore = computeOverall(r.aiReviewDetails);
  const scoreColor = overallScore !== null
    ? overallScore >= 80 ? "#52c41a" : overallScore >= 60 ? "#faad14" : "#ff4d4f"
    : undefined;

  const collapseItems = [
    // 评分总览
    overallScore !== null
      ? {
          key: "score",
          label: (
            <Space>
              <CheckCircleOutlined style={{ color: "#52c41a" }} />
              <span><strong>综合评分</strong>（{overallScore}/100）</span>
            </Space>
          ),
          children: (
            <div>
              {r.aiReviewDetails?.dimensions.map((dim) => (
                <div key={dim.dimension} style={{ marginBottom: 8 }}>
                  <Space style={{ width: "100%", justifyContent: "space-between" }}>
                    <Typography.Text>{dim.label}</Typography.Text>
                    <Tag color={dim.score >= 80 ? "green" : dim.score >= 60 ? "orange" : "red"}>
                      {dim.score}/100
                    </Tag>
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
        }
      : null,
    // 模块拆解
    r.aiReviewDetails && r.aiReviewDetails.issues.some(i => i.type === "missing_coverage" || i.type === "coverage")
      ? {
          key: "modules",
          label: (
            <Space>
              <SolutionOutlined />
              <span><strong>问题详情</strong>（{r.aiReviewDetails.issues.length} 项）</span>
            </Space>
          ),
          children: (
            <div>
              {r.aiReviewDetails.issues.map((issue, idx) => (
                <Alert
                  key={idx}
                  type={issue.severity === "high" ? "error" : issue.severity === "medium" ? "warning" : "info"}
                  showIcon
                  style={{ marginBottom: 8 }}
                  message={
                    <Space>
                      <Tag color={SEVERITY_COLORS[issue.severity] ?? "default"} style={{ fontSize: 11 }}>
                        {DIMENSION_LABELS[issue.type] ?? issue.type}
                      </Tag>
                      <span>{issue.description}</span>
                    </Space>
                  }
                  description={
                    issue.recommendation ? (
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        建议：{issue.recommendation}
                      </Typography.Text>
                    ) : undefined
                  }
                />
              ))}
            </div>
          ),
        }
      : null,
    // 评审意见
    comments.length > 0
      ? {
          key: "comments",
          label: (
            <Space>
              <CommentOutlined style={{ color: "#1890ff" }} />
              <span><strong>评审评论</strong>（{comments.length} 条）</span>
            </Space>
          ),
          children: (
            <List
              size="small"
              dataSource={comments}
              renderItem={(c) => (
                <List.Item style={{ padding: "8px 0" }}>
                  <div style={{ width: "100%" }}>
                    <Space>
                      <Typography.Text strong>{c.author ?? "匿名"}</Typography.Text>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(c.createdAt).toLocaleString("zh-CN")}
                      </Typography.Text>
                    </Space>
                    <Typography.Paragraph style={{ marginBottom: 0, marginTop: 4 }}>
                      {c.content}
                    </Typography.Paragraph>
                  </div>
                </List.Item>
              )}
            />
          ),
        }
      : null,
  ].filter(Boolean) as Collapse["items"];

  return (
    <Card
      size="small"
      style={{ marginTop: 16 }}
      title={
        <Space>
          <SafetyCertificateOutlined />
          <span>评审结果</span>
          {r.aiReviewDetails && (
            <Tag color={scoreColor === "#52c41a" ? "green" : scoreColor === "#faad14" ? "orange" : "red"}>
              {overallScore}/100
            </Tag>
          )}
          <Tag
            color={
              r.reviewStatus === "approved" ? "green"
                : r.reviewStatus === "needs_revision" ? "red"
                : r.reviewStatus === "in_review" ? "blue"
                : "default"
            }
          >
            {STATUS_OPTIONS.find((o) => o.value === r.reviewStatus)?.label ?? r.reviewStatus}
          </Tag>
        </Space>
      }
      extra={
        <Space>
          <Button size="small" onClick={() => void handleReset()}>
            重新评审
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => void handleRunReview()}
          >
            刷新评审
          </Button>
        </Space>
      }
    >
      {/* 状态流转操作区 */}
      <Space style={{ marginBottom: 12 }} wrap>
        <Input
          placeholder="评审人姓名（选填）"
          style={{ width: 140 }}
          size="small"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
        />
        {r.reviewStatus !== "approved" && r.reviewStatus !== "needs_revision" && (
          <>
            <Tooltip title="同意当前评审结果">
              <Button
                size="small"
                icon={<LikeOutlined />}
                type="primary"
                loading={decisionLoading}
                onClick={() => void handleDecision("approved")}
              >
                同意
              </Button>
            </Tooltip>
            <Tooltip title="标记为需要修改">
              <Button
                size="small"
                icon={<DislikeOutlined />}
                danger
                loading={decisionLoading}
                onClick={() => void handleDecision("needs_revision")}
              >
                需修改
              </Button>
            </Tooltip>
          </>
        )}
        <Button
          size="small"
          icon={<CommentOutlined />}
          onClick={() => setShowCommentForm(!showCommentForm)}
        >
          添加评论
        </Button>
      </Space>

      {showCommentForm && (
        <div style={{ marginBottom: 12, padding: 12, background: "#f5f5f5", borderRadius: 6 }}>
          <Input.TextArea
            placeholder="添加评审意见..."
            rows={2}
            value={commentInput}
            onChange={(e) => setCommentInput(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <Button type="primary" size="small" onClick={() => void handleAddComment()}>
            提交评论
          </Button>
        </div>
      )}

      {collapseItems.length === 0 ? (
        <Result
          status="success"
          title="未发现问题"
          subTitle="AI 评审未发现明显问题，当前用例覆盖良好。"
        />
      ) : (
        <Collapse items={collapseItems} defaultActiveKey={["score"]} />
      )}
    </Card>
  );
}
