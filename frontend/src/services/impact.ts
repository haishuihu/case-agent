// ============================================================
// Impact Analysis & Regression API Service
// Sprint 2: 变更影响分析与回归推荐
// ============================================================

import { apiFetchPath, jsonRequest } from "./api";

// ---- Types ----

export interface ChangedFile {
  filename: string;
  status: "added" | "modified" | "deleted";
  additions: number;
  deletions: number;
}

export interface ImpactedModule {
  id: string;
  moduleName: string;
  moduleType: "direct" | "indirect" | "api";
  riskLevel: "high" | "medium" | "low";
  impactDescription: string;
}

export interface RegressionRecommendation {
  id: string;
  caseId: string | null;
  caseTitle: string | null;
  priority: "must" | "should" | "could";
  riskLevel: "high" | "medium" | "low";
  reason: string | null;
  estimatedMinutes: number | null;
  category: string | null;
  executionStatus: "not_started" | "in_progress" | "passed" | "failed" | "blocked" | null;
}

export interface ImpactAnalysis {
  id: string;
  submissionId: string | null;
  changedFiles: ChangedFile[];
  addedLines: number;
  deletedLines: number;
  modifiedFunctions: string[];
  impactedModules: ImpactedModule[];
  indirectImpacts: string[];
  apiBreakingChanges: string[];
  riskPoints: string[];
  confidenceLevel: "high" | "medium" | "low";
  summary: string;
  recommendations: RegressionRecommendation[];
  estimatedTotalMinutes: number;
  createdAt: string;
}

export interface RegressionRecommendResponse {
  analysisId: string;
  mustRegress: RegressionRecommendation[];
  shouldRegress: RegressionRecommendation[];
  couldRegress: RegressionRecommendation[];
  totalMustMinutes: number;
  totalShouldMinutes: number;
  totalCouldMinutes: number;
}

export interface ModuleNode {
  id: string;
  name: string;
  moduleType: string;
  riskLevel: string;
  isDirect: boolean;
  changeFrequency: number;
  x?: number;
  y?: number;
}

export interface ModuleEdge {
  source: string;
  target: string;
  relationType: string;
  weight: number;
}

export interface VisualizationData {
  nodes: ModuleNode[];
  edges: ModuleEdge[];
  summary: string;
  maxDepth: number;
  totalNodes: number;
  totalEdges: number;
}

// ---- Request Payloads ----

export interface CreateImpactAnalysisPayload {
  gitDiff: string;
  affectedModules?: string[];
  submissionId?: string;
  recentDefects?: string[];
}

export interface GetRegressionRecommendPayload {
  analysisId?: string;
  submissionId?: string;
}

// ---- API Functions ----
export async function createImpactAnalysis(
  payload: CreateImpactAnalysisPayload
): Promise<ImpactAnalysis> {
  return jsonRequest(apiFetchPath("/api/v1/impact-analysis"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 获取指定 ID 的影响分析结果 */
export async function getImpactAnalysis(id: string): Promise<ImpactAnalysis> {
  return jsonRequest(apiFetchPath(`/api/v1/impact-analysis/${id}`), {
    method: "GET",
  });
}

/** 获取指定提测申请的最新一条影响分析 */
export async function getLatestImpactBySubmission(
  submissionId: string
): Promise<ImpactAnalysis> {
  return jsonRequest(
    apiFetchPath(`/api/v1/impact-analysis/submissions/${submissionId}`),
    { method: "GET" }
  );
}

/** 获取回归推荐（优先返回已有推荐结果，若无则重新生成） */
export async function getRegressionRecommend(
  payload: GetRegressionRecommendPayload
): Promise<RegressionRecommendResponse> {
  return jsonRequest(apiFetchPath("/api/v1/regression/recommend"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 直接获取指定分析的回归推荐结果 */
export async function getRecommendations(
  analysisId: string
): Promise<RegressionRecommendResponse> {
  return jsonRequest(
    apiFetchPath(`/api/v1/regression/recommendations/${analysisId}`),
    { method: "GET" }
  );
}

/** 获取影响分析的可视化数据（模块关系图） */
export async function getImpactVisualization(
  analysisId: string
): Promise<VisualizationData> {
  return jsonRequest(
    apiFetchPath(`/api/v1/impact-analysis/${analysisId}/visualization`),
    { method: "GET" }
  );
}
