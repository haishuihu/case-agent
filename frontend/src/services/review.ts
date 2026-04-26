import { jsonRequest } from "./api";

const BASE = "/api/v1/reviews";

export interface AIReviewDimension {
  dimension: string;
  label: string;
  score: number;
  description: string;
}

export interface AIReviewIssue {
  type: string;
  severity: "high" | "medium" | "low";
  description: string;
  recommendation?: string;
}

export interface AIReviewResult {
  overallScore: number;
  dimensions: AIReviewDimension[];
  issues: AIReviewIssue[];
  suggestions: string[];
}

export interface ReviewComment {
  id: string;
  reviewId: string;
  author?: string;
  content: string;
  caseId?: string;
  caseTitle?: string;
  parentCommentId?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface CaseReview {
  id: string;
  generationId?: string;
  caseTitle?: string;
  requirementText?: string;
  generatedCases?: string;
  reviewStatus: "pending" | "in_review" | "approved" | "needs_revision";
  completenessScore?: number;
  executabilityScore?: number;
  consistencyScore?: number;
  redundancyScore?: number;
  coverageScore?: number;
  overallScore?: number;
  aiReviewSummary?: string;
  aiReviewDetails?: AIReviewResult;
  reviewer?: string;
  reviewerComment?: string;
  decision?: "approved" | "needs_revision";
  createdAt: string;
  updatedAt?: string;
  comments: ReviewComment[];
}

export interface CaseReviewListResponse {
  items: CaseReview[];
  total: number;
  page: number;
  pageSize: number;
}

export async function createReview(payload: {
  generationId?: string;
  caseTitle?: string;
  requirementText?: string;
  generatedCases?: string;
  reviewer?: string;
}): Promise<CaseReview> {
  return jsonRequest(`${BASE}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function runAIReview(payload: {
  generationId?: string;
  caseTitle?: string;
  requirementText?: string;
  generatedCases?: string;
  modelKey?: string;
}): Promise<CaseReview> {
  return jsonRequest(`${BASE}/ai-review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listReviews(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
}): Promise<CaseReviewListResponse> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.pageSize) sp.set("pageSize", String(params.pageSize));
  if (params?.status) sp.set("status", params.status);
  const query = sp.toString();
  return jsonRequest(`${BASE}${query ? `?${query}` : ""}`, {
    method: "GET",
  });
}

export async function getReview(id: string): Promise<CaseReview> {
  return jsonRequest(`${BASE}/${id}`, {
    method: "GET",
  });
}

export async function updateReviewStatus(
  id: string,
  payload: {
    reviewStatus?: string;
    decision?: "approved" | "needs_revision";
    reviewer?: string;
    reviewerComment?: string;
  }
): Promise<CaseReview> {
  return jsonRequest(`${BASE}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteReview(id: string): Promise<void> {
  return jsonRequest(`${BASE}/${id}`, {
    method: "DELETE",
  });
}

export async function addComment(
  reviewId: string,
  payload: {
    author?: string;
    content: string;
    caseId?: string;
    caseTitle?: string;
    parentCommentId?: string;
  }
): Promise<ReviewComment> {
  return jsonRequest(`${BASE}/${reviewId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listComments(reviewId: string): Promise<ReviewComment[]> {
  return jsonRequest(`${BASE}/${reviewId}/comments`, {
    method: "GET",
  });
}

export async function deleteComment(reviewId: string, commentId: string): Promise<void> {
  return jsonRequest(`${BASE}/${reviewId}/comments/${commentId}`, {
    method: "DELETE",
  });
}
