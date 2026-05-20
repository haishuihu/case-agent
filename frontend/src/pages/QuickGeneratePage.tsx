import { useState, useEffect } from "react";
import {
  Alert,
  Button,
  Card,
  Collapse,
  Drawer,
  Input,
  message,
  Select,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from "antd";
import {
  CopyOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
  InboxOutlined,
  PictureOutlined,
  PaperClipOutlined,
  SendOutlined,
  LoadingOutlined,
  CheckCircleFilled,
  MinusCircleFilled,
  CloseCircleFilled,
  DeleteOutlined,
} from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { UploadFile, UploadProps } from "antd/es/upload/interface";

import {
  quickGenerate,
  listQuickGenerateHistory,
  clearQuickGenerateHistory,
  type QuickGenerateResult,
  type QuickHistoryItem,
} from "../services/api";
import { useModelConfig } from "../context/ModelConfigContext";

const { TextArea } = Input;
const { Dragger } = Upload;

const uploadBase: Partial<UploadProps> = {
  beforeUpload: () => false,
  maxCount: 6,
};

function uploadItemWithTitle(
  originNode: React.ReactElement,
  file: UploadFile
): React.ReactElement {
  return (
    <Tooltip title={file.name} placement="topLeft" mouseEnterDelay={0.35}>
      <span className="requirement-upload-item-tooltip-host">
        {originNode}
      </span>
    </Tooltip>
  );
}

function ReadinessItem({
  ready,
  optional,
  label,
}: {
  ready: boolean;
  optional?: boolean;
  label: string;
}) {
  const icon = ready ? (
    <CheckCircleFilled
      style={{ color: "var(--color-success)", fontSize: 12 }}
    />
  ) : optional ? (
    <MinusCircleFilled
      style={{ color: "var(--text-muted)", fontSize: 12 }}
    />
  ) : (
    <CloseCircleFilled
      style={{ color: "var(--text-muted)", fontSize: 12 }}
    />
  );

  return (
    <div className="readiness-item">
      {icon}
      <span
        style={{
          color: ready ? "var(--text-primary)" : undefined,
        }}
      >
        {label}
      </span>
    </div>
  );
}

export function QuickGeneratePage() {
  const [messageApi, contextHolder] = message.useMessage();
  const { modelOptions, selectedModelKey, setSelectedModelKey } = useModelConfig();
  const [requirementText, setRequirementText] = useState("");
  const [documentFileList, setDocumentFileList] = useState<UploadFile[]>([]);
  const [imageFileList, setImageFileList] = useState<UploadFile[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<QuickGenerateResult | null>(null);

  // History state
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<QuickHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyOverride, setHistoryOverride] = useState<QuickHistoryItem | null>(null);

  // Load history when drawer opens
  useEffect(() => {
    if (!historyDrawerOpen) return;
    const ac = new AbortController();
    setHistoryLoading(true);
    listQuickGenerateHistory({ page: 1, pageSize: 30 })
      .then((r) => {
        if (!ac.signal.aborted) setHistoryItems(r.items);
      })
      .catch(() => {})
      .finally(() => {
        if (!ac.signal.aborted) setHistoryLoading(false);
      });
    return () => ac.abort();
  }, [historyDrawerOpen]);

  const documentFiles = documentFileList.flatMap((f) =>
    f.originFileObj ? [f.originFileObj as File] : []
  );
  const imageFiles = imageFileList.flatMap((f) =>
    f.originFileObj ? [f.originFileObj as File] : []
  );
  const hasInput =
    requirementText.trim().length > 0 ||
    documentFiles.length > 0 ||
    imageFiles.length > 0;

  const handleGenerate = async () => {
    if (!requirementText.trim()) {
      messageApi.warning("请填写需求描述");
      return;
    }
    setGenerating(true);
    setError("");
    setResult(null);
    setHistoryOverride(null);
    try {
      const res = await quickGenerate(
        requirementText.trim(),
        documentFiles,
        imageFiles,
        selectedModelKey
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败，请稍后重试。");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async () => {
    const content = historyOverride?.outputContent ?? result?.content;
    if (!content) return;
    await navigator.clipboard.writeText(content);
    messageApi.success("已复制到剪贴板");
  };

  const handleLoadHistory = (item: QuickHistoryItem) => {
    setHistoryOverride(item);
    setHistoryDrawerOpen(false);
    setRequirementText(item.requirementPreview.replace(/\.\.\.$/, ""));
    messageApi.success("已加载历史结果。");
  };

  const handleClearHistory = async () => {
    try {
      await clearQuickGenerateHistory();
      setHistoryItems([]);
      setHistoryOverride(null);
      messageApi.success("历史已清空。");
    } catch {
      messageApi.error("清空历史失败。");
    }
  };

  // Merged display result: history override takes precedence
  const displayContent = historyOverride?.outputContent ?? result?.content;
  const displayModelName = historyOverride?.modelName ?? result?.modelName;
  const displayGeneratedAt = historyOverride?.createdAt ?? result?.generatedAt;
  const showResult = (displayContent && !generating) || (historyOverride && !generating);

  const charCount = requirementText.length;

  return (
    <>
      {contextHolder}
      <div className="workbench-intro">
        <div className="workbench-intro-main">
          <Typography.Text className="workbench-intro-eyebrow">
            极简模式
          </Typography.Text>
          <Typography.Title level={4} style={{ margin: 0 }}>
            快速生成测试要点 — 临时需求救火专用
          </Typography.Title>
          <Typography.Paragraph
            type="secondary"
            style={{ marginBottom: 0 }}
          >
            单次 LLM 调用，30 秒内输出精简的测试要点（核心流程 /
            边界条件 / 异常场景 / 关键检查）。
            无需等待完整用例格式，直接用于自测或评审。
          </Typography.Paragraph>
        </div>
        <div className="workbench-intro-side">
          <Tag icon={<ClockCircleOutlined />} color="blue">
            快速响应
          </Tag>
          <Tag icon={<CheckCircleOutlined />} color="green">
            Bullet Point 格式
          </Tag>
          <Tag icon={<ThunderboltOutlined />} color="purple">
            单次调用
          </Tag>
          <Button
            icon={<HistoryOutlined />}
            size="small"
            onClick={() => setHistoryDrawerOpen(true)}
          >
            历史
          </Button>
        </div>
      </div>

      {error && (
        <Alert
          type="error"
          showIcon
          closable
          message={error}
          onClose={() => setError("")}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 输入卡片 */}
      <Card className="requirement-card quick-generate-card" size="small">
        <div className="card-section-stack">
          {/* 模型选择行 */}
          <div className="model-select-row">
            <Select
              placeholder="选择模型"
              value={selectedModelKey}
              onChange={setSelectedModelKey}
              size="small"
              options={modelOptions.map((m) => ({
                value: m.key,
                label: m.label,
              }))}
              style={{ flex: 1 }}
            />
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              loading={generating}
              disabled={!hasInput}
              onClick={() => void handleGenerate()}
            >
              {generating ? "生成中..." : "一键生成"}
            </Button>
          </div>

          {/* 需求输入 */}
          <TextArea
            rows={8}
            value={requirementText}
            onChange={(e) => setRequirementText(e.target.value)}
            placeholder={
              "输入需求描述，例如：\n" +
              "用户登录功能：支持手机号+验证码登录，验证码有效期5分钟，" +
              "错误3次后锁定账号，忘记密码可通过邮箱找回"
            }
            maxLength={5000}
            showCount={false}
            style={{ fontSize: 14, lineHeight: 1.7 }}
          />

          <div className="char-count">
            {charCount > 0 ? `${charCount} 字` : ""}
          </div>

          {/* 参考资料折叠区 */}
          <Collapse
            bordered={false}
            className="requirement-refs-collapse"
            defaultActiveKey={[]}
            style={{ background: "transparent" }}
            items={[
              {
                key: "refs",
                label: (
                  <Space>
                    <PaperClipOutlined />
                    <span>参考资料（可选）</span>
                    {documentFiles.length > 0 && (
                      <Tag color="blue" style={{ marginLeft: 4 }}>
                        {documentFiles.length} 文档
                      </Tag>
                    )}
                    {imageFiles.length > 0 && (
                      <Tag color="purple" style={{ marginLeft: 2 }}>
                        {imageFiles.length} 图片
                      </Tag>
                    )}
                  </Space>
                ),
                children: (
                  <div className="requirement-uploads-row">
                    {/* 文档上传 */}
                    <div className="requirement-upload-col requirement-upload-col--doc">
                      <div className="attachment-section-label">
                        <span>文档</span>
                        <span className="attachment-formats">
                          .txt .md .pdf .docx
                        </span>
                      </div>
                      <Dragger
                        {...uploadBase}
                        className="requirement-upload-dragger"
                        fileList={documentFileList}
                        onChange={(info) =>
                          setDocumentFileList(info.fileList)
                        }
                        accept=".txt,.md,.pdf,.docx"
                        multiple
                        itemRender={(node, file) =>
                          uploadItemWithTitle(node, file)
                        }
                      >
                        <p className="ant-upload-drag-icon">
                          <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">
                          点击或拖拽文档到此处上传
                        </p>
                        <p className="ant-upload-hint">
                          单文件不超过平台限制，最多 6 个文件
                        </p>
                      </Dragger>
                    </div>

                    {/* 图片上传 */}
                    <div className="requirement-upload-col requirement-upload-col--img">
                      <div className="attachment-section-label">
                        <span>图片</span>
                        <span className="attachment-formats">
                          PNG / JPG / GIF / WEBP
                        </span>
                      </div>
                      <Upload
                        {...uploadBase}
                        fileList={imageFileList}
                        onChange={(info) => setImageFileList(info.fileList)}
                        accept="image/*"
                        listType="picture-card"
                        multiple
                        itemRender={(node, file) =>
                          uploadItemWithTitle(node, file)
                        }
                      >
                        {imageFileList.length < 6 && (
                          <div>
                            <PictureOutlined style={{ fontSize: 20 }} />
                            <div style={{ marginTop: 8 }}>上传</div>
                          </div>
                        )}
                      </Upload>
                    </div>
                  </div>
                ),
              },
            ]}
          />

          {/* 就绪状态 */}
          <div className="readiness-card">
            <div className="readiness-list">
              <ReadinessItem
                ready={requirementText.trim().length > 0}
                optional={
                  documentFileList.length > 0 || imageFileList.length > 0
                }
                label={
                  requirementText.trim().length > 0
                    ? "已输入需求描述"
                    : "可直接填写需求描述（推荐）"
                }
              />
              <ReadinessItem
                ready={documentFileList.length > 0}
                optional
                label={
                  documentFileList.length > 0
                    ? `已上传 ${documentFileList.length} 份文档`
                    : "可上传参考文档（可选）"
                }
              />
              <ReadinessItem
                ready={imageFileList.length > 0}
                optional
                label={
                  imageFileList.length > 0
                    ? `已上传 ${imageFileList.length} 张图片`
                    : "可上传参考图片（可选）"
                }
              />
            </div>
          </div>

          {/* 生成按钮 */}
          <div className="generate-cta">
            <Button
              type="primary"
              size="large"
              icon={generating ? <LoadingOutlined /> : <SendOutlined />}
              loading={generating}
              disabled={!hasInput}
              onClick={() => void handleGenerate()}
              block
            >
              {generating ? "生成中，请稍候..." : "一键生成测试要点"}
            </Button>
            <Typography.Paragraph
              type="secondary"
              className="generate-cta-hint"
            >
              提示：按 Ctrl+Enter / Cmd+Enter 快捷提交
            </Typography.Paragraph>
          </div>
        </div>
      </Card>

      {/* 加载状态 */}
      {generating && (
        <Card className="quick-result-card workspace-card">
          <Space
            style={{ width: "100%", justifyContent: "center" }}
            direction="vertical"
            align="center"
          >
            <Spin size="large" />
            <Typography.Text type="secondary">
              AI 正在生成测试要点，请稍候...
            </Typography.Text>
          </Space>
        </Card>
      )}

      {/* 结果展示（来自生成或历史加载） */}
      {showResult && (
        <Card
          className="quick-result-card workspace-card"
          title={
            <Space>
              <ThunderboltOutlined />
              <span>测试要点结果</span>
              {historyOverride && <Tag color="orange">历史</Tag>}
              <Tag color="green">{displayModelName}</Tag>
              <Typography.Text
                type="secondary"
                style={{ fontWeight: "normal", fontSize: 13 }}
              >
                {displayGeneratedAt
                  ? new Date(displayGeneratedAt).toLocaleString("zh-CN")
                  : ""}
              </Typography.Text>
            </Space>
          }
          extra={
            <Space>
              <Button
                icon={<CopyOutlined />}
                size="small"
                onClick={() => void handleCopy()}
              >
                复制
              </Button>
              <Button
                size="small"
                onClick={() => {
                  setResult(null);
                  setHistoryOverride(null);
                  setRequirementText("");
                  setDocumentFileList([]);
                  setImageFileList([]);
                }}
              >
                重新生成
              </Button>
            </Space>
          }
        >
          <div className="markdown-document">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {displayContent}
            </ReactMarkdown>
          </div>
        </Card>
      )}

      {/* 历史记录抽屉 */}
      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            <span>快速生成历史</span>
          </Space>
        }
        placement="right"
        width={420}
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
        className="quick-history-drawer"
        extra={
          historyItems.length > 0 ? (
            <Button
              icon={<DeleteOutlined />}
              size="small"
              danger
              onClick={() => void handleClearHistory()}
            >
              清空
            </Button>
          ) : undefined
        }
      >
        {historyLoading ? (
          <Space
            style={{ width: "100%", justifyContent: "center", padding: 48 }}
            direction="vertical"
            align="center"
          >
            <Spin size="small" />
          </Space>
        ) : historyItems.length === 0 ? (
          <div className="quick-history-empty">
            <Typography.Paragraph type="secondary">
              暂无历史记录
            </Typography.Paragraph>
          </div>
        ) : (
          historyItems.map((item) => (
            <div
              key={item.id}
              className="quick-history-row"
              onClick={() => handleLoadHistory(item)}
            >
              <Typography.Text
                className="quick-history-preview"
                ellipsis={{ tooltip: item.requirementPreview }}
              >
                {item.requirementPreview}
              </Typography.Text>
              <div className="quick-history-meta">
                <Tag color="green" style={{ marginRight: 0 }}>
                  {item.modelName}
                </Tag>
                <Typography.Text
                  type="secondary"
                  style={{ fontSize: 12 }}
                >
                  {new Date(item.createdAt).toLocaleString("zh-CN")}
                </Typography.Text>
              </div>
            </div>
          ))
        )}
      </Drawer>
    </>
  );
}
