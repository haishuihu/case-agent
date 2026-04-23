import {
  Button,
  Empty,
  Spin,
  Typography,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { SubmissionCard } from "./SubmissionCard";
import type { Submission } from "../../services/submission";

interface SubmissionListProps {
  submissions: Submission[];
  loading?: boolean;
  onItemClick: (id: string) => void;
  onCreate: () => void;
}

export function SubmissionList({
  submissions,
  loading,
  onItemClick,
  onCreate,
}: SubmissionListProps) {
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 60 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <div className="empty-state" style={{ minHeight: 400 }}>
        <div className="empty-state-icon">
          <PlusOutlined />
        </div>
        <div className="empty-state-text">
          暂无提测申请记录
          <br />
          您的团队还没有提测记录，点击上方「新建提测」开始使用
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={onCreate} style={{ marginTop: 16 }}>
          新建提测
        </Button>
      </div>
    );
  }

  return (
    <div className="submission-grid">
      {submissions.map((submission) => (
        <SubmissionCard
          key={submission.id}
          submission={submission}
          onClick={() => onItemClick(submission.id)}
        />
      ))}
    </div>
  );
}
