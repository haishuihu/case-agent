import { apiFetchPath } from "./api";

// ========== Types ==========

export interface TestSuite {
  id: string;
  name: string;
  description?: string;
  projectId?: string;
  createdBy?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
  caseCount: number;
  planCount: number;
}

export interface TestSuiteCreate {
  name: string;
  description?: string;
  projectId?: string;
}

export interface TestSuiteUpdate {
  name?: string;
  description?: string;
  projectId?: string;
  isActive?: boolean;
}

export interface TestCase {
  id: string;
  suiteId: string;
  title: string;
  description?: string;
  caseType: "api" | "ui" | "unit" | "integration";
  status: "draft" | "active" | "deprecated" | "archived";
  priority: number;
  method?: string;
  endpoint?: string;
  headers?: Record<string, string>;
  requestBody?: Record<string, unknown>;
  expectedStatus?: number;
  expectedResponse?: Record<string, unknown>;
  validationRules?: Record<string, unknown>;
  uiSelector?: string;
  uiAction?: string;
  uiExpected?: string;
  testData?: Record<string, unknown>;
  extraMetadata?: Record<string, unknown>;
  tags?: string[];
  currentVersion: number;
  createdAt: string;
  updatedAt?: string;
}

export interface TestCaseCreate {
  suiteId: string;
  title: string;
  description?: string;
  caseType?: "api" | "ui" | "unit" | "integration";
  priority?: number;
  tags?: string[];
  method?: string;
  endpoint?: string;
  headers?: Record<string, string>;
  requestBody?: Record<string, unknown>;
  expectedStatus?: number;
  expectedResponse?: Record<string, unknown>;
  validationRules?: Record<string, unknown>;
}

export interface TestCaseUpdate {
  title?: string;
  description?: string;
  caseType?: string;
  priority?: number;
  tags?: string[];
  method?: string;
  endpoint?: string;
  headers?: Record<string, string>;
  requestBody?: Record<string, unknown>;
  expectedStatus?: number;
  expectedResponse?: Record<string, unknown>;
  validationRules?: Record<string, unknown>;
  status?: string;
}

export interface TestCaseTag {
  id: string;
  name: string;
  color: string;
  description?: string;
  createdAt: string;
}

export interface TestPlan {
  id: string;
  suiteId: string;
  name: string;
  description?: string;
  scheduleType: "manual" | "cron" | "event";
  scheduleConfig?: Record<string, unknown>;
  autoExecute: boolean;
  notificationConfig?: Record<string, unknown>;
  caseFilter?: Record<string, unknown>;
  executionConfig?: Record<string, unknown>;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
  executionCount: number;
  lastExecutionAt?: string;
  lastExecutionStatus?: string;
}

export interface TestPlanCreate {
  suiteId: string;
  name: string;
  description?: string;
  scheduleType?: "manual" | "cron" | "event";
  scheduleConfig?: Record<string, unknown>;
  autoExecute?: boolean;
}

export interface TestExecution {
  id: string;
  planId?: string;
  suiteId?: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  totalCases: number;
  passedCount: number;
  failedCount: number;
  blockedCount: number;
  skippedCount: number;
  passRate: number;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  triggeredBy?: string;
  triggerSource?: string;
  aiSummary?: string;
  aiRecommendations?: string[];
  createdAt: string;
}

export interface ExecutionCreateRequest {
  suiteId?: string;
  planId?: string;
  caseIds?: string[];
  name?: string;
  context?: Record<string, unknown>;
  triggeredBy?: string;
  triggerSource?: string;
}

export interface TestResult {
  id: string;
  executionId: string;
  caseId: string;
  result: "pass" | "fail" | "blocked" | "skipped" | "pending";
  requestData?: Record<string, unknown>;
  responseData?: Record<string, unknown>;
  responseStatus?: number;
  validationDetails?: Record<string, unknown>;
  errorMessage?: string;
  stackTrace?: string;
  durationMs?: number;
  retryCount: number;
  aiAnalysis?: string;
  likelyRootCause?: string;
  caseTitle?: string;
  caseType?: string;
  createdAt: string;
}

export interface DashboardStats {
  pendingCount: number;
  runningCount: number;
  todayPassCount: number;
  todayFailCount: number;
  todayTotalCases: number;
  todayPassRate: number;
  totalSuites: number;
  totalCases: number;
  totalPlans: number;
  totalExecutions: number;
}

export interface RecentExecution {
  id: string;
  name: string;
  status: string;
  totalCases: number;
  passedCount: number;
  failedCount: number;
  passRate: number;
  triggeredBy?: string;
  createdAt: string;
  durationMs?: number;
}

export interface ExecutionTrend {
  date: string;
  total: number;
  passed: number;
  failed: number;
  passRate: number;
}

export interface RegressionRecommendItem {
  caseId: string;
  caseTitle: string;
  priority: number;
  score: number;
  reason: string;
  aiReasoning?: string;
  estimatedDurationMs?: number;
}

export interface RegressionRecommendResponse {
  totalRecommended: number;
  totalEstimatedDurationMs: number;
  recommendations: RegressionRecommendItem[];
  summary: string;
}

// ========== API Functions ==========

async function jsonRequest<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? `请求失败（${response.status}）`);
  }
  return (await response.json()) as T;
}

function fmtPath(p: string) {
  const path = p.startsWith("/") ? p : `/${p}`;
  return apiFetchPath(path);
}

// ---- Dashboard ----

export async function getDashboardStats(): Promise<DashboardStats> {
  return jsonRequest<DashboardStats>(fmtPath("/api/v1/auto-test/dashboard/stats"), {
    method: "GET",
  });
}

export async function getRecentExecutions(limit = 10): Promise<RecentExecution[]> {
  return jsonRequest<RecentExecution[]>(fmtPath(`/api/v1/auto-test/dashboard/recent?limit=${limit}`), {
    method: "GET",
  });
}

export async function getExecutionTrends(days = 7): Promise<ExecutionTrend[]> {
  return jsonRequest<ExecutionTrend[]>(fmtPath(`/api/v1/auto-test/dashboard/trends?days=${days}`), {
    method: "GET",
  });
}

// ---- TestSuite ----

export async function listSuites(params?: {
  projectId?: string;
  isActive?: boolean;
}): Promise<TestSuite[]> {
  const searchParams = new URLSearchParams();
  if (params?.projectId) searchParams.set("project_id", params.projectId);
  if (params?.isActive !== undefined) searchParams.set("is_active", String(params.isActive));
  const query = searchParams.toString();
  return jsonRequest<TestSuite[]>(
    fmtPath(`/api/v1/auto-test/suites${query ? `?${query}` : ""}`),
    { method: "GET" }
  );
}

export async function createSuite(data: TestSuiteCreate): Promise<TestSuite> {
  return jsonRequest<TestSuite>(fmtPath("/api/v1/auto-test/suites"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getSuite(id: string): Promise<TestSuite> {
  return jsonRequest<TestSuite>(fmtPath(`/api/v1/auto-test/suites/${id}`), {
    method: "GET",
  });
}

export async function updateSuite(id: string, data: TestSuiteUpdate): Promise<TestSuite> {
  return jsonRequest<TestSuite>(fmtPath(`/api/v1/auto-test/suites/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteSuite(id: string): Promise<void> {
  await fetch(fmtPath(`/api/v1/auto-test/suites/${id}`), { method: "DELETE" });
}

// ---- TestCase ----

export async function listCases(params?: {
  suiteId?: string;
  caseType?: string;
  status?: string;
  priority?: number;
  search?: string;
}): Promise<TestCase[]> {
  const searchParams = new URLSearchParams();
  if (params?.suiteId) searchParams.set("suite_id", params.suiteId);
  if (params?.caseType) searchParams.set("case_type", params.caseType);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.priority) searchParams.set("priority", String(params.priority));
  if (params?.search) searchParams.set("search", params.search);
  const query = searchParams.toString();
  return jsonRequest<TestCase[]>(
    fmtPath(`/api/v1/auto-test/cases${query ? `?${query}` : ""}`),
    { method: "GET" }
  );
}

export async function createCase(data: TestCaseCreate): Promise<TestCase> {
  return jsonRequest<TestCase>(fmtPath("/api/v1/auto-test/cases"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getCase(id: string): Promise<TestCase> {
  return jsonRequest<TestCase>(fmtPath(`/api/v1/auto-test/cases/${id}`), {
    method: "GET",
  });
}

export async function updateCase(id: string, data: TestCaseUpdate): Promise<TestCase> {
  return jsonRequest<TestCase>(fmtPath(`/api/v1/auto-test/cases/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteCase(id: string): Promise<void> {
  await fetch(fmtPath(`/api/v1/auto-test/cases/${id}`), { method: "DELETE" });
}

// ---- Tags ----

export async function listTags(): Promise<TestCaseTag[]> {
  return jsonRequest<TestCaseTag[]>(fmtPath("/api/v1/auto-test/tags"), {
    method: "GET",
  });
}

export async function createTag(data: { name: string; color?: string }): Promise<TestCaseTag> {
  return jsonRequest<TestCaseTag>(fmtPath("/api/v1/auto-test/tags"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ---- TestPlan ----

export async function listPlans(params?: { suiteId?: string; isActive?: boolean }): Promise<TestPlan[]> {
  const searchParams = new URLSearchParams();
  if (params?.suiteId) searchParams.set("suite_id", params.suiteId);
  if (params?.isActive !== undefined) searchParams.set("is_active", String(params.isActive));
  const query = searchParams.toString();
  return jsonRequest<TestPlan[]>(
    fmtPath(`/api/v1/auto-test/plans${query ? `?${query}` : ""}`),
    { method: "GET" }
  );
}

export async function createPlan(data: TestPlanCreate): Promise<TestPlan> {
  return jsonRequest<TestPlan>(fmtPath("/api/v1/auto-test/plans"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ---- Execution ----

export async function listExecutions(params?: {
  planId?: string;
  status?: string;
}): Promise<TestExecution[]> {
  const searchParams = new URLSearchParams();
  if (params?.planId) searchParams.set("plan_id", params.planId);
  if (params?.status) searchParams.set("status", params.status);
  const query = searchParams.toString();
  return jsonRequest<TestExecution[]>(
    fmtPath(`/api/v1/auto-test/executions${query ? `?${query}` : ""}`),
    { method: "GET" }
  );
}

export async function createExecution(data: ExecutionCreateRequest): Promise<TestExecution> {
  return jsonRequest<TestExecution>(fmtPath("/api/v1/auto-test/executions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getExecution(id: string): Promise<TestExecution & { results: TestResult[] }> {
  return jsonRequest(fmtPath(`/api/v1/auto-test/executions/${id}`), {
    method: "GET",
  });
}

export async function startExecution(id: string): Promise<TestExecution> {
  return jsonRequest<TestExecution>(fmtPath(`/api/v1/auto-test/executions/${id}/start`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

// ---- Regression Recommend ----

export async function getRegressionRecommend(params: {
  changedFiles?: string[];
  diffContent?: string;
  moduleNames?: string[];
  maxCases?: number;
}): Promise<RegressionRecommendResponse> {
  return jsonRequest<RegressionRecommendResponse>(fmtPath("/api/v1/auto-test/recommend"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

// ---- TestPlan (extended) ----

export async function getPlan(id: string): Promise<TestPlan> {
  return jsonRequest<TestPlan>(fmtPath(`/api/v1/auto-test/plans/${id}`), { method: "GET" });
}

export async function updatePlan(id: string, data: Partial<TestPlan>): Promise<TestPlan> {
  return jsonRequest<TestPlan>(fmtPath(`/api/v1/auto-test/plans/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deletePlan(id: string): Promise<void> {
  await fetch(fmtPath(`/api/v1/auto-test/plans/${id}`), { method: "DELETE" });
}

// ---- Triggers ----

export async function listTriggers(planId: string): Promise<TriggerConfig[]> {
  return jsonRequest<TriggerConfig[]>(fmtPath(`/api/v1/auto-test/plans/${planId}/triggers`), {
    method: "GET",
  });
}

export async function createTrigger(planId: string, data: TriggerConfigCreate): Promise<TriggerConfig> {
  return jsonRequest<TriggerConfig>(fmtPath(`/api/v1/auto-test/plans/${planId}/triggers`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateTrigger(id: string, data: TriggerConfigUpdate): Promise<TriggerConfig> {
  return jsonRequest<TriggerConfig>(fmtPath(`/api/v1/auto-test/triggers/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteTrigger(id: string): Promise<void> {
  await fetch(fmtPath(`/api/v1/auto-test/triggers/${id}`), { method: "DELETE" });
}

export async function retryFailedCases(executionId: string): Promise<TestExecution> {
  return jsonRequest<TestExecution>(fmtPath(`/api/v1/auto-test/executions/${executionId}/retry-failed`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export async function cloneCase(id: string, suffix?: string): Promise<TestCase> {
  const query = suffix ? `?suffix=${encodeURIComponent(suffix)}` : "";
  return jsonRequest<TestCase>(fmtPath(`/api/v1/auto-test/cases/${id}/clone${query}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export async function restoreCaseVersion(caseId: string, versionId: string): Promise<TestCase> {
  return jsonRequest<TestCase>(
    fmtPath(`/api/v1/auto-test/cases/${caseId}/versions/${versionId}/restore`),
    { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
  );
}

export async function listCaseVersions(caseId: string): Promise<CaseVersion[]> {
  return jsonRequest<CaseVersion[]>(fmtPath(`/api/v1/auto-test/cases/${caseId}/versions`), {
    method: "GET",
  });
}

export async function getFailureDistribution(limit = 10): Promise<FailureDistribution[]> {
  return jsonRequest<FailureDistribution[]>(
    fmtPath(`/api/v1/auto-test/dashboard/failures?limit=${limit}`),
    { method: "GET" }
  );
}

export async function getExecutionReport(executionId: string): Promise<string> {
  const resp = await fetch(fmtPath(`/api/v1/auto-test/executions/${executionId}/report`));
  return resp.text();
}

export async function convertCasesFromGeneration(
  generationId: string,
  suiteId: string,
  caseIds?: string[],
  baseUrl?: string,
): Promise<TestCase[]> {
  const params = new URLSearchParams({ generation_id: generationId, suite_id: suiteId });
  if (caseIds && caseIds.length > 0) params.set("case_ids", caseIds.join(","));
  if (baseUrl) params.set("base_url", baseUrl);
  return jsonRequest<TestCase[]>(fmtPath(`/api/v1/auto-test/cases/convert-from-generation?${params}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

// ---- Environments ----

export async function listEnvironments(): Promise<Environment[]> {
  return jsonRequest<Environment[]>(fmtPath("/api/v1/auto-test/environments"), { method: "GET" });
}

export async function createEnvironment(data: EnvironmentCreate): Promise<Environment> {
  return jsonRequest<Environment>(fmtPath("/api/v1/auto-test/environments"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteEnvironment(id: string): Promise<void> {
  await fetch(fmtPath(`/api/v1/auto-test/environments/${id}`), { method: "DELETE" });
}

// ---- Additional Types ----

export interface TriggerConfig {
  id: string;
  planId: string;
  triggerType: string;
  name?: string;
  config?: Record<string, unknown>;
  enabled: boolean;
  lastTriggeredAt?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface TriggerConfigCreate {
  triggerType: string;
  name?: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface TriggerConfigUpdate {
  name?: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface CaseVersion {
  id: string;
  caseId: string;
  version: number;
  content?: Record<string, unknown>;
  changeSummary?: string;
  changedBy?: string;
  createdAt: string;
}

export interface FailureDistribution {
  module: string;
  count: number;
  percentage: number;
}

export interface Environment {
  id: string;
  name: string;
  baseUrl?: string;
  description?: string;
  variables?: Record<string, string>;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface EnvironmentCreate {
  name: string;
  baseUrl?: string;
  description?: string;
  variables?: Record<string, string>;
}
