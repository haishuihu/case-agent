const API_BASE_URL = "";

function apiFetchPath(pathWithLeadingSlash: string): string {
  const p = pathWithLeadingSlash.startsWith("/")
    ? pathWithLeadingSlash
    : `/${pathWithLeadingSlash}`;
  return /^https?:\/\//i.test(API_BASE_URL)
    ? `${API_BASE_URL.replace(/\/$/, "")}${p}`
    : `${API_BASE_URL}${p}`;
}

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
  const response = await fetch(
    apiFetchPath(`/api/v1/regression/recommendations/${encodeURIComponent(recommendationId)}/execute`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  if (!response.ok) {
    const payload_ = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload_.detail ?? "更新执行状态失败，请稍后重试。");
  }
  return (await response.json()) as ExecutionUpdateResponse;
}

export async function getExecutionStatus(
  recommendationId: string
): Promise<ExecutionUpdateResponse> {
  const response = await fetch(
    apiFetchPath(`/api/v1/regression/recommendations/${encodeURIComponent(recommendationId)}/execute`)
  );
  if (!response.ok) {
    const payload_ = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload_.detail ?? "获取执行状态失败，请稍后重试。");
  }
  return (await response.json()) as ExecutionUpdateResponse;
}
