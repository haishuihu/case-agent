import { useState, useMemo, useCallback } from "react";
import {
  Button,
  Card,
  Collapse,
  Divider,
  Empty,
  message,
  Modal,
  Progress,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  CheckCircleFilled,
  CheckCircleOutlined,
  CloseCircleFilled,
  ClockCircleOutlined,
  MinusCircleOutlined,
  RollbackOutlined,
  WarningFilled,
} from "@ant-design/icons";
import type { ImpactAnalysis } from "../../services/impact";
import {
  updateExecutionStatus,
  type ExecutionStatus,
} from "../../services/regression_execution";

const PRIORITY_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  must: { label: "必须回归", color: "red", icon: <WarningFilled /> },
  should: { label: "建议回归", color: "orange", icon: <CheckCircleFilled /> },
  could: { label: "可选回归", color: "default", icon: <CheckCircleFilled /> },
};

const RISK_META: Record<string, { label: string; color: string }> = {
  high: { label: "高风险", color: "red" },
  medium: { label: "中风险", color: "orange" },
  low: { label: "低风险", color: "default" },
};

const EXECUTION_META: Record<ExecutionStatus, { label: string; color: string; icon: React.ReactNode }> = {
  not_started: { label: "未开始", color: "default", icon: <MinusCircleOutlined /> },
  in_progress: { label: "进行中", color: "processing", icon: <ClockCircleOutlined /> },
  passed: { label: "通过", color: "success", icon: <CheckCircleOutlined /> },
  failed: { label: "失败", color: "error", icon: <CloseCircleFilled /> },
  blocked: { label: "阻塞", color: "warning", icon: <WarningFilled /> },
};

const ALL_EXEC_STATUSES: ExecutionStatus[] = [
  "not_started",
  "in_progress",
  "passed",
  "failed",
  "blocked",
];

interface RegressionRecommendPanelProps {
  submissionId: string;
  impactAnalysis: ImpactAnalysis | null;
}

export function RegressionRecommendPanel({
  submissionId,
  impactAnalysis,
}: RegressionRecommendPanelProps) {
  const [couldOpen, setCouldOpen] = useState(false);
  const [execStatusMap, setExecStatusMap] = useState<Record<string, ExecutionStatus>>({});
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [modalRecId, setModalRecId] = useState<string | null>(null);
  const [modalStatus, setModalStatus] = useState<ExecutionStatus>("not_started");
  const [modalResult, setModalResult] = useState("");
  const [modalComment, setModalComment] = useState("");
  const [messageApi, contextHolder] = message.useMessage();

  const getStatus = useCallback(
    (recId: string): ExecutionStatus => {
      if (execStatusMap[recId] !== undefined) return execStatusMap[recId];
      const rec = impactAnalysis?.recommendations.find((r) => r.id === recId);
      return (rec?.executionStatus as ExecutionStatus) ?? "not_started";
    },
    [execStatusMap, impactAnalysis]
  );

  const handleStatusClick = (recId: string, status: ExecutionStatus) => {
    setModalRecId(recId);
    setModalStatus(status);
    setModalResult("");
    setModalComment("");
  };

  const handleModalConfirm = async () => {
    if (!modalRecId) return;
    setUpdatingId(modalRecId);
    try {
      const result = await updateExecutionStatus(modalRecId, {
        status: modalStatus,
        actualResult: modalResult || undefined,
        comment: modalComment || undefined,
      });
      setExecStatusMap((prev) => ({ ...prev, [modalRecId]: result.status }));
      messageApi.success("执行状态已更新");
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "更新失败");
    } finally {
      setUpdatingId(null);
      setModalRecId(null);
    }
  };

  const { must, should, could, total } = useMemo(() => {
    if (!impactAnalysis?.recommendations) {
      return { must: [], should: [], could: [], total: { must: 0, should: 0, could: 0 } };
    }

    const recs = impactAnalysis.recommendations;
    const must_ = recs.filter((r) => r.priority === "must");
    const should_ = recs.filter((r) => r.priority === "should");
    const could_ = recs.filter((r) => r.priority === "could");

    const sumMinutes = (items: typeof recs) =>
      items.reduce((acc, r) => acc + (r.estimatedMinutes ?? 0), 0);

    return {
      must: must_,
      should: should_,
      could: could_,
      total: {
        must: sumMinutes(must_),
        should: sumMinutes(should_),
        could: sumMinutes(could_),
      },
    };
  }, [impactAnalysis]);

  const grandTotal = total.must + total.should + total.could;

  // mustDone: count of must items that are passed/failed/blocked
  const mustDone = useMemo(
    () => must.filter((r) => {
      const s = getStatus(r.id);
      return s === "passed" || s === "failed" || s === "blocked";
    }).length,
    [must, getStatus]
  );

  if (!impactAnalysis) return null;
  const recCount = impactAnalysis.recommendations.length;
  if (recCount === 0) return null;

  return (
    <>
      {contextHolder}
      <Card className="regression-panel">
        <div className="regression-panel-header">
          <div className="regression-panel-title">
            <Typography.Title level={5} style={{ margin: 0 }}>
              回归测试推荐
            </Typography.Title>
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              共 {recCount} 项推荐用例
            </Typography.Text>
          </div>
          <Tag icon={<RollbackOutlined />} color="blue">
            预估 {grandTotal} 分钟
          </Tag>
        </div>

        <Divider style={{ margin: "12px 0" }} />

        {/* 总览进度 */}
        {grandTotal > 0 && (
          <div className="regression-summary">
            <div className="regression-summary-bars">
              {total.must > 0 && (
                <div className="regression-bar must">
                  <Typography.Text style={{ fontSize: 12 }}>必须</Typography.Text>
                  <Progress
                    percent={100}
                    success={{ percent: must.length > 0 ? Math.round((mustDone / must.length) * 100) : 0 }}
                    strokeColor="var(--color-danger)"
                    size="small"
                    showInfo={false}
                    style={{ flex: 1 }}
                  />
                  <Typography.Text style={{ fontSize: 12, minWidth: 60, textAlign: "right" }}>
                    {mustDone}/{must.length}
                  </Typography.Text>
                </div>
              )}
              {total.should > 0 && (
                <div className="regression-bar should">
                  <Typography.Text style={{ fontSize: 12 }}>建议</Typography.Text>
                  <Progress
                    percent={100}
                    strokeColor="var(--color-warning, #faad14)"
                    size="small"
                    showInfo={false}
                    style={{ flex: 1 }}
                  />
                  <Typography.Text style={{ fontSize: 12, minWidth: 60, textAlign: "right" }}>
                    {total.should} 分钟
                  </Typography.Text>
                </div>
              )}
              {total.could > 0 && (
                <div className="regression-bar could">
                  <Typography.Text style={{ fontSize: 12 }}>可选</Typography.Text>
                  <Progress
                    percent={100}
                    strokeColor="var(--border-card)"
                    size="small"
                    showInfo={false}
                    style={{ flex: 1 }}
                  />
                  <Typography.Text style={{ fontSize: 12, minWidth: 60, textAlign: "right" }}>
                    {total.could} 分钟
                  </Typography.Text>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 必须回归 */}
        {must.length > 0 && (
          <div className="regression-priority-group must">
            <div className="regression-group-header">
              <Tag color="red" icon={PRIORITY_META.must.icon}>
                {PRIORITY_META.must.label}（{must.length} 项）
              </Tag>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                共 {total.must} 分钟，已完成 {mustDone}/{must.length}
              </Typography.Text>
            </div>
            {must.map((rec) => (
              <RegressionItem
                key={rec.id}
                rec={rec}
                status={getStatus(rec.id)}
                updating={updatingId === rec.id}
                onStatusClick={(s) => handleStatusClick(rec.id, s)}
              />
            ))}
          </div>
        )}

        {/* 建议回归 */}
        {should.length > 0 && (
          <div className="regression-priority-group should">
            <div className="regression-group-header">
              <Tag color="orange" icon={PRIORITY_META.should.icon}>
                {PRIORITY_META.should.label}（{should.length} 项）
              </Tag>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                共 {total.should} 分钟
              </Typography.Text>
            </div>
            {should.map((rec) => (
              <RegressionItem
                key={rec.id}
                rec={rec}
                status={getStatus(rec.id)}
                updating={updatingId === rec.id}
                onStatusClick={(s) => handleStatusClick(rec.id, s)}
              />
            ))}
          </div>
        )}

        {/* 可选回归（折叠） */}
        {could.length > 0 && (
          <Collapse
            ghost
            activeKey={couldOpen ? ["could"] : []}
            onChange={(keys) => setCouldOpen(keys.includes("could"))}
            items={[
              {
                key: "could",
                label: (
                  <Space>
                    <Tag color="default" icon={PRIORITY_META.could.icon}>
                      {PRIORITY_META.could.label}（{could.length} 项）
                    </Tag>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      共 {total.could} 分钟
                    </Typography.Text>
                  </Space>
                ),
                children: could.map((rec) => (
                  <RegressionItem
                    key={rec.id}
                    rec={rec}
                    status={getStatus(rec.id)}
                    updating={updatingId === rec.id}
                    onStatusClick={(s) => handleStatusClick(rec.id, s)}
                  />
                )),
              },
            ]}
            style={{ marginTop: 8 }}
          />
        )}

        {/* 总计 */}
        <Divider style={{ margin: "12px 0" }} />
        <div className="regression-total">
          <Typography.Text strong>预估总时间</Typography.Text>
          <Typography.Text strong style={{ color: "var(--color-primary)" }}>
            {grandTotal} 分钟
          </Typography.Text>
        </div>
      </Card>

      {/* 状态更新弹窗 */}
      <Modal
        title={`更新执行状态：${modalRecId ? impactAnalysis?.recommendations.find((r) => r.id === modalRecId)?.caseTitle ?? modalRecId.slice(0, 8) : ""}`}
        open={modalRecId !== null}
        onOk={() => void handleModalConfirm()}
        onCancel={() => setModalRecId(null)}
        okText="确认更新"
        confirmLoading={updatingId !== null}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
              执行状态
            </Typography.Text>
            <Space wrap>
              {ALL_EXEC_STATUSES.map((s) => {
                const meta = EXECUTION_META[s];
                return (
                  <Tag
                    key={s}
                    icon={meta.icon}
                    color={modalStatus === s ? meta.color : "default"}
                    style={{ cursor: "pointer", fontSize: 13, padding: "2px 8px" }}
                    onClick={() => setModalStatus(s)}
                  >
                    {meta.label}
                  </Tag>
                );
              })}
            </Space>
          </div>
          <div>
            <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
              实际结果（选填）
            </Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>
              记录实际执行的结果，用于后续复盘
            </Typography.Text>
            <Typography.TextArea
              rows={3}
              placeholder="请描述实际执行结果..."
              value={modalResult}
              onChange={(e) => setModalResult(e.target.value)}
            />
          </div>
          <div>
            <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
              备注（选填）
            </Typography.Text>
            <Typography.TextArea
              rows={2}
              placeholder="补充说明..."
              value={modalComment}
              onChange={(e) => setModalComment(e.target.value)}
            />
          </div>
        </Space>
      </Modal>
    </>
  );
}

function RegressionItem({
  rec,
  status,
  updating,
  onStatusClick,
}: {
  rec: ImpactAnalysis["recommendations"][0];
  status: ExecutionStatus;
  updating: boolean;
  onStatusClick: (s: ExecutionStatus) => void;
}) {
  const riskMeta = RISK_META[rec.riskLevel] ?? RISK_META.low;
  const execMeta = EXECUTION_META[status] ?? EXECUTION_META.not_started;

  return (
    <div className="regression-item">
      <div className="regression-item-header">
        <Space size={4} wrap>
          <Tag
            icon={execMeta.icon}
            color={execMeta.color}
            style={{ cursor: "pointer", fontSize: 11 }}
            onClick={() => onStatusClick(status)}
          >
            {execMeta.label}
          </Tag>
          {rec.caseTitle ? (
            <Typography.Text strong style={{ fontSize: 13 }}>
              {rec.caseTitle}
            </Typography.Text>
          ) : (
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              (未命名用例)
            </Typography.Text>
          )}
          <Tag color={riskMeta.color} style={{ marginRight: 0 }}>
            {riskMeta.label}
          </Tag>
          {rec.category && (
            <Tag style={{ marginRight: 0 }}>{rec.category}</Tag>
          )}
        </Space>
        {rec.estimatedMinutes && (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {rec.estimatedMinutes} 分钟
          </Typography.Text>
        )}
      </div>
      {rec.reason && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {rec.reason}
        </Typography.Text>
      )}
      {updating && (
        <Typography.Text type="secondary" style={{ fontSize: 12, display: "block" }}>
          更新中...
        </Typography.Text>
      )}
    </div>
  );
}
