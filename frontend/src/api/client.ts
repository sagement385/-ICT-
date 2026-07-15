export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;

  constructor(code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError("BACKEND_API_NOT_CONFIGURED", "백엔드 API 주소가 설정되지 않았습니다.");
  }
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = (await response.json()) as { error?: { code: string; message: string; details?: Record<string, unknown> } };
  if (!response.ok) {
    throw new ApiError(body.error?.code ?? "API_ERROR", body.error?.message ?? "API 오류", body.error?.details);
  }
  return body as T;
}

