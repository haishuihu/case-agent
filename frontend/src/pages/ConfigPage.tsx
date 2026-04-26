import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  ApiOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  PlusOutlined,
  SettingOutlined,
  StarFilled,
  SwapOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import {
  PROVIDER_PRESETS,
  createEmbeddingConfig,
  createLLMConfig,
  deleteEmbeddingConfig,
  deleteLLMConfig,
  findPreset,
  listEmbeddingConfigs,
  listLLMConfigs,
  setDefaultLLMConfig,
  testLLMConnection,
  type EmbeddingConfig,
  type EmbeddingConfigCreate,
  type EmbeddingConfigUpdate,
  type LLMConfig,
  type LLMConfigCreate,
  type LLMConfigUpdate,
} from "../services/config";

const { TextArea } = Input;

function normalizeConfigs(configs: LLMConfig[]): LLMConfig[] {
  return configs.map((c) => ({
    ...c,
    apiFormat: c.apiFormat as LLMConfig["apiFormat"],
  }));
}

export function ConfigPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([]);
  const [embConfigs, setEmbConfigs] = useState<EmbeddingConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [llmModalOpen, setLlmModalOpen] = useState(false);
  const [embModalOpen, setEmbModalOpen] = useState(false);
  const [editingLlm, setEditingLlm] = useState<LLMConfig | null>(null);
  const [editingEmb, setEditingEmb] = useState<EmbeddingConfig | null>(null);
  const [llmForm] = Form.useForm<LLMConfigCreate & { confirmApiKey: string }>();
  const [embForm] = Form.useForm<EmbeddingConfigCreate & { confirmApiKey: string }>();
  const [saving, setSaving] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [connResult, setConnResult] = useState<{ ok: boolean; message: string } | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [llm, emb] = await Promise.all([listLLMConfigs(), listEmbeddingConfigs()]);
      setLlmConfigs(llm);
      setEmbConfigs(emb);
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "加载配置失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, []);

  // ---- LLM Config Handlers ----

  const openAddLlm = () => {
    setEditingLlm(null);
    llmForm.resetFields();
    llmForm.setFieldsValue({
      provider: "DeepSeek",
      apiFormat: "openai_compatible",
      baseUrl: "https://api.deepseek.com/v1",
      maxOutputTokens: 64000,
      timeoutSeconds: 120,
      supportsVision: false,
      supportsStructuredOutput: true,
      isDefault: llmConfigs.length === 0,
      isActive: true,
    });
    setConnResult(null);
    setLlmModalOpen(true);
  };

  const openEditLlm = (cfg: LLMConfig) => {
    setEditingLlm(cfg);
    llmForm.setFieldsValue({
      name: cfg.name,
      provider: cfg.provider,
      apiFormat: cfg.apiFormat,
      baseUrl: cfg.baseUrl,
      apiKey: "",
      confirmApiKey: "",
      modelName: cfg.modelName,
      maxOutputTokens: cfg.maxOutputTokens,
      timeoutSeconds: cfg.timeoutSeconds,
      supportsVision: cfg.supportsVision,
      supportsStructuredOutput: cfg.supportsStructuredOutput,
      isDefault: cfg.isDefault,
      isActive: cfg.isActive,
    });
    setConnResult(null);
    setLlmModalOpen(true);
  };

  const handleLlmSave = async () => {
    try {
      const vals = await llmForm.validateFields();
      setSaving(true);
      if (!vals.apiKey && !editingLlm) {
        messageApi.error("API Key 为必填项");
        setSaving(false);
        return;
      }
      const basePayload = {
        name: vals.name,
        provider: vals.provider,
        apiFormat: vals.apiFormat,
        baseUrl: vals.baseUrl,
        apiKey: vals.apiKey,
        modelName: vals.modelName,
        maxOutputTokens: vals.maxOutputTokens,
        timeoutSeconds: vals.timeoutSeconds,
        supportsVision: vals.supportsVision,
        supportsStructuredOutput: vals.supportsStructuredOutput,
        isActive: vals.isActive,
        isDefault: vals.isDefault,
      };
      if (editingLlm) {
        const updatePayload: LLMConfigUpdate = { ...basePayload };
        if (!vals.apiKey) {
          delete updatePayload.apiKey;
        }
        await updateLLMConfig(editingLlm.id, updatePayload);
        messageApi.success("配置已更新");
      } else {
        await createLLMConfig(basePayload as LLMConfigCreate);
        messageApi.success("配置已添加");
      }
      setLlmModalOpen(false);
      await loadAll();
    } catch (e) {
      if (e instanceof Error) messageApi.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLlm = async (id: string) => {
    try {
      await deleteLLMConfig(id);
      messageApi.success("配置已删除");
      await loadAll();
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await setDefaultLLMConfig(id);
      messageApi.success("已设为默认");
      await loadAll();
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "设置失败");
    }
  };

  const handleTestConnection = async () => {
    try {
      const vals = await llmForm.validateFields(["provider", "apiFormat", "baseUrl", "apiKey", "modelName"]);
      if (!vals.apiKey) {
        messageApi.warning("请先填写 API Key");
        return;
      }
      setTestingConn(true);
      setConnResult(null);
      const result = await testLLMConnection({
        provider: vals.provider,
        apiFormat: vals.apiFormat,
        baseUrl: vals.baseUrl,
        apiKey: vals.apiKey,
        modelName: vals.modelName,
        timeoutSeconds: 30,
      });
      setConnResult(result);
    } catch (e) {
      if (e instanceof Error) messageApi.error(e.message);
    } finally {
      setTestingConn(false);
    }
  };

  const handleProviderChange = (provider: string) => {
    const preset = findPreset(provider);
    if (preset) {
      llmForm.setFieldsValue({
        apiFormat: preset.apiFormat,
        baseUrl: preset.baseUrl,
        supportsVision: preset.supportsVision,
        supportsStructuredOutput: preset.supportsStructuredOutput,
      });
    }
  };

  // ---- Embedding Config Handlers ----

  const openAddEmb = () => {
    setEditingEmb(null);
    embForm.resetFields();
    embForm.setFieldsValue({
      provider: "OpenAI",
      apiFormat: "openai_compatible",
      baseUrl: "",
      maxOutputTokens: undefined,
      timeoutSeconds: 60,
      dimensions: 0,
      isActive: true,
    });
    setEmbModalOpen(true);
  };

  const openEditEmb = (cfg: EmbeddingConfig) => {
    setEditingEmb(cfg);
    embForm.setFieldsValue({
      name: cfg.name,
      provider: cfg.provider,
      apiFormat: cfg.apiFormat,
      baseUrl: cfg.baseUrl,
      apiKey: "",
      confirmApiKey: "",
      modelName: cfg.modelName,
      dimensions: cfg.dimensions,
      isActive: cfg.isActive,
    });
    setEmbModalOpen(true);
  };

  const handleEmbSave = async () => {
    try {
      const vals = await embForm.validateFields();
      setSaving(true);
      if (!vals.apiKey && !editingEmb) {
        messageApi.error("API Key 为必填项");
        setSaving(false);
        return;
      }
      const basePayload = {
        name: vals.name,
        provider: vals.provider,
        apiFormat: vals.apiFormat,
        baseUrl: vals.baseUrl,
        apiKey: vals.apiKey,
        modelName: vals.modelName,
        dimensions: vals.dimensions,
        isActive: vals.isActive,
      };
      if (editingEmb) {
        const updatePayload: EmbeddingConfigUpdate = { ...basePayload };
        if (!vals.apiKey) {
          delete updatePayload.apiKey;
        }
        await updateEmbeddingConfig(editingEmb.id, updatePayload);
        messageApi.success("配置已更新");
      } else {
        await createEmbeddingConfig(basePayload as EmbeddingConfigCreate);
        messageApi.success("配置已添加");
      }
      setEmbModalOpen(false);
      await loadAll();
    } catch (e) {
      if (e instanceof Error) messageApi.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteEmb = async (id: string) => {
    try {
      await deleteEmbeddingConfig(id);
      messageApi.success("配置已删除");
      await loadAll();
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  // ---- Render ----

  return (
    <>
      {contextHolder}
      <div className="workbench-intro">
        <div className="workbench-intro-main">
          <Typography.Text className="workbench-intro-eyebrow">System</Typography.Text>
          <Typography.Title level={4} style={{ margin: 0 }}>
            模型配置管理
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            统一管理 LLM 大模型和 Embedding 向量模型的 API 配置，支持多种供应商和 API 格式。
          </Typography.Paragraph>
        </div>
        <div className="workbench-intro-side">
          <Tag color="blue" icon={<ApiOutlined />}>多供应商</Tag>
          <Tag color="purple" icon={<ThunderboltOutlined />}>动态切换</Tag>
          <Tag color="green" icon={<CheckCircleFilled />}>连接测试</Tag>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : (
        <Tabs
          className="config-tabs"
          defaultActiveKey="llm"
          items={[
            {
              key: "llm",
              label: (
                <Space>
                  <ApiOutlined />
                  <span>LLM 大模型配置</span>
                </Space>
              ),
              children: (
                <LLMConfigPanel
                  configs={llmConfigs}
                  onAdd={openAddLlm}
                  onEdit={openEditLlm}
                  onDelete={handleDeleteLlm}
                  onSetDefault={handleSetDefault}
                />
              ),
            },
            {
              key: "embedding",
              label: (
                <Space>
                  <ExperimentOutlined />
                  <span>Embedding 向量模型配置</span>
                </Space>
              ),
              children: (
                <EmbeddingConfigPanel
                  configs={embConfigs}
                  onAdd={openAddEmb}
                  onEdit={openEditEmb}
                  onDelete={handleDeleteEmb}
                />
              ),
            },
            {
              key: "system",
              label: (
                <Space>
                  <SettingOutlined />
                  <span>系统预留</span>
                </Space>
              ),
              children: (
                <div className="config-system-panel">
                  <div className="empty-state">
                    <div className="empty-state-icon"><SettingOutlined /></div>
                    <div className="empty-state-text">
                      系统预留配置区域。<br />
                      未来将支持用户管理、项目管理等功能。
                    </div>
                  </div>
                </div>
              ),
            },
          ]}
        />
      )}

      {/* LLM Config Modal */}
      <Modal
        className="config-modal"
        open={llmModalOpen}
        title={
          <Space>
            <ApiOutlined />
            <span>{editingLlm ? "编辑 LLM 配置" : "添加 LLM 配置"}</span>
          </Space>
        }
        onCancel={() => setLlmModalOpen(false)}
        onOk={() => void handleLlmSave()}
        okText={saving ? "保存中..." : "保存"}
        cancelText="取消"
        confirmLoading={saving}
        width={640}
        destroyOnClose
      >
        <Form form={llmForm} layout="vertical" className="config-form">
          <Typography.Title level={5} style={{ marginTop: 0 }}>基本信息</Typography.Title>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="name"
                label="配置名称"
                rules={[{ required: true, message: "请输入配置名称" }]}
              >
                <Input placeholder="例如：我的 DeepSeek" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="isDefault" valuePropName="checked" label="默认配置">
                <Switch checkedChildren="默认" unCheckedChildren="非默认" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="provider"
            label="供应商"
            rules={[{ required: true, message: "请选择供应商" }]}
          >
            <Select
              showSearch
              placeholder="选择或搜索供应商"
              onChange={handleProviderChange}
              options={PROVIDER_PRESETS.map((p) => ({ value: p.provider, label: p.provider }))}
            />
          </Form.Item>

          <Typography.Title level={5}>连接信息</Typography.Title>
          <Form.Item
            name="apiFormat"
            label="API 格式"
            rules={[{ required: true, message: "请选择 API 格式" }]}
            extra="决定与 API 服务器通信的协议和鉴权方式"
          >
            <Select
              options={[
                { value: "openai_compatible", label: "OpenAI 兼容格式（base_url + Bearer Token）" },
                { value: "anthropic", label: "Anthropic Claude 格式" },
                { value: "google_ai", label: "Google AI Gemini 格式" },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="baseUrl"
            label="Base URL"
            rules={[{ required: true, message: "请输入 API Endpoint" }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="apiKey"
            label={editingLlm ? "API Key（留空则不更新）" : "API Key"}
            rules={editingLlm ? [] : [{ required: true, message: "API Key 为必填项" }]}
            extra="API 密钥仅在保存时传输，存储后不返回明文"
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item
            name="modelName"
            label="模型名称"
            rules={[{ required: true, message: "请输入模型名称" }]}
            extra="填写 AI 供应商提供的具体模型 ID，如 deepseek-reasoner"
          >
            <Input placeholder="deepseek-reasoner" />
          </Form.Item>

          <Typography.Title level={5}>高级设置</Typography.Title>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="maxOutputTokens" label="最大输出 Token" initialValue={131072}>
                <InputNumber style={{ width: "100%" }} min={1} max={10_000_000} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="timeoutSeconds" label="超时（秒）" initialValue={120}>
                <InputNumber style={{ width: "100%" }} min={10} max={600} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="supportsVision" valuePropName="checked" label="支持视觉" initialValue={false}>
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="supportsStructuredOutput" valuePropName="checked" label="支持结构化输出" initialValue={true}>
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="isActive" valuePropName="checked" label="启用状态" initialValue={true}>
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          {/* Connection Test */}
          <div className="config-test-row">
            <Button
              icon={<ApiOutlined />}
              onClick={() => void handleTestConnection()}
              loading={testingConn}
            >
              测试连接
            </Button>
            {connResult && (
              <span style={{ marginLeft: 12 }}>
                {connResult.ok ? (
                  <Tag color="success" icon={<CheckCircleFilled />}>连接成功</Tag>
                ) : (
                  <Tag color="error" icon={<CloseCircleFilled />}>连接失败</Tag>
                )}
                <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                  {connResult.message}
                </Typography.Text>
              </span>
            )}
          </div>
        </Form>
      </Modal>

      {/* Embedding Config Modal */}
      <Modal
        className="config-modal"
        open={embModalOpen}
        title={
          <Space>
            <ExperimentOutlined />
            <span>{editingEmb ? "编辑 Embedding 配置" : "添加 Embedding 配置"}</span>
          </Space>
        }
        onCancel={() => setEmbModalOpen(false)}
        onOk={() => void handleEmbSave()}
        okText={saving ? "保存中..." : "保存"}
        cancelText="取消"
        confirmLoading={saving}
        width={640}
        destroyOnClose
      >
        <Form form={embForm} layout="vertical" className="config-form">
          <Typography.Title level={5} style={{ marginTop: 0 }}>基本信息</Typography.Title>
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: "请输入配置名称" }]}
          >
            <Input placeholder="例如：我的 Embedding" />
          </Form.Item>

          <Form.Item
            name="provider"
            label="供应商"
            rules={[{ required: true, message: "请选择供应商" }]}
          >
            <Select
              showSearch
              placeholder="选择或搜索供应商"
              options={[
                { value: "OpenAI", label: "OpenAI" },
                { value: "Azure OpenAI", label: "Azure OpenAI" },
                { value: "通义千问", label: "通义千问（百炼）" },
                { value: "硅基流动", label: "硅基流动" },
                { value: "DeepSeek", label: "DeepSeek" },
              ]}
            />
          </Form.Item>

          <Typography.Title level={5}>连接信息</Typography.Title>
          <Form.Item
            name="baseUrl"
            label="Base URL"
            rules={[{ required: true, message: "请输入 API Endpoint" }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="apiKey"
            label={editingEmb ? "API Key（留空则不更新）" : "API Key"}
            rules={editingEmb ? [] : [{ required: true, message: "API Key 为必填项" }]}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item
            name="modelName"
            label="Embedding 模型名称"
            rules={[{ required: true, message: "请输入模型名称" }]}
          >
            <Input placeholder="text-embedding-3-small" />
          </Form.Item>

          <Form.Item
            name="dimensions"
            label="向量维度"
            initialValue={0}
            extra="百炼等模型可指定维度（0 表示不指定，使用模型默认值）"
          >
            <InputNumber style={{ width: "100%" }} min={0} max={4096} placeholder="0 = 不指定" />
          </Form.Item>

          <Form.Item name="isActive" valuePropName="checked" label="启用状态" initialValue={true}>
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

// ---- Sub-panels ----

function LLMConfigCard({
  cfg,
  onEdit,
  onDelete,
  onSetDefault,
}: {
  cfg: LLMConfig;
  onEdit: (cfg: LLMConfig) => void;
  onDelete: (id: string) => void;
  onSetDefault: (id: string) => void;
}) {
  const providerColor: Record<string, string> = {
    openai: "blue",
    deepseek: "cyan",
    anthropic: "orange",
    google: "green",
    minimax: "purple",
    通义千问: "gold",
  };
  const color = providerColor[cfg.provider.toLowerCase()] ?? "default";

  return (
    <Card
      className="config-card"
      size="small"
      actions={[
        cfg.isDefault ? (
          <Tooltip title="当前默认"><StarFilled style={{ color: "#fadb14", fontSize: 16 }} /></Tooltip>
        ) : (
          <Tooltip title="设为默认">
            <Button type="text" size="small" icon={<StarFilled />} onClick={() => onSetDefault(cfg.id)}>设为默认</Button>
          </Tooltip>
        ),
        <Tooltip title="编辑"><Button type="text" size="small" icon={<EditOutlined />} onClick={() => onEdit(cfg)}>编辑</Button></Tooltip>,
        <Popconfirm
          title="确认删除此配置？"
          description="删除后无法恢复。"
          onConfirm={() => onDelete(cfg.id)}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Tooltip title="删除"><Button type="text" size="small" danger icon={<DeleteOutlined />}>删除</Button></Tooltip>
        </Popconfirm>,
      ]}
    >
      <div className="config-card-header">
        <Space>
          <Typography.Text strong style={{ fontSize: 15 }}>{cfg.name}</Typography.Text>
          {cfg.isDefault && <Tag color="gold" icon={<StarFilled />} style={{ fontSize: 11 }}>默认</Tag>}
          {cfg.isActive ? (
            <Tag color="success" style={{ fontSize: 11 }}>启用</Tag>
          ) : (
            <Tag color="default" style={{ fontSize: 11 }}>禁用</Tag>
          )}
        </Space>
        <Tag color={color}>{cfg.provider}</Tag>
      </div>
      <div className="config-card-body">
        <Space wrap style={{ fontSize: 12 }} size={[4, 4]}>
          <span>
            <Typography.Text type="secondary">模型：</Typography.Text>
            <Typography.Text code style={{ fontSize: 11 }}>{cfg.modelName}</Typography.Text>
          </span>
          <span>
            <Typography.Text type="secondary">格式：</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{cfg.apiFormat}</Typography.Text>
          </span>
          <span>
            <Typography.Text type="secondary">Token 上限：</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{cfg.maxOutputTokens.toLocaleString()}</Typography.Text>
          </span>
        </Space>
        <div style={{ marginTop: 6 }}>
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            {cfg.baseUrl}
          </Typography.Text>
        </div>
        <div className="config-card-tags" style={{ marginTop: 8 }}>
          {cfg.supportsVision && <Tag color="cyan" style={{ fontSize: 11 }}>视觉</Tag>}
          {cfg.supportsStructuredOutput && <Tag color="purple" style={{ fontSize: 11 }}>结构化</Tag>}
        </div>
      </div>
    </Card>
  );
}

function LLMConfigPanel({
  configs,
  onAdd,
  onEdit,
  onDelete,
  onSetDefault,
}: {
  configs: LLMConfig[];
  onAdd: () => void;
  onEdit: (cfg: LLMConfig) => void;
  onDelete: (id: string) => void;
  onSetDefault: (id: string) => void;
}) {
  return (
    <div className="config-panel">
      <div className="config-panel-header">
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            共 {configs.length} 个配置，已启用 {configs.filter((c) => c.isActive).length} 个
          </Typography.Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
          添加 LLM 配置
        </Button>
      </div>
      {configs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><ApiOutlined /></div>
          <div className="empty-state-text">
            暂无可用配置。<br />
            点击上方「添加 LLM 配置」添加你的第一个模型配置。
          </div>
        </div>
      ) : (
        <Row gutter={[16, 16]}>
          {configs.map((cfg) => (
            <Col xs={24} md={12} xl={8} key={cfg.id}>
              <LLMConfigCard
                cfg={cfg}
                onEdit={onEdit}
                onDelete={onDelete}
                onSetDefault={onSetDefault}
              />
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}

function EmbeddingConfigCard({
  cfg,
  onEdit,
  onDelete,
}: {
  cfg: EmbeddingConfig;
  onEdit: (cfg: EmbeddingConfig) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <Card
      className="config-card"
      size="small"
      actions={[
        cfg.isActive ? (
          <Tag color="success" style={{ fontSize: 11 }}>启用</Tag>
        ) : (
          <Tag color="default" style={{ fontSize: 11 }}>禁用</Tag>
        ),
        <Tooltip title="编辑"><Button type="text" size="small" icon={<EditOutlined />} onClick={() => onEdit(cfg)}>编辑</Button></Tooltip>,
        <Popconfirm
          title="确认删除此配置？"
          onConfirm={() => onDelete(cfg.id)}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Tooltip title="删除"><Button type="text" size="small" danger icon={<DeleteOutlined />}>删除</Button></Tooltip>
        </Popconfirm>,
      ]}
    >
      <div className="config-card-header">
        <Typography.Text strong style={{ fontSize: 15 }}>{cfg.name}</Typography.Text>
      </div>
      <div className="config-card-body">
        <Space wrap style={{ fontSize: 12 }} size={[4, 4]}>
          <span>
            <Typography.Text type="secondary">供应商：</Typography.Text>
            <Typography.Text type="secondary">{cfg.provider}</Typography.Text>
          </span>
          <span>
            <Typography.Text type="secondary">模型：</Typography.Text>
            <Typography.Text code style={{ fontSize: 11 }}>{cfg.modelName}</Typography.Text>
          </span>
          {cfg.dimensions > 0 && (
            <span>
              <Typography.Text type="secondary">维度：</Typography.Text>
              <Typography.Text type="secondary">{cfg.dimensions}</Typography.Text>
            </span>
          )}
        </Space>
      </div>
    </Card>
  );
}

function EmbeddingConfigPanel({
  configs,
  onAdd,
  onEdit,
  onDelete,
}: {
  configs: EmbeddingConfig[];
  onAdd: () => void;
  onEdit: (cfg: EmbeddingConfig) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="config-panel">
      <div className="config-panel-header">
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            共 {configs.length} 个配置，已启用 {configs.filter((c) => c.isActive).length} 个
          </Typography.Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
          添加 Embedding 配置
        </Button>
      </div>
      {configs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><ExperimentOutlined /></div>
          <div className="empty-state-text">
            暂无可用配置。<br />
            Embedding 用于知识库文档的向量化和语义检索。
          </div>
        </div>
      ) : (
        <Row gutter={[16, 16]}>
          {configs.map((cfg) => (
            <Col xs={24} md={12} xl={8} key={cfg.id}>
              <EmbeddingConfigCard
                cfg={cfg}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}
