export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  requestId: string | null;
  status: number | null;

  constructor(
    code: string,
    message: string,
    details: Record<string, unknown> = {},
    requestId: string | null = null,
    status: number | null = null,
  ) {
    super(message);
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.status = status;
  }
}

export function formatApiError(error: ApiError): string {
  const requestId = error.requestId ? ` (요청 ID: ${error.requestId})` : "";
  return `${error.code}: ${error.message}${requestId}`;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError("BACKEND_API_NOT_CONFIGURED", "백엔드 API 주소가 설정되지 않았습니다.");
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL.replace(/\/$/, "")}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch (error) {
    throw new ApiError(
      "BACKEND_API_UNREACHABLE",
      "백엔드 API에 연결할 수 없습니다. 백엔드 실행 상태와 VITE_API_BASE_URL을 확인해주세요.",
      { path },
    );
  }
  let body: {
    error?: {
      code: string;
      message: string;
      details?: Record<string, unknown>;
      request_id?: string;
    };
  };
  try {
    body = (await response.json()) as typeof body;
  } catch (error) {
    throw new ApiError("API_INVALID_RESPONSE", "백엔드가 JSON 응답을 반환하지 않았습니다.", { path });
  }
  if (!response.ok) {
    throw new ApiError(
      body.error?.code ?? "API_ERROR",
      body.error?.message ?? "API 오류",
      body.error?.details,
      body.error?.request_id ?? response.headers.get("X-Request-ID"),
      response.status,
    );
  }
  return body as T;
}
