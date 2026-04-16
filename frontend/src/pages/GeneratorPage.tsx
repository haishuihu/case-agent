import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Col, Drawer, Input, Modal, Row, Space, Spin, Tag, Typography, message } from "antd";
import {
  ThunderboltOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  ReloadOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import type { UploadFile, UploadProps } from "antd/es/upload/interface";

import { RequirementInput } from "../components/RequirementInput";
import { ResultPreview } from "../components/ResultPreview";
import { useGenerationTask } from "../context/GenerationTaskContext";
import {
  clearAllGenerationTasks,
  getTaskStatus,
  listGenerationTasks,
  listModels,
  submitGenerateAsync,
  summarizeRequirementFromFiles,
  type GenerateResult,
  type ModelOption,
  type RequirementSummaryResult,
  type TaskListItemPayload,
} from "../services/api";

const { TextArea } = Input;

function normalizeFiles(fileList: UploadFile[]): File[] {
  return fileList.flatMap((file) => {
    const originFile = file.originFileObj;
    return originFile ? [originFile as File] : [];
  });
}

export function GeneratorPage() {
  const [messageApi, contextHolder] = message.useMessage();
  const {
    taskId,
    taskStatus,
    result: ctxResult,
    pollError,
    startTask,
    stopPolling,
    isRunning,
    cancelActiveTask,
  } = useGenerationTask();

  const [requirementText, setRequirementText] = useState("");
  const [documentFileList, setDocumentFileList] = useState<UploadFile[]>([]);
  const [imageFileList, setImageFileList] = useState<UploadFile[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [selectedModelKey, setSelectedModelKey] = useState<string>();
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);
  const [summaryDraft, setSummaryDraft] = useState("");
  const [summaryPreview, setSummaryPreview] = useState<RequirementSummaryResult | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [historyOverride, setHistoryOverride] = useState<GenerateResult | null>(null);
  const [historyItems, setHistoryItems] = useState<TaskListItemPayload[]>([]);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyLoadError, setHistoryLoadError] = useState<string | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const [historyClearing, setHistoryClearing] = useState(false);
  /** 后端仅返回已配置 API Key 的模型；全部未配置时列表为空 */
  const [modelListHint, setModelListHint] = useState<string | null>(null);

  const documentFiles = useMemo(
    () => normalizeFiles(documentFileList),
    [documentFileList]
  );
  const imageFiles = useMemo(() => normalizeFiles(imageFileList), [imageFileList]);
  const hasRequirementText = requirementText.trim().length > 0;
  const hasAttachments = documentFiles.length > 0 || imageFiles.length > 0;
  const canSubmit = hasRequirementText || hasAttachments;

  const displayResult = historyOverride ?? ctxResult;

  const handleDocumentChange: UploadProps["onChange"] = ({ fileList }) => {
    setDocumentFileList(fileList);
  };

  const handleImageChange: UploadProps["onChange"] = ({ fileList }) => {
    setImageFileList(fileList);
  };

  useEffect(() => {
    if (!historyDrawerOpen) return;

    const ac = new AbortController();
    setHistoryLoading(true);
    setHistoryLoadError(null);

    void listGenerationTasks({ page: 1, pageSize: 30 }, { signal: ac.signal })
      .then((r) => setHistoryItems(r.items))
      .catch((e: unknown) => {
        const aborted =
          (e instanceof DOMException && e.name === "AbortError") ||
          (e instanceof Error && e.name === "AbortError");
        if (aborted) return;
        const msg =
          e instanceof Error ? e.message : "无法加载生成历史，请确认后端服务可用后重试。";
        setHistoryLoadError(msg);
      })
      .finally(() => {
        if (!ac.signal.aborted) setHistoryLoading(false);
      });

    return () => ac.abort();
  }, [historyDrawerOpen, historyRefreshKey]);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const options = await listModels();
        setModelOptions(options);
        setSelectedModelKey((current) => current ?? options[0]?.key);
        setModelListHint(
          options.length === 0
            ? "未检测到可用模型：列表仅包含已在后端配置 API Key 的供应商。请在 backend 目录下的 .env 中至少设置 LLM_API_KEY、DEEPSEEK_API_KEY 或 MINIMAX_API_KEY（可参考项目根目录 .env.example），保存后重启后端，再刷新本页。"
            : null
        );
      } catch (error) {
        setModelListHint(null);
        messageApi.error(error instanceof Error ? error.message : "加载模型列表失败。");
      }
    };

    void loadModels();
  }, [messageApi]);

  useEffect(() => {
    if (pollError) setErrorMessage(pollError);
  }, [pollError]);

  useEffect(() => {
    if (taskStatus?.status === "failed") {
      setErrorMessage(taskStatus.errorMessage ?? "生成失败，请稍后重试。");
    }
    if (taskStatus?.status === "cancelled") {
      messageApi.info("任务已取消。");
    }
  }, [taskStatus, messageApi]);

  const selectedModel = modelOptions.find((m) => m.key === selectedModelKey);

  const runGenerateAsync = async (finalRequirementText: string) => {
    setErrorMessage("");
    setHistoryOverride(null);
    try {
      const { taskId: tid } = await submitGenerateAsync(
        finalRequirementText,
        documentFiles,
        imageFiles,
        selectedModelKey
      );
      startTask(tid);
      if (typeof Notification !== "undefined" && Notification.permission === "default") {
        void Notification.requestPermission();
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "生成失败，请稍后重试。");
    }
  };

  const handleConfirmSummary = async () => {
    const finalSummary = summaryDraft.trim();
    if (!finalSummary) {
      messageApi.warning("请先确认或补充需求摘要。");
      return;
    }
    setSummaryModalOpen(false);
    setRequirementText(finalSummary);
    await runGenerateAsync(finalSummary);
  };

  const handleGenerate = async () => {
    if (!canSubmit) {
      messageApi.warning("请填写需求摘要或上传参考文件。");
      return;
    }
    if (
      !hasRequirementText &&
      imageFiles.length > 0 &&
      !documentFiles.length &&
      !selectedModel?.supportsVision
    ) {
      messageApi.warning("当前模型不支持图片理解，请上传文档或切换支持视觉的模型。");
      return;
    }
    if (hasRequirementText) {
      await runGenerateAsync(requirementText.trim());
      return;
    }

    setSummaryLoading(true);
    setErrorMessage("");
    try {
      const summary = await summarizeRequirementFromFiles(
        requirementText,
        documentFiles,
        imageFiles,
        selectedModelKey
      );
      setSummaryPreview(summary);
      setSummaryDraft(summary.summaryText);
      setSummaryModalOpen(true);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "需求摘要提炼失败，请稍后重试。"
      );
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleCancelTask = async () => {
    setCancelling(true);
    try {
      await cancelActiveTask();
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "取消失败。");
    } finally {
      setCancelling(false);
    }
  };

  const handleLoadHistoryTask = async (id: string) => {
    try {
      const s = await getTaskStatus(id);
      if (s.result) {
        setHistoryOverride(s.result);
        setHistoryDrawerOpen(false);
        messageApi.success("已加载历史结果。");
      } else {
        messageApi.warning("该任务暂无可用结果。");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "加载该条生成历史失败。";
      messageApi.error({ content: <span style={{ whiteSpace: "pre-wrap" }}>{msg}</span>, duration: 6 });
    }
  };

  const handleClearAllHistory = async () => {
    setHistoryClearing(true);
    try {
      const result = await clearAllGenerationTasks();
      setHistoryItems([]);
      setHistoryOverride(null);
      // 通知 context 停止轮询并清除残留的活动任务 ID
      stopPolling();
      if (result.cancelledRunningCount > 0) {
        messageApi.success(`已清理 ${result.deletedCount} 条历史任务，其中 ${result.cancelledRunningCount} 条正在运行的任务已取消。`);
      } else {
        messageApi.success(`已清理 ${result.deletedCount} 条历史任务。`);
      }
      setHistoryRefreshKey((k) => k + 1);
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "清理历史失败。");
    } finally {
      setHistoryClearing(false);
    }
  };

  const loading = isRunning || summaryLoading;

  return (
    <>
      {contextHolder}
      <div className="workbench-intro">
        <div className="workbench-intro-main">
          <Typography.Text className="workbench-intro-eyebrow">AI Test Design Workbench</Typography.Text>
          <Typography.Title level={4} style={{ margin: 0 }}>
            从需求摘要、文档和图片中组织测试上下文，再输出结构化测试用例
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            左侧整理输入材料与测试关注点，右侧统一查看总览、模块分布、表格和 Markdown 文档结果。
          </Typography.Paragraph>
        </div>
        <div className="workbench-intro-side">
          {selectedModel && (
            <Tag icon={<ThunderboltOutlined />} color="blue">
              {selectedModel.label}
            </Tag>
          )}
          <Tag color="geekblue">多阶段生成</Tag>
          <Tag color="purple">Markdown / CSV / Excel 导出</Tag>
        </div>
      </div>

      {errorMessage && (
        <Alert
          type="error"
          showIcon
          closable
          message={errorMessage}
          onClose={() => setErrorMessage("")}
          style={{ marginBottom: 16 }}
        />
      )}

      {modelListHint && (
        <Alert
          type="warning"
          showIcon
          closable
          message={modelListHint}
          onClose={() => setModelListHint(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[24, 24]} className="generator-layout">
        <Col xs={24} lg={7} xl={6} className="generator-layout-column">
          <div className="workspace-column">
            <div className="workspace-column-header">
              <Typography.Title level={5} style={{ margin: 0 }}>
                输入工作区
              </Typography.Title>
              <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                录入测试重点并整理参考材料
              </Typography.Text>
            </div>

            <div className="input-workspace">
              <RequirementInput
                value={requirementText}
                loading={loading}
                selectedModelKey={selectedModelKey}
                modelOptions={modelOptions}
                documentCount={documentFileList.length}
                imageCount={imageFileList.length}
                canSubmit={canSubmit}
                documentFileList={documentFileList}
                imageFileList={imageFileList}
                onDocumentChange={handleDocumentChange}
                onImageChange={handleImageChange}
                onChange={setRequirementText}
                onModelChange={setSelectedModelKey}
                onSubmit={handleGenerate}
              />
            </div>
          </div>
        </Col>
        <Col xs={24} lg={17} xl={18} className="generator-layout-column">
          <div className="workspace-column">
            <div className="workspace-column-header workspace-column-header--with-actions">
              <div className="workspace-column-header-text">
                <Typography.Title level={5} style={{ margin: 0 }}>
                  结果工作区
                </Typography.Title>
                <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                  统一查看生成概览、模块拆分、表格和文档格式结果
                </Typography.Text>
              </div>
              <Button icon={<HistoryOutlined />} onClick={() => setHistoryDrawerOpen(true)}>
                生成历史
              </Button>
            </div>

            <ResultPreview
              result={displayResult}
              loading={loading && !displayResult}
              taskStatus={isRunning ? taskStatus : null}
              onCancelTask={taskId && taskStatus?.status === "running" ? handleCancelTask : undefined}
              cancellingTask={cancelling}
            />
          </div>
        </Col>
      </Row>

      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            <span>生成历史</span>
          </Space>
        }
        placement="right"
        width={420}
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
        destroyOnClose={false}
        extra={
          <Space>
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              loading={historyClearing}
              onClick={() => void handleClearAllHistory()}
            >
              清空全部
            </Button>
            <Button
              type="text"
              icon={<ReloadOutlined />}
              loading={historyLoading}
              onClick={() => setHistoryRefreshKey((k) => k + 1)}
            >
              刷新
            </Button>
          </Space>
        }
        styles={{ body: { paddingTop: 12 } }}
      >
        {historyLoadError ? (
          <Alert
            type="warning"
            showIcon
            message="无法加载生成历史列表"
            description={
              <div>
                <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{historyLoadError}</div>
                <Typography.Paragraph type="secondary" style={{ margin: "8px 0 0", fontSize: 12, marginBottom: 0 }}>
                  请打开开发者工具 → Network，查找路径包含{" "}
                  <Typography.Text code>/api/v1/generate/tasks</Typography.Text>{" "}
                  的请求；同时在 Console 中搜索{" "}
                  <Typography.Text code>hpr-api</Typography.Text>
                </Typography.Paragraph>
              </div>
            }
            action={
              <Button size="small" onClick={() => setHistoryRefreshKey((k) => k + 1)}>
                重试
              </Button>
            }
            style={{ marginBottom: 12 }}
          />
        ) : null}
        {historyLoading && historyItems.length === 0 && !historyLoadError ? (
          <div className="history-drawer-loading">
            <Spin />
          </div>
        ) : null}
        {!historyLoading && historyItems.length === 0 && !historyLoadError ? (
          <Typography.Text type="secondary">暂无生成记录</Typography.Text>
        ) : null}
        {historyItems.length > 0 ? (
          <div className="history-list">
            <Space direction="vertical" style={{ width: "100%" }} size="small">
              {historyItems.map((item) => (
                <div
                  key={item.taskId}
                  className="history-row"
                  role="button"
                  tabIndex={0}
                  onClick={() => void handleLoadHistoryTask(item.taskId)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      void handleLoadHistoryTask(item.taskId);
                    }
                  }}
                >
                  <Space wrap style={{ width: "100%", justifyContent: "space-between" }}>
                    <Typography.Text ellipsis style={{ maxWidth: 260, fontSize: 13 }}>
                      {item.requirementPreview}
                    </Typography.Text>
                    <Space size="small">
                      <Tag
                        color={
                          item.status === "succeeded"
                            ? "green"
                            : item.status === "running"
                              ? "processing"
                              : "default"
                        }
                      >
                        {item.status}
                      </Tag>
                      {item.caseCount != null && (
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {item.caseCount} 条
                        </Typography.Text>
                      )}
                    </Space>
                  </Space>
                  <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                    {new Date(item.createdAt).toLocaleString("zh-CN")}
                  </Typography.Text>
                </div>
              ))}
            </Space>
          </div>
        ) : null}
      </Drawer>

      <Modal
        className="summary-modal"
        open={summaryModalOpen}
        title={
          <Space>
            <FileSearchOutlined />
            <span>确认自动提炼的需求摘要</span>
          </Space>
        }
        onCancel={() => setSummaryModalOpen(false)}
        onOk={() => void handleConfirmSummary()}
        okText="确认并生成"
        cancelText="返回修改"
        width={760}
      >
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            系统已根据上传文件提炼出一份需求摘要。你可以直接确认，也可以补充测试重点后再生成。
          </Typography.Paragraph>
          {summaryPreview?.modules?.length ? (
            <div>
              <Typography.Text strong style={{ fontSize: 13 }}>
                识别模块
              </Typography.Text>
              <div className="tag-group" style={{ marginTop: 8 }}>
                {summaryPreview.modules.map((module) => (
                  <Tag key={module} color="geekblue">
                    {module}
                  </Tag>
                ))}
              </div>
            </div>
          ) : null}
          {summaryPreview?.openQuestions?.length ? (
            <Alert
              type="warning"
              showIcon
              message="检测到待确认问题"
              description={summaryPreview.openQuestions.join("；")}
            />
          ) : null}
          <TextArea
            rows={14}
            value={summaryDraft}
            onChange={(event) => setSummaryDraft(event.target.value)}
            placeholder="请确认或补充需求摘要。"
          />
        </Space>
      </Modal>
    </>
  );
}
