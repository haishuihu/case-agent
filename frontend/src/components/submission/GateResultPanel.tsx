import { useState } from "react";
import {
  Alert,
  Button,
  Input,
  Modal,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleFilled,
  WarningFilled,
} from "@ant-design/icons";
import type { Submission, GateResult } from "../../services/submission";

const STATUS_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending: {
    label: "待处理",
    color: "default",
    icon: <ExclamationCircleFilled style={{ color: "#86868b" }} />,
  },
  self_test: {
    label: "自测中",
    color: "processing",
    icon: <ExclamationCircleFilled style={{ color: "var(--color-primary)" }} />,
  },
  self_test_passed: {
    label: "自测通过",
    color: "success",
    icon: <CheckCircleFilled style={{ color: "#34c759" }} />,
  },
  gate_passed: {
    label: "门禁通过",
    color: "purple",
    icon: <CheckCircleFilled style={{ color: "var(--color-primary)" }} />,
  },
  gate_rejected: {
    label: "门禁拒绝",
    color: "error",
    icon: <CloseCircleFilled style={{ color: "#ff3b30" }} />,
  },
};

interface GateResultPanelProps {
  submission: Submission;
  onStatusChange?: (status: string, reason?: string) => Promise<void>;
}

export function GateResultPanel({ submission, onStatusChange }: GateResultPanelProps) {
  const [gateModalOpen, setGateModalOpen] = useState(false);
  const [gateAction, setGateAction] = useState<"pass" | "reject">("pass");
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const status = STATUS_META[submission.status] ?? STATUS_META.pending;
  const gateResult = submission.gateResult as GateResult | null | undefined;

  const canGate = submission.status === "self_test_passed";

  const handleGateAction = async () => {
    if (!onStatusChange) return;
    setSubmitting(true);
    try {
      if (gateAction === "reject") {
        await onStatusChange("gate_rejected", rejectReason);
      } else {
        await onStatusChange("gate_passed");
      }
      setGateModalOpen(false);
      setRejectReason("");
    } finally {
      setSubmitting(false);
    }
  };

  const openGateModal = (action: "pass" | "reject") => {
    setGateAction(action);
    setGateModalOpen(true);
  };

  return (
    <div className={`gate-result-panel${submission.status === "gate_passed" ? " passed" : submission.status === "gate_rejected" ? " rejected" : ""}`}>
      <div className="gate-result-header">
        <div className="gate-result-status">
          <Typography.Title level={5} style={{ margin: 0 }}>
            门禁状态
          </Typography.Title>
          <Tag color={status.color} icon={status.icon}>
            {status.label}
          </Tag>
        </div>
        {canGate && onStatusChange && (
          <Space>
            <Button
              type="primary"
              icon={<CheckCircleFilled />}
              onClick={() => openGateModal("pass")}
              style={{ background: "var(--color-success)" }}
            >
              审核通过
            </Button>
            <Button
              danger
              icon={<CloseCircleFilled />}
              onClick={() => openGateModal("reject")}
            >
              审核拒绝
            </Button>
          </Space>
        )}
      </div>

      {submission.gateRejectReason && (
        <Alert
          type="error"
          showIcon
          icon={<WarningFilled />}
          message="拒绝原因"
          description={submission.gateRejectReason}
          style={{ marginBottom: 16 }}
        />
      )}

      {gateResult ? (
        <>
          {gateResult.summary && (
            <div className="gate-result-section">
              <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                风险评估摘要
              </Typography.Text>
              <Alert
                type="info"
                showIcon={false}
                message={gateResult.summary}
                style={{ marginTop: 8, background: "rgba(0, 0, 0, 0.06)", borderColor: "rgba(0, 0, 0, 0.06)" }}
              />
            </div>
          )}

          {gateResult.suggestions && gateResult.suggestions.length > 0 && (
            <div className="gate-result-section" style={{ marginTop: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                建议
              </Typography.Text>
              <ul className="gate-result-list" style={{ marginTop: 8, paddingLeft: 20 }}>
                {gateResult.suggestions.map((s, i) => (
                  <li key={i}>
                    <Typography.Text style={{ fontSize: 13 }}>{s}</Typography.Text>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {gateResult.highRiskAreas && gateResult.highRiskAreas.length > 0 && (
            <div className="gate-result-section" style={{ marginTop: 16 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                高风险区域
              </Typography.Text>
              <div className="tag-group" style={{ marginTop: 8 }}>
                {gateResult.highRiskAreas.map((area, i) => (
                  <Tag key={i} color="red" style={{ borderRadius: "var(--radius-xs)" }}>
                    {area}
                  </Tag>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <Alert
          type="info"
          showIcon
          message="尚未生成门禁分析"
          description="提交提测后，系统将根据变更内容自动分析风险并生成门禁建议"
          style={{ marginTop: 8 }}
        />
      )}

      <Modal
        title={gateAction === "pass" ? "确认门禁通过" : "确认门禁拒绝"}
        open={gateModalOpen}
        onCancel={() => {
          setGateModalOpen(false);
          setRejectReason("");
        }}
        onOk={() => void handleGateAction()}
        okText={gateAction === "pass" ? "确认通过" : "确认拒绝"}
        cancelText="取消"
        confirmLoading={submitting}
        okButtonProps={gateAction === "reject" ? { danger: true } : { style: { background: "var(--color-success)" } }}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          {gateAction === "pass" ? (
            <Alert
              type="success"
              message="确认该提测已通过所有检查，门禁放行"
              showIcon
            />
          ) : (
            <>
              <Alert
                type="error"
                message="请填写拒绝原因"
                showIcon
              />
              <Input.TextArea
                rows={3}
                placeholder="请输入拒绝原因"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </>
          )}
        </Space>
      </Modal>
    </div>
  );
}
