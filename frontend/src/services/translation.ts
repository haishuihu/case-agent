import { apiFetchPath } from "./api";

// ---- Types ----

export interface TranslationResponse {
  id: string;
  originalRequirementText: string;
  translatedContent: string;
  reviewedContent?: string | null;
  status: string;
  modelName: string;
  createdAt: string;
  updatedAt?: string | null;
}

export interface TranslationListItem {
  id: string;
  requirementPreview: string;
  status: string;
  modelName: string;
  createdAt: string;
}

export interface TranslationListResponse {
  items: TranslationListItem[];
  total: number;
  page: number;
  pageSize: number;
}

// ---- Helpers ----

async function jsonRequest<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "请求失败，请稍后重试。");
  }
  if (response.status === 204) return undefined as unknown as T;
  return (await response.json()) as T;
}

// ---- API Functions ----

export async function createTranslation(params: {
  requirementText: string;
  modelKey?: string;
  documentFiles?: File[];
  imageFiles?: File[];
}): Promise<TranslationResponse> {
  const formData = new FormData();
  formData.append("requirementText", params.requirementText);
  if (params.modelKey) formData.append("modelKey", params.modelKey);
  if (params.documentFiles) {
    for (const f of params.documentFiles) formData.append("documentFiles", f);
  }
  if (params.imageFiles) {
    for (const f of params.imageFiles) formData.append("imageFiles", f);
  }

  const response = await fetch(apiFetchPath("/api/v1/translations"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "翻译请求失败，请稍后重试。");
  }

  return (await response.json()) as TranslationResponse;
}

export async function listTranslations(params: {
  page?: number;
  pageSize?: number;
}): Promise<TranslationListResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("pageSize", String(params.pageSize));
  return jsonRequest<TranslationListResponse>(
    apiFetchPath(`/api/v1/translations?${qs}`),
    { method: "GET" }
  );
}

export async function getTranslation(id: string): Promise<TranslationResponse> {
  return jsonRequest<TranslationResponse>(
    apiFetchPath(`/api/v1/translations/${id}`),
    { method: "GET" }
  );
}

export async function updateTranslation(
  id: string,
  data: { reviewedContent: string; status: string }
): Promise<TranslationResponse> {
  return jsonRequest<TranslationResponse>(
    apiFetchPath(`/api/v1/translations/${id}`),
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
}

export async function deleteTranslation(id: string): Promise<{ ok: boolean }> {
  return jsonRequest<{ ok: boolean }>(
    apiFetchPath(`/api/v1/translations/${id}`),
    { method: "DELETE" }
  );
}
