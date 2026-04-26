// ============================================================
// Defect API Service
// Sprint 5: 用例执行与缺陷联动
// ============================================================

import { apiFetchPath, jsonRequest } from "./api";

// ---- Types ----

export type DefectSeverity = "critical" | "high" | "medium" | "low";
export type DefectPriority = "high" | "medium" | "low";
export type DefectStatus = "open" | "in_progress" | "resolved" | "closed";

export interface Defect {
  id: string;
  submissionId?: string | null;
  recommendationId?: string | null;
  executionId?: string | null;
  title: string;
  description?: string | null;
  severity: DefectSeverity;
  priority: DefectPriority;
  status: DefectStatus;
  environment?: string | null;
  browser?: string | null;
  rootCause?: string | null;
  attachments: string[];
  creator?: string | null;
  assignee?: string | null;
  createdAt: string;
  updatedAt?: string | null;
  resolvedAt?: string | null;
}

export interface CreateDefectPayload {
  submissionId?: string;
  recommendationId?: string;
  executionId?: string;
  title: string;
  description?: string;
  severity?: DefectSeverity;
  priority?: DefectPriority;
  environment?: string;
  browser?: string;
  rootCause?: string;
  attachments?: string[];
  creator?: string;
  assignee?: string;
}

export interface CreateDefectFromExecutionPayload {
  executionId: string;
  title?: string;
  description?: string;
  severity?: DefectSeverity;
  priority?: DefectPriority;
  creator?: string;
}

export interface DefectListResponse {
  items: Defect[];
  total: number;
  page: number;
  pageSize: number;
}

// ---- API Functions ----

export async function createDefect(payload: CreateDefectPayload): Promise<Defect> {
  return jsonRequest(apiFetchPath("/api/v1/defects"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function createDefectFromExecution(
  payload: CreateDefectFromExecutionPayload
): Promise<Defect> {
  return jsonRequest(apiFetchPath("/api/v1/defects/from-execution"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listDefects(params?: {
  page?: number;
  pageSize?: number;
  submissionId?: string;
  status?: DefectStatus;
  severity?: DefectSeverity;
}): Promise<DefectListResponse> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.pageSize) sp.set("pageSize", String(params.pageSize));
  if (params?.submissionId) sp.set("submissionId", params.submissionId);
  if (params?.status) sp.set("status", params.status);
  if (params?.severity) sp.set("severity", params.severity);
  const query = sp.toString();
  return jsonRequest(apiFetchPath(`/api/v1/defects${query ? `?${query}` : ""}`), {
    method: "GET",
  });
}

export async function getDefect(id: string): Promise<Defect> {
  return jsonRequest(apiFetchPath(`/api/v1/defects/${id}`), {
    method: "GET",
  });
}

export async function updateDefect(
  id: string,
  payload: Partial<Omit<CreateDefectPayload, "submissionId" | "recommendationId" | "executionId">>
): Promise<Defect> {
  return jsonRequest(apiFetchPath(`/api/v1/defects/${id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteDefect(id: string): Promise<void> {
  return jsonRequest(apiFetchPath(`/api/v1/defects/${id}`), {
    method: "DELETE",
  });
}
