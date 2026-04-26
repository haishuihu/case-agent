// ============================================================
// Submission API Service
// Sprint 1: 提测质量门禁
// ============================================================

import { apiFetchPath, jsonRequest } from "./api";

// ---- Types ----

export interface ChecklistItem {
  id: string;
  item: string;
  checkMethod: string;
  passCriteria: string;
  riskLevel: "high" | "medium" | "low";
  category: string;
  isChecked: boolean;
  checkResult?: string | null;
  checkedBy?: string | null;
  checkedAt?: string | null;
  isAiGenerated: boolean;
}

export interface Submission {
  id: string;
  version: string;
  submissionType: "feature" | "bugfix" | "urgent";
  requirementId?: string | null;
  requirementLink?: string | null;
  changeDescription: string;
  affectedModules: string[];
  changeType: "added" | "modified" | "deleted";
  selfTestPassed: boolean;
  selfTestCaseCount: number;
  selfTestCoverage?: number | null;
  selfTestConclusion?: string | null;
  smokeTestResult: string;
  blockingIssueCount: number;
  status:
    | "pending"
    | "self_test"
    | "self_test_passed"
    | "gate_passed"
    | "gate_rejected";
  gateResult?: GateResult | null;
  gateRejectReason?: string | null;
  gitDiff?: string | null;
  gitCommitHash?: string | null;
  branchName?: string | null;
  submitter?: string | null;
  reviewedBy?: string | null;
  createdAt: string;
  updatedAt?: string | null;
  checklists: ChecklistItem[];
}

export interface GateResult {
  summary: string;
  suggestions: string[];
  highRiskAreas: string[];
  generated_at?: string;
}

export interface CreateSubmissionPayload {
  version: string;
  submissionType?: "feature" | "bugfix" | "urgent";
  requirementId?: string;
  requirementLink?: string;
  changeDescription: string;
  affectedModules?: string[];
  changeType?: "added" | "modified" | "deleted";
  selfTestPassed?: boolean;
  selfTestCaseCount?: number;
  selfTestCoverage?: number;
  selfTestConclusion?: string;
  smokeTestResult?: string;
  blockingIssueCount?: number;
  gitDiff?: string;
  gitCommitHash?: string;
  branchName?: string;
  submitter?: string;
}

export interface UpdateSubmissionPayload {
  status?: string;
  selfTestPassed?: boolean;
  selfTestCaseCount?: number;
  selfTestCoverage?: number;
  selfTestConclusion?: string;
  smokeTestResult?: string;
  blockingIssueCount?: number;
  gateResult?: string;
  gateRejectReason?: string;
  reviewedBy?: string;
}

export interface GenerateChecklistPayload {
  submissionId: string;
  changeDescription: string;
  affectedModules?: string[];
  gitDiff?: string;
  recentDefects?: string[];
}

export interface GenerateChecklistItem {
  item: string;
  method: string;
  pass_criteria: string;
  risk_level: string;
  category: string;
}

export interface GenerateChecklistResponse {
  checklists: GenerateChecklistItem[];
  summary: string;
  suggestions: string[];
  highRiskAreas: string[];
}

export interface ChecklistCheckPayload {
  checklistId: string;
  isChecked: boolean;
  checkResult?: string;
  checkedBy?: string;
}

export interface ChecklistCheckResponse {
  ok: boolean;
  high_risk_all_checked: boolean;
  checklist_id: string;
  is_checked: boolean;
}

export interface ImpactResult {
  impacted_modules: string[];
  indirect_impacts: string[];
  data_flow_impacts: string[];
  api_breaking_changes: string[];
  risk_points: string[];
  confidence_level: "high" | "medium" | "low";
}

export interface SubmissionListResponse {
  items: Submission[];
  total: number;
  page: number;
  pageSize: number;
}

// ---- API Functions ----

export async function createSubmission(
  payload: CreateSubmissionPayload
): Promise<Submission> {
  return jsonRequest(apiFetchPath("/api/v1/submissions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listSubmissions(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
}): Promise<SubmissionListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.pageSize) qs.set("pageSize", String(params.pageSize));
  if (params?.status) qs.set("status", params.status);
  return jsonRequest(apiFetchPath(`/api/v1/submissions?${qs}`), {
    method: "GET",
  });
}

export async function getSubmission(id: string): Promise<Submission> {
  return jsonRequest(apiFetchPath(`/api/v1/submissions/${id}`), {
    method: "GET",
  });
}

export async function updateSubmission(
  id: string,
  payload: UpdateSubmissionPayload
): Promise<Submission> {
  return jsonRequest(apiFetchPath(`/api/v1/submissions/${id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteSubmission(id: string): Promise<void> {
  return jsonRequest(apiFetchPath(`/api/v1/submissions/${id}`), {
    method: "DELETE",
  });
}

export async function generateChecklist(
  payload: GenerateChecklistPayload
): Promise<GenerateChecklistResponse> {
  return jsonRequest(apiFetchPath("/api/v1/submissions/checklist/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getSubmissionChecklists(
  submissionId: string
): Promise<ChecklistItem[]> {
  return jsonRequest(
    apiFetchPath(`/api/v1/submissions/${submissionId}/checklist`),
    { method: "GET" }
  );
}

export async function checkChecklist(
  payload: ChecklistCheckPayload
): Promise<ChecklistCheckResponse> {
  return jsonRequest(
    apiFetchPath("/api/v1/submissions/checklist/check"),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function analyzeImpact(params: {
  gitDiff: string;
  affectedModules?: string;
}): Promise<ImpactResult> {
  const qs = new URLSearchParams();
  qs.set("git_diff", params.gitDiff);
  if (params.affectedModules) {
    qs.set("affected_modules", params.affectedModules);
  }
  return jsonRequest(
    apiFetchPath(`/api/v1/submissions/checklist/impact?${qs}`),
    { method: "POST" }
  );
}
