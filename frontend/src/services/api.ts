export interface TestCaseItem {
  caseId: string;
  title: string;
  preconditions: string[];
  steps: string[];
  expectedResult: string;
  category: string;
  priority: string;
  module: string;
  moduleId: string;
  confirmationNote?: string | null;
  sourceBatch?: string | null;
}

export interface ReviewQuestionItem {
  id: string;
  questionType: string;
  description: string;
  module: string;
  suggestion: string;
}

export interface GenerationMetadata {
  caseCount: number;
  categoryCounts: Record<string, number>;
  moduleCounts: Record<string, number>;
  priorityCounts: Record<string, number>;
  reviewQuestions: ReviewQuestionItem[];
  warnings: string[];
  truncated: boolean;
  incompleteCategories: string[];
}

export interface GenerateResult {
  generationId: string;
  markdown: string;
  modelName: string;
  attachmentCount: number;
  createdAt: string;
  cases: TestCaseItem[];
  metadata: GenerationMetadata;
}

export interface ReviewModuleItem {
  id: string;
  name: string;
  description: string;
  subFeatures: string[];
}

export interface ReviewResult {
  modules: ReviewModuleItem[];
  questions: ReviewQuestionItem[];
  businessRules: string[];
  dataConstraints: Record<string, unknown>[];
  modelName: string;
}

export interface RequirementSummaryResult {
  summaryText: string;
  modules: string[];
  businessRules: string[];
  dataConstraints: string[];
  openQuestions: string[];
  modelName: string;
}

/**
 * 本地开发默认走 Vite 同源 `/api` 代理，避免：
 * - 页面在 localhost:5173、接口写死 127.0.0.1:8000 时的跨源长连接被 Chrome 挂起（net::ERR_NETWORK_IO_SUSPENDED）
 * - 直连后端时绕过代理，无法享受上面配置的 proxy 超长超时
 *
 * 若需在开发环境直连其它地址，可设置 `VITE_DEV_DIRECT_API=1` 并配置 `VITE_API_BASE_URL`。
 */
export const API_BASE_URL =
  import.meta.env.DEV && import.meta.env.VITE_DEV_DIRECT_API !== "1"
    ? ""
    : (import.meta.env.VITE_API_BASE_URL ?? "");

export function apiFetchPath(pathWithLeadingSlash: string): string {
  const p = pathWithLeadingSlash.startsWith("/")
    ? pathWithLeadingSlash
    : `/${pathWithLeadingSlash}`;
  return /^https?:\/\//i.test(API_BASE_URL)
    ? `${API_BASE_URL.replace(/\/$/, "")}${p}`
    : `${API_BASE_URL}${p}`;
}

/** 浏览器实际访问的绝对 URL（便于与 Network、后端日志对照） */
export function resolveApiAbsoluteUrl(pathWithLeadingSlash: string): string {
  const p = pathWithLeadingSlash.startsWith("/")
    ? pathWithLeadingSlash
    : `/${pathWithLeadingSlash}`;
  const fetchUrl = apiFetchPath(p);
  if (typeof window === "undefined") {
    return fetchUrl;
  }
  if (/^https?:\/\//i.test(fetchUrl)) {
    return fetchUrl;
  }
  try {
    return new URL(fetchUrl || p, window.location.origin).href;
  } catch {
    return fetchUrl || p;
  }
}

function formatJsonDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const s = detail
      .map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item)))
      .join("；");
    return s.length > 400 ? `${s.slice(0, 400)}…` : s;
  }
  if (typeof detail === "object") {
    const s = JSON.stringify(detail);
    return s.length > 400 ? `${s.slice(0, 400)}…` : s;
  }
  return String(detail);
}

async function readHttpErrorDetail(response: Response): Promise<string> {
  const raw = await response.text().catch(() => "");
  const trimmed = raw.trim();
  if (!trimmed) {
    return [response.status, response.statusText].filter(Boolean).join(" ");
  }
  const ctype = response.headers.get("content-type") ?? "";
  if (ctype.includes("application/json")) {
    try {
      const j = JSON.parse(trimmed) as { detail?: unknown };
      const d = formatJsonDetail(j.detail);
      if (d) return d;
    } catch {
      /* fall through */
    }
  }
  return trimmed.length > 320 ? `${trimmed.slice(0, 320)}…` : trimmed;
}

/** 统一前缀，便于在 Console 搜索（勿依赖 minify 后的函数名） */
function logApiFailure(label: string, info: Record<string, unknown>): void {
  console.error(`[hpr-api] ${label}`, info);
}

function isAbortError(e: unknown): boolean {
  return (
    (e instanceof DOMException && e.name === "AbortError") ||
    (e instanceof Error && e.name === "AbortError")
  );
}

/** response.ok 已为 true 时解析 JSON；若实为 HTML（常见于未代理到后端）则给出可操作建议 */
async function parseSuccessJson<T>(response: Response, absUrl: string, logLabel: string): Promise<T> {
  const text = await response.text();
  const head = text.trimStart().slice(0, 96).toLowerCase();
  if (head.startsWith("<!doctype") || head.startsWith("<html")) {
    const healthUrl = resolveApiAbsoluteUrl("/api/health");
    logApiFailure(`${logLabel}:html-not-json`, {
      url: absUrl,
      contentType: response.headers.get("content-type"),
      snippet: text.slice(0, 240),
    });
    throw new Error(
      `接口返回了 HTML 网页而不是 JSON。\n\n常见原因：后端未启动、/api 未代理到 FastAPI，或误用静态文件打开页面。\n\n请先确认：浏览器访问 ${healthUrl} 能看到 {"status":"ok"}；本地开发请同时运行 Vite（5173）与后端（8000），或使用已配置 /api 代理的 npm run preview。\n\n请求：GET ${absUrl}`
    );
  }
  try {
    return JSON.parse(text) as T;
  } catch (e) {
    logApiFailure(`${logLabel}:json`, { url: absUrl, error: e, snippet: text.slice(0, 160) });
    throw new Error(`响应不是合法 JSON\n请求：GET ${absUrl}`);
  }
}

export type ExportFormat = "md" | "csv" | "xlsx";

export interface ModelOption {
  key: string;
  label: string;
  provider: string;
  modelName: string;
  supportsVision: boolean;
  supportsStructuredOutput: boolean;
}

export async function reviewRequirement(
  requirementText: string,
  documentFiles: File[],
  imageFiles: File[],
  modelKey?: string
): Promise<ReviewResult> {
  const formData = new FormData();
  formData.append("requirement_text", requirementText);
  if (modelKey) {
    formData.append("modelKey", modelKey);
  }
  documentFiles.forEach((file) => formData.append("documentFiles", file));
  imageFiles.forEach((file) => formData.append("imageFiles", file));

  const response = await fetch(`${API_BASE_URL}/api/v1/generate/review`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "需求评审失败，请稍后重试。");
  }

  return (await response.json()) as ReviewResult;
}

const ACTIVE_GENERATION_TASK_KEY = "hpr-active-generation-task";

export function getStoredGenerationTaskId(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_GENERATION_TASK_KEY);
  } catch {
    return null;
  }
}

export function setStoredGenerationTaskId(taskId: string | null): void {
  try {
    if (taskId) {
      window.localStorage.setItem(ACTIVE_GENERATION_TASK_KEY, taskId);
    } else {
      window.localStorage.removeItem(ACTIVE_GENERATION_TASK_KEY);
    }
  } catch {
    /* ignore */
  }
}

export interface TaskPhaseItem {
  name: string;
  label: string;
  status: string;
  elapsedSeconds?: number;
}

export interface TaskStatusPayload {
  taskId: string;
  status: string;
  currentPhase: string;
  phaseLabel: string;
  progress: number;
  phases: TaskPhaseItem[];
  elapsedSeconds: number;
  result: GenerateResult | null;
  errorMessage?: string | null;
  requirementPreview?: string | null;
  caseCount?: number | null;
}

export interface TaskListItemPayload {
  taskId: string;
  status: string;
  requirementPreview: string;
  caseCount?: number | null;
  createdAt: string;
  modelName?: string | null;
}

export async function submitGenerateAsync(
  requirementText: string,
  documentFiles: File[],
  imageFiles: File[],
  modelKey?: string
): Promise<{ taskId: string; status: string }> {
  const formData = new FormData();
  formData.append("requirement_text", requirementText);
  if (modelKey) {
    formData.append("modelKey", modelKey);
  }
  documentFiles.forEach((file) => formData.append("documentFiles", file));
  imageFiles.forEach((file) => formData.append("imageFiles", file));

  const response = await fetch(`${API_BASE_URL}/api/v1/generate/async`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "提交生成任务失败，请稍后重试。");
  }
  return (await response.json()) as { taskId: string; status: string };
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusPayload> {
  const path = `/api/v1/generate/tasks/${encodeURIComponent(taskId)}`;
  const url = apiFetchPath(path);
  const abs = resolveApiAbsoluteUrl(path);

  let response: Response;
  try {
    response = await fetch(url);
  } catch (e) {
    logApiFailure("getTaskStatus:network", { url: abs, error: e });
    const hint = e instanceof Error ? e.message : String(e);
    throw new Error(
      `加载该条生成历史失败（网络）：${hint}\n请求：GET ${abs}`
    );
  }

  if (!response.ok) {
    const detail = await readHttpErrorDetail(response);
    logApiFailure("getTaskStatus:http", { url: abs, status: response.status, detail });
    throw new Error(
      `加载该条生成历史失败（HTTP ${response.status}）${detail ? `：${detail}` : ""}\n请求：GET ${abs}`
    );
  }

  return parseSuccessJson<TaskStatusPayload>(response, abs, "getTaskStatus");
}

export async function listGenerationTasks(
  params: {
    page?: number;
    pageSize?: number;
  },
  init?: RequestInit
): Promise<{ items: TaskListItemPayload[]; total: number; page: number; pageSize: number }> {
  const qs = new URLSearchParams();
  qs.set("page", String(params.page ?? 1));
  qs.set("pageSize", String(params.pageSize ?? 30));
  const path = `/api/v1/generate/tasks?${qs.toString()}`;
  const url = apiFetchPath(path);
  const abs = resolveApiAbsoluteUrl(path);

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (e) {
    if (isAbortError(e)) {
      throw e;
    }
    logApiFailure("listGenerationTasks:network", { url: abs, error: e });
    const hint = e instanceof Error ? e.message : String(e);
    throw new Error(
      `加载生成历史列表失败（网络）：${hint}\n请求：GET ${abs}\n请确认后端 API 已启动；本地开发通常需同时运行 Vite(5173) 与后端(8000)，或通过 VITE_API_BASE_URL 指向可访问的后端。`
    );
  }

  if (!response.ok) {
    const detail = await readHttpErrorDetail(response);
    logApiFailure("listGenerationTasks:http", {
      url: abs,
      status: response.status,
      detail,
    });
    throw new Error(
      `加载生成历史列表失败（HTTP ${response.status}）${detail ? `：${detail}` : ""}\n请求：GET ${abs}`
    );
  }

  return parseSuccessJson<{
    items: TaskListItemPayload[];
    total: number;
    page: number;
    pageSize: number;
  }>(response, abs, "listGenerationTasks");
}

export async function cancelGenerationTask(taskId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/generate/tasks/${taskId}/cancel`, {
    method: "POST",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "取消任务失败。");
  }
}

export interface ClearTasksResponse {
  ok: boolean;
  deletedCount: number;
  cancelledRunningCount: number;
}

export async function clearAllGenerationTasks(): Promise<ClearTasksResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/generate/tasks`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "清理任务失败。");
  }
  return (await response.json()) as ClearTasksResponse;
}

export type WsMessage =
  | { type: "status"; data: TaskStatusPayload }
  | { type: "error"; message: string }
  | { type: "pong" };

export type WsStatusHandler = (status: TaskStatusPayload) => void;
export type WsErrorHandler = (message: string) => void;

interface WsConnection {
  ws: WebSocket;
  handlers: {
    onStatus: WsStatusHandler;
    onError: WsErrorHandler;
    onClose: () => void;
  };
}

const _wsConnections: Map<string, WsConnection> = new Map();

export function connectTaskWebSocket(
  taskId: string,
  onStatus: WsStatusHandler,
  onError: WsErrorHandler,
  onClose: () => void
): () => void {
  if (_wsConnections.has(taskId)) {
    disconnectTaskWebSocket(taskId);
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrlBase =
    import.meta.env.VITE_API_BASE_URL && !import.meta.env.DEV
      ? import.meta.env.VITE_API_BASE_URL.replace(/^https?:\/\//, "")
      : window.location.host;
  const wsUrl = `${wsProtocol}//${wsUrlBase}/api/v1/generate/ws/${encodeURIComponent(taskId)}`;

  const ws = new WebSocket(wsUrl);
  let pongTimer: ReturnType<typeof setTimeout> | null = null;

  ws.addEventListener("message", (event: MessageEvent) => {
    let msg: WsMessage;
    try {
      msg = JSON.parse(event.data as string) as WsMessage;
    } catch {
      return;
    }
    if (msg.type === "status") {
      onStatus(msg.data);
      if (msg.data.status === "succeeded" || msg.data.status === "failed" || msg.data.status === "cancelled") {
        ws.close();
      }
    } else if (msg.type === "error") {
      onError(msg.message);
    }
  });

  ws.addEventListener("close", () => {
    if (pongTimer) clearTimeout(pongTimer);
    _wsConnections.delete(taskId);
    onClose();
  });

  ws.addEventListener("error", () => {
    ws.close();
  });

  // Keep-alive ping
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send("ping");
      pongTimer = setTimeout(() => {
        ws.close();
      }, 5000);
    }
  }, 25000);

  ws.addEventListener("message", (event: MessageEvent) => {
    if ((event.data as string) === "pong" && pongTimer) {
      clearTimeout(pongTimer);
      pongTimer = null;
    }
  });

  _wsConnections.set(taskId, { ws, handlers: { onStatus, onError, onClose } });

  return () => {
    clearInterval(pingInterval);
    if (pongTimer) clearTimeout(pongTimer);
    ws.close();
    _wsConnections.delete(taskId);
  };
}

export function disconnectTaskWebSocket(taskId: string): void {
  const conn = _wsConnections.get(taskId);
  if (conn) {
    conn.ws.close();
    _wsConnections.delete(taskId);
  }
}

export async function generateTestCases(
  requirementText: string,
  documentFiles: File[],
  imageFiles: File[],
  modelKey?: string
): Promise<GenerateResult> {
  const formData = new FormData();
  formData.append("requirement_text", requirementText);
  if (modelKey) {
    formData.append("modelKey", modelKey);
  }

  documentFiles.forEach((file) => {
    formData.append("documentFiles", file);
  });
  imageFiles.forEach((file) => {
    formData.append("imageFiles", file);
  });

  const response = await fetch(`${API_BASE_URL}/api/v1/generate`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "生成失败，请稍后重试。");
  }

  return (await response.json()) as GenerateResult;
}

export async function summarizeRequirementFromFiles(
  requirementText: string,
  documentFiles: File[],
  imageFiles: File[],
  modelKey?: string
): Promise<RequirementSummaryResult> {
  const formData = new FormData();
  formData.append("requirement_text", requirementText);
  if (modelKey) {
    formData.append("modelKey", modelKey);
  }

  documentFiles.forEach((file) => {
    formData.append("documentFiles", file);
  });
  imageFiles.forEach((file) => {
    formData.append("imageFiles", file);
  });

  const response = await fetch(`${API_BASE_URL}/api/v1/generate/summary`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "需求摘要提炼失败，请稍后重试。");
  }

  return (await response.json()) as RequirementSummaryResult;
}

export interface QuickGenerateResult {
  content: string;
  modelName: string;
  generatedAt: string;
}

export async function quickGenerate(
  requirementText: string,
  documentFiles: File[],
  imageFiles: File[],
  modelKey?: string,
): Promise<QuickGenerateResult> {
  const formData = new FormData();
  formData.append("requirement_text", requirementText);
  if (modelKey) {
    formData.append("modelKey", modelKey);
  }
  documentFiles.forEach((file) => {
    formData.append("documentFiles", file);
  });
  imageFiles.forEach((file) => {
    formData.append("imageFiles", file);
  });

  const response = await fetch(`${API_BASE_URL}/api/v1/generate/quick`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "快速生成失败，请稍后重试。");
  }

  return (await response.json()) as QuickGenerateResult;
}

// ============================================================
// Quick Generate History
// ============================================================

export interface QuickHistoryItem {
  id: string;
  requirementPreview: string;
  outputContent: string;
  modelName: string;
  createdAt: string;
}

export interface QuickHistoryListResponse {
  items: QuickHistoryItem[];
  total: number;
  page: number;
  pageSize: number;
}

function _buildQs(params: { page?: number; pageSize?: number }): string {
  const p = new URLSearchParams();
  if (params.page != null) p.set("page", String(params.page));
  if (params.pageSize != null) p.set("pageSize", String(params.pageSize));
  return p.toString();
}

export async function listQuickGenerateHistory(
  params: { page?: number; pageSize?: number } = {},
): Promise<QuickHistoryListResponse> {
  const qs = _buildQs(params);
  const path = `/api/v1/generate/quick/history${qs ? `?${qs}` : ""}`;
  const abs = resolveApiAbsoluteUrl(path);

  let response: Response;
  try {
    response = await fetch(abs);
  } catch (e) {
    if (isAbortError(e)) throw e;
    logApiFailure("listQuickGenerateHistory:network", { url: abs, error: e });
    const hint = e instanceof Error ? e.message : String(e);
    throw new Error(`加载快速生成历史失败（网络）：${hint}\n请求：GET ${abs}`);
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? `加载快速生成历史失败（HTTP ${response.status}）`);
  }

  return (await response.json()) as QuickHistoryListResponse;
}

export interface QuickHistoryClearResponse {
  ok: boolean;
  deletedCount: number;
}

export async function clearQuickGenerateHistory(): Promise<QuickHistoryClearResponse> {
  const path = "/api/v1/generate/quick/history";
  const abs = resolveApiAbsoluteUrl(path);

  const response = await fetch(abs, { method: "DELETE" });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "清空历史失败。");
  }
  return (await response.json()) as QuickHistoryClearResponse;
}

export async function listModels(): Promise<ModelOption[]> {
  const path = "/api/v1/models";
  const url = apiFetchPath(path);
  const abs = resolveApiAbsoluteUrl(path);

  let response: Response;
  try {
    response = await fetch(url);
  } catch (e) {
    logApiFailure("listModels:network", { url: abs, error: e });
    const hint = e instanceof Error ? e.message : String(e);
    throw new Error(
      `加载模型列表失败（网络）：${hint}\n请求：GET ${abs}\n请确认后端 API 已启动；本地开发需 Vite 与后端同时运行或设置 VITE_API_BASE_URL。`
    );
  }

  if (!response.ok) {
    const detail = await readHttpErrorDetail(response);
    logApiFailure("listModels:http", { url: abs, status: response.status, detail });
    throw new Error(
      `加载模型列表失败（HTTP ${response.status}）${detail ? `：${detail}` : ""}\n请求：GET ${abs}`
    );
  }

  return parseSuccessJson<ModelOption[]>(response, abs, "listModels");
}

// ---- Knowledge Base ----

export interface KnowledgeDocumentItem {
  id: string;
  title: string;
  docType: string;
  moduleTags: string[];
  status: string;
  summary: string | null;
  sourceType: string;
  sourceFilename: string | null;
  embeddingStatus: string;
  createdAt: string;
  updatedAt: string | null;
  chunkCount: number;
}

export interface KnowledgeChunkItem {
  id: string;
  chunkIndex: number;
  chunkText: string;
  tokenCount: number;
  hasEmbedding: boolean;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocumentItem {
  content: string;
  structuredPayload: Record<string, unknown> | null;
  chunks: KnowledgeChunkItem[];
}

export interface KnowledgeDocumentListResponse {
  items: KnowledgeDocumentItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface KnowledgeStatsResponse {
  totalDocuments: number;
  activeDocuments: number;
  typeCounts: Record<string, number>;
  embeddingCounts: Record<string, number>;
  totalChunks: number;
}

export interface KnowledgeSearchResultItem {
  documentId: string;
  title: string;
  docType: string;
  summary: string | null;
  relevanceScore: number;
  matchSource: string;
}

export interface KnowledgeDocumentCreatePayload {
  title: string;
  docType: string;
  moduleTags: string[];
  content: string;
  structuredPayload?: Record<string, unknown> | null;
}

export interface KnowledgeDocumentUpdatePayload {
  title?: string;
  docType?: string;
  moduleTags?: string[];
  status?: string;
  summary?: string;
  content?: string;
  structuredPayload?: Record<string, unknown> | null;
}

export async function jsonRequest<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "请求失败，请稍后重试。");
  }
  if (response.status === 204) return undefined as unknown as T;
  return (await response.json()) as T;
}

export async function listKnowledgeDocuments(params: {
  page?: number;
  pageSize?: number;
  docType?: string;
  status?: string;
  search?: string;
}): Promise<KnowledgeDocumentListResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("pageSize", String(params.pageSize));
  if (params.docType) qs.set("docType", params.docType);
  if (params.status) qs.set("status", params.status);
  if (params.search) qs.set("search", params.search);
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents?${qs}`, { method: "GET" });
}

export async function getKnowledgeDocument(id: string): Promise<KnowledgeDocumentDetail> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents/${id}`, { method: "GET" });
}

export async function createKnowledgeDocument(payload: KnowledgeDocumentCreatePayload): Promise<KnowledgeDocumentItem> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadKnowledgeDocument(
  file: File,
  options: { title?: string; docType?: string; moduleTags?: string }
): Promise<KnowledgeDocumentItem> {
  const formData = new FormData();
  formData.append("file", file);
  const qs = new URLSearchParams();
  if (options.title) qs.set("title", options.title);
  if (options.docType) qs.set("docType", options.docType);
  if (options.moduleTags) qs.set("moduleTags", options.moduleTags);
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents/upload?${qs}`, {
    method: "POST",
    body: formData,
  });
}

export async function updateKnowledgeDocument(
  id: string,
  payload: KnowledgeDocumentUpdatePayload
): Promise<KnowledgeDocumentItem> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteKnowledgeDocument(id: string): Promise<void> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents/${id}`, { method: "DELETE" });
}

export async function reindexKnowledgeDocument(id: string): Promise<KnowledgeDocumentItem> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/documents/${id}/reindex`, { method: "POST" });
}

export async function searchKnowledge(params: {
  query: string;
  docTypes?: string[];
  moduleTags?: string[];
  topK?: number;
}): Promise<{ results: KnowledgeSearchResultItem[] }> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getKnowledgeStats(): Promise<KnowledgeStatsResponse> {
  return jsonRequest(`${API_BASE_URL}/api/v1/knowledge/stats`, { method: "GET" });
}

export async function downloadGenerationExport(
  generationId: string,
  format: ExportFormat
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/generations/${generationId}/export?format=${format}`
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "导出失败，请稍后重试。");
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  // Prefer filename*=UTF-8'' (RFC 5987, carries UTF-8 encoded filename)
  const starMatch = disposition.match(/filename\*=UTF-8''([^;]+)/);
  let filename: string;
  if (starMatch) {
    filename = decodeURIComponent(starMatch[1]);
  } else {
    const plainMatch = disposition.match(/filename="([^"]+)"/);
    filename = plainMatch?.[1] ?? `testcases.${format}`;
  }

  return {
    blob: await response.blob(),
    filename,
  };
}

export interface AppendedCase {
  title: string;
  category: string;
  priority: string;
  module: string;
  missing_reason: string;
  preconditions: string[];
  steps: string[];
  expectedResult: string;
}

export interface AppendGenerateResult {
  appendedCases: AppendedCase[];
  totalCount: number;
  modelName: string;
  generatedAt: string;
  summary: string;
}

export async function appendGenerateCases(
  existingCases: string,
  requirementText: string,
  modelKey?: string,
): Promise<AppendGenerateResult> {
  return jsonRequest(`${API_BASE_URL}/api/v1/generate/append`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      existingCases,
      requirementText,
      modelKey,
    }),
  });
}
