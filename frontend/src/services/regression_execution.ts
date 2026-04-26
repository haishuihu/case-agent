import { apiFetchPath, jsonRequest } from "./api";

export type ExecutionStatus = "not_started" | "in_progress" | "passed" | "failed" | "blocked";

export interface ExecutionUpdateRequest {
  status: ExecutionStatus;
  executedBy?: string;
  actualResult?: string;
  comment?: string;
}

export interface ExecutionUpdateResponse {
  id: string;
  recommendationId: string;
  status: ExecutionStatus;
  executedBy: string | null;
  executedAt: string | null;
  actualResult: string | null;
  comment: string | null;
}

export async function updateExecutionStatus(
  recommendationId: string,
  payload: ExecutionUpdateRequest
): Promise<ExecutionUpdateResponse> {
  return jsonRequest(
    apiFetchPath(`/api/v1/regression/recommendations/${encodeURIComponent(recommendationId)}/execute`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function getExecutionStatus(
  recommendationId: string
): Promise<ExecutionUpdateResponse> {
  return jsonRequest(
    apiFetchPath(`/api/v1/regression/recommendations/${encodeURIComponent(recommendationId)}/execute`),
    { method: "GET" }
  );
}
