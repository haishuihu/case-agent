import { useEffect, useState } from "react";
import {
  Button,
  Collapse,
  Drawer,
  Input,
  message,
  Segmented,
  Select,
  Skeleton,
  Space,
  Tag,
  Typography,
  Upload,
  UploadFile,
} from "antd";
import {
  TranslationOutlined,
  FileTextOutlined,
  PictureOutlined,
  SaveOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import type { UploadProps } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { listModels, type ModelOption } from "../services/api";
import {
  createTranslation,
  listTranslations,
  getTranslation,
  updateTranslation,
  deleteTranslation,
  type TranslationListItem,
  type TranslationResponse,
} from "../services/translation";

const { Text } = Typography;
const { TextArea } = Input;

type ViewMode = "preview" | "edit";

const uploadPropsBase: Partial<UploadProps> = {
  beforeUpload: () => false,
  maxCount: 6,
};

export function TranslationPage() {
  // ---- Input state ----
  const [requirementText, setRequirementText] = useState("");
  const [documentFiles, setDocumentFiles] = useState<UploadFile[]>([]);
  const [imageFiles, setImageFiles] = useState<UploadFile[]>([]);
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [selectedModelKey, setSelectedModelKey] = useState<string | undefined>();
  const [translating, setTranslating] = useState(false);

  // ---- Result state ----
  const [currentTranslation, setCurrentTranslation] = useState<TranslationResponse | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("preview");
  const [saving, setSaving] = useState(false);

  // ---- History state ----
  const [historyItems, setHistoryItems] = useState<TranslationListItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);

  // ---- Load models ----
  useEffect(() => {
    listModels().then((models) => {
      setModelOptions(models);
      if (models.length > 0 && !selectedModelKey) {
        setSelectedModelKey(models[0].key);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- Load history ----
  const loadHistory = () => {
    setHistoryLoading(true);
    listTranslations({ page: 1, pageSize: 20 })
      .then((data) => setHistoryItems(data.items))
      .catch(() => message.error("加载历史记录失败"))
      .finally(() => setHistoryLoading(false));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // ---- Translate ----
  const handleTranslate = async () => {
    const hasFiles = documentFiles.length > 0;
    if (!requirementText.trim() && !hasFiles) {
      message.warning("请至少填写需求描述或上传参考文档。");
      return;
    }
    setTranslating(true);
    try {
      const docFiles = documentFiles
        .filter((f) => f.originFileObj)
        .map((f) => f.originFileObj as File);
      const imgFiles = imageFiles
        .filter((f) => f.originFileObj)
        .map((f) => f.originFileObj as File);

      const result = await createTranslation({
        requirementText: requirementText.trim(),
        modelKey: selectedModelKey,
        documentFiles: docFiles.length > 0 ? docFiles : undefined,
        imageFiles: imgFiles.length > 0 ? imgFiles : undefined,
      });

      setCurrentTranslation(result);
      setEditedContent(result.translatedContent);
      setViewMode("preview");
      message.success("翻译完成，请审查并补充待确认问题。");
      loadHistory();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "翻译失败，请稍后重试。");
    } finally {
      setTranslating(false);
    }
  };

  // ---- Save review ----
  const handleSaveReview = async () => {
    if (!currentTranslation) return;
    setSaving(true);
    try {
      const updated = await updateTranslation(currentTranslation.id, {
        reviewedContent: editedContent,
        status: "reviewed",
      });
      setCurrentTranslation(updated);
      message.success("审查结果已保存。");
      loadHistory();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  };

  // ---- Load from history ----
  const handleLoadHistory = async (id: string) => {
    try {
      const record = await getTranslation(id);
      setCurrentTranslation(record);
      setEditedContent(record.reviewedContent || record.translatedContent);
      setRequirementText(record.originalRequirementText);
      setViewMode("preview");
    } catch {
      message.error("加载翻译记录失败。");
    }
  };

  // ---- Delete history ----
  const handleDeleteHistory = async (id: string) => {
    try {
      await deleteTranslation(id);
      if (currentTranslation?.id === id) {
        setCurrentTranslation(null);
      }
      message.success("已删除。");
      loadHistory();
    } catch {
      message.error("删除失败。");
    }
  };

  // ---- Upload handlers ----
  const handleDocumentChange: UploadProps["onChange"] = ({ fileList }) => {
    setDocumentFiles(fileList);
  };

  const handleImageChange: UploadProps["onChange"] = ({ fileList }) => {
    setImageFiles(fileList);
  };

  // ---- Copy output ----
  const handleCopyOutput = () => {
    if (displayContent) {
      navigator.clipboard.writeText(displayContent).then(() => message.success("已复制"));
    }
  };

  const hasFiles = documentFiles.length > 0;
  const canTranslate = (requirementText.trim().length > 0 || hasFiles) && !translating;
  const displayContent = viewMode === "edit" ? editedContent : (currentTranslation?.reviewedContent || currentTranslation?.translatedContent || "");
  const isReviewed = currentTranslation?.status === "reviewed";

  return (
    <div className="translation-page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <h1 className="page-title" style={{ margin: 0 }}>需求翻译</h1>
        <Button
          icon={<HistoryOutlined />}
          onClick={() => {
            loadHistory();
            setHistoryDrawerOpen(true);
          }}
        >
          历史记录
        </Button>
      </div>

      {/* Input Area */}
      <div className="translation-input-area">
        <label className="translation-input-label">翻译模型</label>
        <Select
          value={selectedModelKey}
          onChange={setSelectedModelKey}
          options={modelOptions.map((m) => ({
            value: m.key,
            label: m.label,
          }))}
          style={{ width: "100%" }}
          size="small"
        />

        <label className="translation-input-label">
          需求描述
          {!hasFiles && (
            <span style={{ color: "var(--color-danger)", fontSize: 12 }}> *</span>
          )}
          {hasFiles && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              （已上传文档时可留空）
            </Text>
          )}
        </label>
        <TextArea
          value={requirementText}
          onChange={(e) => setRequirementText(e.target.value)}
          rows={10}
          maxLength={10000}
          showCount
          placeholder={hasFiles ? "可选：补充说明或测试关注点…" : "粘贴产品需求文档的文字内容…"}
        />

        <Collapse
          ghost
          items={[
            {
              key: "uploads",
              label: (
                <Space>
                  <FileTextOutlined />
                  <span>上传参考资料（可选）</span>
                </Space>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>
                      参考文档（.txt .md .pdf .docx）
                    </Text>
                    <Upload.Dragger
                      {...uploadPropsBase}
                      accept=".txt,.md,.pdf,.docx"
                      fileList={documentFiles}
                      onChange={handleDocumentChange}
                    >
                      <p className="ant-upload-drag-icon">
                        <FileTextOutlined />
                      </p>
                      <p className="ant-upload-text">点击或拖拽文档到此处上传</p>
                    </Upload.Dragger>
                  </div>
                  <div>
                    <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>
                      参考截图（支持图片格式）
                    </Text>
                    <Upload
                      {...uploadPropsBase}
                      accept="image/*"
                      listType="picture-card"
                      fileList={imageFiles}
                      onChange={handleImageChange}
                    >
                      <PictureOutlined />
                      <span style={{ marginLeft: 8 }}>上传</span>
                    </Upload>
                  </div>
                </div>
              ),
            },
          ]}
        />

        <Button
          type="primary"
          icon={translating ? <LoadingOutlined /> : <TranslationOutlined />}
          onClick={handleTranslate}
          loading={translating}
          disabled={!canTranslate}
          block
          size="large"
        >
          {translating ? "正在翻译…" : "开始翻译"}
        </Button>
      </div>

      {/* Output Area */}
      {!currentTranslation && !translating ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <TranslationOutlined />
          </div>
          <p className="empty-state-text">
            输入需求并点击「开始翻译」后，结构化需求文档将展示在这里
          </p>
        </div>
      ) : translating ? (
        <div>
          <Skeleton active paragraph={{ rows: 12 }} />
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <LoadingOutlined style={{ fontSize: 24, color: "var(--text-secondary)" }} />
            <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
              AI 正在分析需求并生成结构化文档…
            </Text>
          </div>
        </div>
      ) : currentTranslation ? (
        <div className="translation-output-area" style={{ background: "#ffffff", border: "1px solid var(--border-light)", borderRadius: 6, padding: 20 }}>
          <div className="translation-output-header" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="translation-output-title">翻译结果</span>
              <Tag
                icon={isReviewed ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                color={isReviewed ? "success" : "warning"}
                style={{ margin: 0 }}
              >
                {isReviewed ? "已审查" : "待审查"}
              </Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                模型：{currentTranslation.modelName}
              </Text>
            </div>
            <Space>
              <Button
                type="text"
                icon={<CopyOutlined />}
                onClick={handleCopyOutput}
                size="small"
              >
                复制
              </Button>
              <Segmented
                value={viewMode}
                onChange={(val) => setViewMode(val as ViewMode)}
                options={[
                  { label: "预览", value: "preview", icon: <EyeOutlined /> },
                  { label: "编辑", value: "edit", icon: <EditOutlined /> },
                ]}
                size="small"
              />
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveReview}
                loading={saving}
                size="small"
              >
                保存审查结果
              </Button>
            </Space>
          </div>

          {viewMode === "preview" ? (
            <div className="translation-markdown-preview">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {displayContent}
              </ReactMarkdown>
            </div>
          ) : (
            <TextArea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={24}
              style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
            />
          )}

          {isReviewed && currentTranslation.reviewedContent && (
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                最后更新：
                {currentTranslation.updatedAt
                  ? new Date(currentTranslation.updatedAt).toLocaleString("zh-CN")
                  : new Date(currentTranslation.createdAt).toLocaleString("zh-CN")}
              </Text>
            </div>
          )}
        </div>
      ) : null}

      {/* History Drawer */}
      <Drawer
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <HistoryOutlined />
            <span>翻译历史</span>
            {historyItems.length > 0 && (
              <Tag style={{ margin: 0 }}>{historyItems.length}</Tag>
            )}
          </div>
        }
        placement="right"
        width={420}
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
        styles={{ body: { padding: 0 } }}
      >
        <div className="history-drawer-body">
          {historyLoading ? (
            <div style={{ padding: 24 }}>
              <Skeleton active paragraph={{ rows: 6 }} />
            </div>
          ) : historyItems.length === 0 ? (
            <div className="empty-state" style={{ padding: 48 }}>
              <div className="empty-state-icon">
                <HistoryOutlined />
              </div>
              <p className="empty-state-text">暂无翻译记录</p>
            </div>
          ) : (
            <div className="history-drawer-list">
              {historyItems.map((item) => (
                <div
                  key={item.id}
                  className="history-drawer-item"
                  onClick={() => {
                    handleLoadHistory(item.id);
                    setHistoryDrawerOpen(false);
                  }}
                >
                  <div className="history-drawer-item-main">
                    <div className="history-drawer-item-preview">
                      {item.requirementPreview || "未命名翻译"}
                    </div>
                    <div className="history-drawer-item-meta">
                      <Tag
                        color={item.status === "reviewed" ? "success" : "warning"}
                      >
                        {item.status === "reviewed" ? "已审查" : "待审查"}
                      </Tag>
                      <span className="history-drawer-item-date">
                        {new Date(item.createdAt).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                  </div>
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteHistory(item.id);
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </Drawer>
    </div>
  );
}
