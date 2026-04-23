import { useMemo } from "react";
import {
  Button,
  Progress,
  Space,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  CloseCircleFilled,
  RightOutlined,
} from "@ant-design/icons";
import type { Submission } from "../../services/submission";

const STATUS_META: Record<
  string,
  { label: string; color: string; icon: React.ReactNode }
> = {
  pending: {
    label: "待处理",
    color: "default",
    icon: <ClockCircleFilled style={{ color: "#86868b" }} />,
  },
  self_test: {
    label: "自测中",
    color: "processing",
    icon: <ExclamationCircleFilled style={{ color: "#0071e3" }} />,
  },
  self_test_passed: {
    label: "自测通过",
    color: "success",
    icon: <CheckCircleFilled style={{ color: "#34c759" }} />,
  },
  gate_passed: {
    label: "门禁通过",
    color: "purple",
    icon: <CheckCircleFilled style={{ color: "#5856d6" }} />,
  },
  gate_rejected: {
    label: "门禁拒绝",
    color: "error",
    icon: <CloseCircleFilled style={{ color: "#ff3b30" }} />,
  },
};

const TYPE_META: Record<string, { label: string; color: string }> = {
  feature: { label: "功能开发", color: "blue" },
  bugfix: { label: "Bug修复", color: "orange" },
  urgent: { label: "紧急提测", color: "red" },
};

interface SubmissionCardProps {
  submission: Submission;
  onClick: () => void;
}

export function SubmissionCard({ submission, onClick }: SubmissionCardProps) {
  const totalChecklists = submission.checklists.length;
  const checkedCount = submission.checklists.filter((c) => c.isChecked).length;
  const highRiskItems = submission.checklists.filter((c) => c.riskLevel === "high");
  const highRiskTotal = highRiskItems.length;
  const highRiskChecked = highRiskItems.filter((c) => c.isChecked).length;
  const allHighRiskChecked = highRiskTotal > 0 && highRiskChecked === highRiskTotal;

  const progress = totalChecklists > 0 ? Math.round((checkedCount / totalChecklists) * 100) : 0;

  const status = STATUS_META[submission.status] ?? STATUS_META.pending;
  const type = TYPE_META[submission.submissionType] ?? TYPE_META.feature;

  const timeAgo = useMemo(() => {
    const diff = Date.now() - new Date(submission.createdAt).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}天前`;
    if (hours > 0) return `${hours}小时前`;
    if (minutes > 0) return `${minutes}分钟前`;
    return "刚刚";
  }, [submission.createdAt]);

  return (
    <div
      className={`submission-card${totalChecklists > 0 && !allHighRiskChecked && highRiskTotal > 0 ? " has-high-risk" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="submission-card-header">
        <Tag color={type.color}>{type.label}</Tag>
        <Tag color={status.color}>
          <Space size={4}>
            {status.icon}
            {status.label}
          </Space>
        </Tag>
      </div>

      <div className="submission-card-title">
        <Typography.Text strong style={{ fontSize: 16 }}>
          {submission.version}
        </Typography.Text>
        <Tooltip title={submission.changeDescription}>
          <Typography.Paragraph
            ellipsis={{ rows: 2 }}
            style={{ marginBottom: 0, color: "var(--text-secondary)" }}
          >
            {submission.changeDescription}
          </Typography.Paragraph>
        </Tooltip>
      </div>

      {submission.affectedModules.length > 0 && (
        <div className="submission-card-modules">
          <Space size={4} wrap>
            {submission.affectedModules.slice(0, 3).map((m) => (
              <Tag key={m} color="geekblue" style={{ fontSize: 11 }}>
                {m}
              </Tag>
            ))}
            {submission.affectedModules.length > 3 && (
              <Tag style={{ fontSize: 11 }}>+{submission.affectedModules.length - 3}</Tag>
            )}
          </Space>
        </div>
      )}

      {totalChecklists > 0 && (
        <div className="submission-card-progress">
          <div className="submission-card-progress-header">
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              检查进度
            </Typography.Text>
            <Typography.Text style={{ fontSize: 12 }}>
              {checkedCount}/{totalChecklists}
            </Typography.Text>
          </div>
          <Progress
            percent={progress}
            size="small"
            strokeColor={allHighRiskChecked ? "var(--color-success)" : "var(--color-primary)"}
            showInfo={false}
          />
          {highRiskTotal > 0 && (
            <Typography.Text
              type={allHighRiskChecked ? "secondary" : "warning"}
              style={{ fontSize: 11 }}
            >
              高风险项: {highRiskChecked}/{highRiskTotal}
              {allHighRiskChecked ? " 已完成" : " 未完成"}
            </Typography.Text>
          )}
        </div>
      )}

      <div className="submission-card-footer">
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {submission.submitter ?? "未知"} · {timeAgo}
        </Typography.Text>
        <Button type="text" size="small" icon={<RightOutlined />} />
      </div>
    </div>
  );
}
