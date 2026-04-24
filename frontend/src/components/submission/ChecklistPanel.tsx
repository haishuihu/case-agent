import { useState, useMemo } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Collapse,
  Input,
  List,
  Modal,
  Progress,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleFilled,
  RobotOutlined,
  WarningFilled,
} from "@ant-design/icons";
import type { ChecklistItem, ChecklistCheckResponse } from "../../services/submission";

const RISK_ORDER = ["high", "medium", "low"] as const;

const RISK_META: Record<string, { label: string; color: string }> = {
  high: { label: "高风险", color: "red" },
  medium: { label: "中风险", color: "orange" },
  low: { label: "低风险", color: "default" },
};

interface ChecklistPanelProps {
  submissionId: string;
  checklists: ChecklistItem[];
  onGenerate: () => Promise<void>;
  onCheck: (
    checklistId: string,
    isChecked: boolean,
    result?: string
  ) => Promise<ChecklistCheckResponse>;
  generating?: boolean;
  loading?: boolean;
}

export function ChecklistPanel({
  submissionId,
  checklists,
  onGenerate,
  onCheck,
  generating,
  loading,
}: ChecklistPanelProps) {
  const [checkModalOpen, setCheckModalOpen] = useState(false);
  const [currentCheck, setCurrentCheck] = useState<{
    id: string;
    item: string;
    isChecked: boolean;
  } | null>(null);
  const [checkResult, setCheckResult] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const groupedChecklists = useMemo(() => {
    const groups: Record<string, ChecklistItem[]> = {};
    for (const item of checklists) {
      const key = item.category || "general";
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    }
    return RISK_ORDER
      .map((risk) => ({
        risk,
        meta: RISK_META[risk],
        items: checklists.filter((c) => c.riskLevel === risk),
      }))
      .filter((g) => g.items.length > 0);
  }, [checklists]);

  const total = checklists.length;
  const checked = checklists.filter((c) => c.isChecked).length;
  const highRiskTotal = checklists.filter((c) => c.riskLevel === "high").length;
  const highRiskChecked = checklists.filter(
    (c) => c.riskLevel === "high" && c.isChecked
  ).length;
  const progress = total > 0 ? Math.round((checked / total) * 100) : 0;

  const handleCheckClick = (item: ChecklistItem) => {
    setCurrentCheck({
      id: item.id,
      item: item.item,
      isChecked: !item.isChecked,
    });
    setCheckResult(item.checkResult ?? "");
    setCheckModalOpen(true);
  };

  const handleCheckSubmit = async () => {
    if (!currentCheck) return;
    setSubmitting(true);
    try {
      await onCheck(currentCheck.id, currentCheck.isChecked, checkResult || undefined);
      setCheckModalOpen(false);
      setCurrentCheck(null);
      setCheckResult("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="checklist-panel">
      <div className="checklist-panel-header">
        <div className="checklist-panel-title">
          <Typography.Title level={5} style={{ margin: 0 }}>
            AI 检查清单
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            基于变更内容自动生成的检查项
          </Typography.Text>
        </div>
        <Button
          icon={<RobotOutlined />}
          onClick={() => void onGenerate()}
          loading={generating}
        >
          重新生成
        </Button>
      </div>

      {checklists.length > 0 && (
        <div className="checklist-progress">
          <div className="checklist-progress-info">
            <Typography.Text>
              检查进度: {checked}/{total}
            </Typography.Text>
            <Typography.Text type="secondary">
              高风险项: {highRiskChecked}/{highRiskTotal}
            </Typography.Text>
          </div>
          <Progress
            percent={progress}
            strokeColor={
              highRiskChecked === highRiskTotal && highRiskTotal > 0
                ? "var(--color-success)"
                : "var(--color-primary)"
            }
            size="small"
          />
          {highRiskTotal > 0 && (
            <Alert
              type={highRiskChecked === highRiskTotal ? "success" : "warning"}
              showIcon
              icon={highRiskChecked === highRiskTotal ? <CheckCircleFilled /> : <WarningFilled />}
              message={
                highRiskChecked === highRiskTotal
                  ? "所有高风险检查项已完成"
                  : `还有 ${highRiskTotal - highRiskChecked} 项高风险检查未完成`
              }
              style={{ marginTop: 8 }}
            />
          )}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}>
          <Spin />
        </div>
      ) : checklists.length === 0 ? (
        <div className="checklist-empty">
          <RobotOutlined style={{ fontSize: 48, color: "var(--border-card)" }} />
          <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
            尚未生成检查清单
          </Typography.Paragraph>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
            点击上方按钮，AI 将根据变更内容自动生成针对性的检查清单
          </Typography.Paragraph>
          <Button type="primary" icon={<RobotOutlined />} onClick={() => void onGenerate()} loading={generating}>
            AI 生成检查清单
          </Button>
        </div>
      ) : (
        <div className="checklist-items">
          {groupedChecklists.map((group) => (
            <div key={group.risk} className="checklist-risk-group">
              <div className="checklist-risk-header">
                <Tag color={group.meta.color}>{group.meta.label}</Tag>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {group.items.filter((i) => i.isChecked).length}/{group.items.length} 已完成
                </Typography.Text>
              </div>
              {group.items.map((item) => (
                <div
                  key={item.id}
                  className={`checklist-item${item.isChecked ? " is-checked" : ""} ${item.riskLevel}-risk`}
                >
                  <div className="checklist-item-check">
                    <Checkbox
                      checked={item.isChecked}
                      onChange={() => void handleCheckClick(item)}
                    />
                  </div>
                  <div className="checklist-item-content">
                    <div className="checklist-item-title">
                      <Typography.Text strong={!item.isChecked}>
                        {item.item}
                      </Typography.Text>
                      {item.isChecked && (
                        <CheckCircleFilled
                          style={{ color: "var(--color-success)", marginLeft: 8 }}
                        />
                      )}
                    </div>
                    {item.checkMethod && (
                      <Typography.Paragraph
                        type="secondary"
                        style={{ fontSize: 12, marginBottom: 4 }}
                      >
                        检查方法: {item.checkMethod}
                      </Typography.Paragraph>
                    )}
                    {item.passCriteria && (
                      <Typography.Paragraph
                        type="secondary"
                        style={{ fontSize: 12, marginBottom: 0 }}
                      >
                        通过标准: {item.passCriteria}
                      </Typography.Paragraph>
                    )}
                    {item.checkResult && (
                      <Alert
                        type="success"
                        message={`检查结果: ${item.checkResult}`}
                        style={{ marginTop: 8 }}
                      />
                    )}
                    {item.checkedBy && (
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        {item.checkedBy}
                        {item.checkedAt
                          ? ` · ${new Date(item.checkedAt).toLocaleString("zh-CN")}`
                          : ""}
                      </Typography.Text>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      <Modal
        title="标记检查结果"
        open={checkModalOpen}
        onCancel={() => {
          setCheckModalOpen(false);
          setCurrentCheck(null);
          setCheckResult("");
        }}
        onOk={() => void handleCheckSubmit()}
        okText="确认"
        cancelText="取消"
        confirmLoading={submitting}
      >
        {currentCheck && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <Typography.Text>
              检查项: <strong>{currentCheck.item}</strong>
            </Typography.Text>
            <Checkbox
              checked={currentCheck.isChecked}
              onChange={(e) =>
                setCurrentCheck((prev) =>
                  prev ? { ...prev, isChecked: e.target.checked } : null
                )
              }
            >
              标记为已检查
            </Checkbox>
            {currentCheck.isChecked && (
              <Input.TextArea
                rows={3}
                placeholder="填写检查结果（可选）"
                value={checkResult}
                onChange={(e) => setCheckResult(e.target.value)}
              />
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
}
