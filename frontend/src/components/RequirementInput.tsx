import type { KeyboardEvent, ReactElement } from "react";
import { Button, Card, Collapse, Input, Select, Space, Tooltip, Typography, Upload } from "antd";
import {
  SendOutlined,
  LoadingOutlined,
  RobotOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  MinusCircleFilled,
  InboxOutlined,
  PictureOutlined,
  PaperClipOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { UploadFile, UploadProps } from "antd/es/upload/interface";

import type { ModelOption } from "../services/api";

const { TextArea } = Input;
const { Dragger } = Upload;

const uploadPropsBase: Partial<UploadProps> = {
  beforeUpload: () => false,
  maxCount: 6,
};

/** 列表项 hover 展示完整文件名；配合 CSS 缩略显示 */
function uploadItemWithTitle(
  originNode: ReactElement,
  file: UploadFile
): ReactElement {
  return (
    <Tooltip title={file.name} placement="topLeft" mouseEnterDelay={0.35}>
      <span className="requirement-upload-item-tooltip-host">{originNode}</span>
    </Tooltip>
  );
}

interface RequirementInputProps {
  value: string;
  loading: boolean;
  selectedModelKey?: string;
  modelOptions: ModelOption[];
  documentCount: number;
  imageCount: number;
  canSubmit: boolean;
  documentFileList: UploadFile[];
  imageFileList: UploadFile[];
  onDocumentChange: UploadProps["onChange"];
  onImageChange: UploadProps["onChange"];
  onChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onSubmit: () => void;
}

export function RequirementInput({
  value,
  loading,
  selectedModelKey,
  modelOptions,
  documentCount,
  imageCount,
  canSubmit,
  documentFileList,
  imageFileList,
  onDocumentChange,
  onImageChange,
  onChange,
  onModelChange,
  onSubmit,
}: RequirementInputProps) {
  const navigate = useNavigate();
  const hasContent = value.trim().length > 0;
  const charCount = value.length;

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (!loading && canSubmit) {
        onSubmit();
      }
    }
  };

  return (
    <Card
      className="workspace-card requirement-card"
      title={
        <Space>
          <RobotOutlined />
          <span>需求摘要 / 测试关注点</span>
        </Space>
      }
      size="small"
    >
      <div className="card-section-stack">
        <div className="model-select-row">
          <Typography.Text type="secondary" style={{ fontSize: 13, flexShrink: 0 }}>
            模型
          </Typography.Text>
          <Select
            value={selectedModelKey}
            onChange={onModelChange}
            placeholder="选择模型"
            size="small"
            options={modelOptions.map((option) => ({
              value: option.key,
              label: option.label,
            }))}
            style={{ flex: 1 }}
          />
          <Tooltip title="管理模型配置">
            <Button
              type="text"
              size="small"
              icon={<SettingOutlined style={{ fontSize: 13 }} />}
              onClick={() => navigate("/settings")}
              style={{ color: "var(--text-muted)" }}
            />
          </Tooltip>
        </div>

        <TextArea
          rows={8}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            "可选填写本次测试重点，例如：\n\n" +
            "优先覆盖登录主流程、验证码时效、频控限制、异常提示和边界输入。\n" +
            "如果已上传需求文档，也可以留空，系统会先自动提炼摘要供你确认。"
          }
          style={{ fontSize: 14, lineHeight: 1.6 }}
        />

        <div className="char-count">{charCount > 0 ? `${charCount} 字` : ""}</div>

        <Collapse
          bordered={false}
          className="requirement-refs-collapse"
          defaultActiveKey={["refs"]}
          style={{ background: "transparent" }}
          items={[
            {
              key: "refs",
              label: (
                <Space>
                  <PaperClipOutlined />
                  <span>参考资料（可选）</span>
                </Space>
              ),
              children: (
                <div className="requirement-uploads-row">
                  <div className="requirement-upload-col requirement-upload-col--doc">
                    <div className="attachment-section-label">
                      <span>文档</span>
                      <span className="attachment-formats">.txt .md .pdf .docx</span>
                    </div>
                    <Dragger
                      {...uploadPropsBase}
                      className="requirement-upload-dragger"
                      fileList={documentFileList}
                      onChange={onDocumentChange}
                      accept=".txt,.md,.pdf,.docx"
                      multiple
                      itemRender={(node, file) => uploadItemWithTitle(node, file)}
                    >
                      <p className="ant-upload-drag-icon">
                        <InboxOutlined />
                      </p>
                      <p className="ant-upload-text">点击或拖拽文档到此处上传</p>
                      <p className="ant-upload-hint">单文件不超过平台限制，最多 6 个文件</p>
                    </Dragger>
                  </div>
                  <div className="requirement-upload-col requirement-upload-col--img">
                    <div className="attachment-section-label">
                      <span>图片</span>
                      <span className="attachment-formats">PNG / JPG / GIF / WEBP</span>
                    </div>
                    <Upload
                      {...uploadPropsBase}
                      fileList={imageFileList}
                      onChange={onImageChange}
                      accept="image/*"
                      listType="picture-card"
                      multiple
                      itemRender={(node, file) => uploadItemWithTitle(node, file)}
                    >
                      {imageFileList.length < 6 && (
                        <div>
                          <PictureOutlined />
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

        <div className="readiness-card">
          <div className="readiness-list">
            <ReadinessItem
              ready={hasContent}
              optional={documentCount > 0 || imageCount > 0}
              label={hasContent ? "已输入需求摘要 / 测试关注点" : "可直接填写测试重点（推荐）"}
            />
            <ReadinessItem
              ready={documentCount > 0}
              optional
              label={
                documentCount > 0
                  ? `已上传 ${documentCount} 份文档`
                  : "可上传参考文档（可选）"
              }
            />
            <ReadinessItem
              ready={imageCount > 0}
              optional
              label={
                imageCount > 0
                  ? `已上传 ${imageCount} 张图片`
                  : "可上传参考图片（可选）"
              }
            />
          </div>
        </div>

        <div className="generate-cta">
          <Button
            type="primary"
            size="large"
            loading={loading}
            disabled={!canSubmit}
            onClick={onSubmit}
            icon={loading ? <LoadingOutlined /> : <SendOutlined />}
            block
          >
            {loading ? "处理中..." : "生成测试用例"}
          </Button>
          <Typography.Paragraph type="secondary" className="generate-cta-hint">
            提示：在需求输入框内可使用 Ctrl+Enter / Cmd+Enter 快捷提交
          </Typography.Paragraph>
        </div>
      </div>
    </Card>
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
    <CheckCircleFilled style={{ color: "var(--color-success)", fontSize: 12 }} />
  ) : optional ? (
    <MinusCircleFilled style={{ color: "var(--text-muted)", fontSize: 12 }} />
  ) : (
    <CloseCircleFilled style={{ color: "var(--text-muted)", fontSize: 12 }} />
  );

  return (
    <div className="readiness-item">
      {icon}
      <span style={{ color: ready ? "var(--text-primary)" : undefined }}>{label}</span>
    </div>
  );
}
