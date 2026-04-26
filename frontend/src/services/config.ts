import { API_BASE_URL, apiFetchPath, resolveApiAbsoluteUrl } from "./api";

export interface LLMConfig {
  id: string;
  userId: string | null;
  name: string;
  provider: string;
  apiFormat: "openai_compatible" | "anthropic" | "google_ai";
  baseUrl: string;
  apiKeyMasked: string;
  modelName: string;
  maxOutputTokens: number;
  timeoutSeconds: number;
  supportsVision: boolean;
  supportsStructuredOutput: boolean;
  extraConfig: Record<string, unknown> | null;
  isDefault: boolean;
  isActive: boolean;
  displayOrder: number;
  createdAt: string;
  updatedAt: string | null;
}

export interface LLMConfigCreate {
  name: string;
  provider: string;
  apiFormat: string;
  baseUrl: string;
  apiKey: string;
  modelName: string;
  maxOutputTokens?: number;
  timeoutSeconds?: number;
  supportsVision?: boolean;
  supportsStructuredOutput?: boolean;
  extraConfig?: Record<string, unknown> | null;
  isDefault?: boolean;
  isActive?: boolean;
  displayOrder?: number;
}

export interface LLMConfigUpdate {
  name?: string;
  provider?: string;
  apiFormat?: string;
  baseUrl?: string;
  apiKey?: string;
  modelName?: string;
  maxOutputTokens?: number;
  timeoutSeconds?: number;
  supportsVision?: boolean;
  supportsStructuredOutput?: boolean;
  extraConfig?: Record<string, unknown> | null;
  isActive?: boolean;
  displayOrder?: number;
}

export interface EmbeddingConfig {
  id: string;
  userId: string | null;
  name: string;
  provider: string;
  apiFormat: string;
  baseUrl: string;
  apiKeyMasked: string;
  modelName: string;
  dimensions: number;
  extraConfig: Record<string, unknown> | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
}

export interface EmbeddingConfigCreate {
  name: string;
  provider: string;
  apiFormat?: string;
  baseUrl: string;
  apiKey: string;
  modelName: string;
  dimensions?: number;
  extraConfig?: Record<string, unknown> | null;
  isActive?: boolean;
}

export interface EmbeddingConfigUpdate {
  name?: string;
  provider?: string;
  apiFormat?: string;
  baseUrl?: string;
  apiKey?: string;
  modelName?: string;
  dimensions?: number;
  extraConfig?: Record<string, unknown> | null;
  isActive?: boolean;
}

export interface TestConnectionRequest {
  provider: string;
  apiFormat: string;
  baseUrl: string;
  apiKey: string;
  modelName: string;
  timeoutSeconds?: number;
}

export interface TestConnectionResponse {
  ok: boolean;
  message: string;
}

export interface SetDefaultResponse {
  ok: boolean;
  message: string;
}

export interface MigrateStatusResponse {
  needsMigration: boolean;
  llmConfigsCount: number;
  embeddingConfigsCount: number;
  envHasLlmConfig: boolean;
  envHasEmbeddingConfig: boolean;
}

async function jsonRequest<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? `请求失败（${response.status}），请稍后重试。`);
  }
  if (response.status === 204) return undefined as unknown as T;
  return (await response.json()) as T;
}

function fmtPath(p: string) {
  return apiFetchPath(p.startsWith("/") ? p : `/${p}`);
}

// ---- LLM Config ----

export async function listLLMConfigs(): Promise<LLMConfig[]> {
  return jsonRequest<LLMConfig[]>(fmtPath("/api/v1/config/llm"), { method: "GET" });
}

export async function getLLMConfig(id: string): Promise<LLMConfig> {
  return jsonRequest<LLMConfig>(fmtPath(`/api/v1/config/llm/${id}`), { method: "GET" });
}

export async function createLLMConfig(payload: LLMConfigCreate): Promise<LLMConfig> {
  return jsonRequest<LLMConfig>(fmtPath("/api/v1/config/llm"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateLLMConfig(id: string, payload: LLMConfigUpdate): Promise<LLMConfig> {
  return jsonRequest<LLMConfig>(fmtPath(`/api/v1/config/llm/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteLLMConfig(id: string): Promise<void> {
  return jsonRequest<void>(fmtPath(`/api/v1/config/llm/${id}`), { method: "DELETE" });
}

export async function setDefaultLLMConfig(id: string): Promise<SetDefaultResponse> {
  return jsonRequest<SetDefaultResponse>(fmtPath(`/api/v1/config/llm/${id}/set-default`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

// ---- Embedding Config ----

export async function listEmbeddingConfigs(): Promise<EmbeddingConfig[]> {
  return jsonRequest<EmbeddingConfig[]>(fmtPath("/api/v1/config/embedding"), { method: "GET" });
}

export async function getEmbeddingConfig(id: string): Promise<EmbeddingConfig> {
  return jsonRequest<EmbeddingConfig>(fmtPath(`/api/v1/config/embedding/${id}`), { method: "GET" });
}

export async function createEmbeddingConfig(payload: EmbeddingConfigCreate): Promise<EmbeddingConfig> {
  return jsonRequest<EmbeddingConfig>(fmtPath("/api/v1/config/embedding"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateEmbeddingConfig(id: string, payload: EmbeddingConfigUpdate): Promise<EmbeddingConfig> {
  return jsonRequest<EmbeddingConfig>(fmtPath(`/api/v1/config/embedding/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteEmbeddingConfig(id: string): Promise<void> {
  return jsonRequest<void>(fmtPath(`/api/v1/config/embedding/${id}`), { method: "DELETE" });
}

// ---- Test Connection ----

export async function testLLMConnection(payload: TestConnectionRequest): Promise<TestConnectionResponse> {
  return jsonRequest<TestConnectionResponse>(fmtPath("/api/v1/config/llm/test-connection"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ---- Migration ----

export async function getMigrateStatus(): Promise<MigrateStatusResponse> {
  return jsonRequest<MigrateStatusResponse>(fmtPath("/api/v1/config/migrate-status"), { method: "GET" });
}

export async function migrateConfigs(): Promise<{ ok: boolean; migrated: { llm: number; embedding: number } }> {
  return jsonRequest(fmtPath("/api/v1/config/migrate"), { method: "POST" });
}

// ---- Provider presets ----

export interface ProviderPreset {
  provider: string;
  apiFormat: string;
  baseUrl: string;
  supportsVision: boolean;
  supportsStructuredOutput: boolean;
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  {
    provider: "OpenAI",
    apiFormat: "openai_compatible",
    baseUrl: "https://api.openai.com/v1",
    supportsVision: true,
    supportsStructuredOutput: true,
  },
  {
    provider: "DeepSeek",
    apiFormat: "openai_compatible",
    baseUrl: "https://api.deepseek.com/v1",
    supportsVision: false,
    supportsStructuredOutput: true,
  },
  {
    provider: "MiniMax",
    apiFormat: "openai_compatible",
    baseUrl: "https://api.minimaxi.com/v1",
    supportsVision: false,
    supportsStructuredOutput: false,
  },
  {
    provider: "通义千问",
    apiFormat: "openai_compatible",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    supportsVision: false,
    supportsStructuredOutput: true,
  },
  {
    provider: "硅基流动",
    apiFormat: "openai_compatible",
    baseUrl: "https://api.siliconflow.cn/v1",
    supportsVision: false,
    supportsStructuredOutput: true,
  },
  {
    provider: "Azure OpenAI",
    apiFormat: "openai_compatible",
    baseUrl: "https://{your-resource}.openai.azure.com/v1",
    supportsVision: true,
    supportsStructuredOutput: true,
  },
  {
    provider: "Anthropic",
    apiFormat: "anthropic",
    baseUrl: "https://api.anthropic.com",
    supportsVision: false,
    supportsStructuredOutput: false,
  },
  {
    provider: "Google AI",
    apiFormat: "google_ai",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    supportsVision: false,
    supportsStructuredOutput: false,
  },
];

export function findPreset(provider: string): ProviderPreset | undefined {
  return PROVIDER_PRESETS.find((p) => p.provider === provider);
}
