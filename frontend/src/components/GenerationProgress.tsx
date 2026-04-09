import { Button, List, Progress, Space, Typography } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
} from "@ant-design/icons";

import type { TaskStatusPayload } from "../services/api";

interface GenerationProgressProps {
  taskStatus: TaskStatusPayload | null;
  onCancel?: () => void;
  cancelling?: boolean;
}

function phaseIcon(status: string) {
  if (status === "running") {
    return <LoadingOutlined style={{ color: "var(--color-primary)" }} />;
  }
  if (status === "done" || status === "skipped") {
    return <CheckCircleOutlined style={{ color: "var(--color-success)" }} />;
  }
  return <MinusCircleOutlined style={{ color: "var(--text-muted)" }} />;
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m} 分 ${s} 秒`;
}

export function GenerationProgress({
  taskStatus,
  onCancel,
  cancelling,
}: GenerationProgressProps) {
  const progress = taskStatus?.progress ?? 0;
  const elapsed = taskStatus?.elapsedSeconds ?? 0;
  const phases = taskStatus?.phases ?? [];
  const label = taskStatus?.phaseLabel ?? "准备中…";
  const isFinishing = progress >= 0.99 && taskStatus?.status === "running";

  return (
    <div className="generation-progress-panel">
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <div>
          <Space align="center" style={{ width: "100%", justifyContent: "space-between" }}>
            <Typography.Text strong>生成进度</Typography.Text>
            <Space size="small">
              <ClockCircleOutlined style={{ color: "var(--text-muted)" }} />
              <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                已用时 {formatElapsed(elapsed)}
              </Typography.Text>
            </Space>
          </Space>
          <Progress
            percent={Math.round(progress * 100)}
            status="active"
            style={{ marginTop: 8 }}
          />
          <Typography.Paragraph type="secondary" style={{ margin: "8px 0 0", fontSize: 13 }}>
            当前：{isFinishing ? "正在整理并保存结果" : label}
          </Typography.Paragraph>
        </div>

        {phases.length > 0 && (
          <List
            size="small"
            dataSource={phases}
            renderItem={(item) => (
              <List.Item style={{ padding: "6px 0", border: "none" }}>
                <Space>
                  {phaseIcon(String(item.status ?? "pending"))}
                  <span style={{ fontSize: 13 }}>{item.label}</span>
                  {typeof item.elapsedSeconds === "number" && item.elapsedSeconds > 0 && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      ({item.elapsedSeconds}s)
                    </Typography.Text>
                  )}
                </Space>
              </List.Item>
            )}
          />
        )}

        <Typography.Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 12 }}>
          你可以自由浏览其他页面，任务将在后台继续执行。
        </Typography.Paragraph>

        {onCancel && (
          <Button danger size="small" loading={cancelling} onClick={onCancel}>
            取消任务
          </Button>
        )}
      </Space>
    </div>
  );
}
