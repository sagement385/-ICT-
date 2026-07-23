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
    this.name = "ApiError";
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

export type RuntimeValidator<T> = (value: unknown) => value is T;

export type RequestOptions<T> = RequestInit & {
  timeoutMs?: number;
  validate?: RuntimeValidator<T>;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export async function requestJson<T>(path: string, options: RequestOptions<T> = {}): Promise<T> {
  const { timeoutMs = 15_000, validate, ...init } = options;
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const abortFromCaller = (): void => controller.abort();
  init.signal?.addEventListener("abort", abortFromCaller, { once: true });
  const headers = new Headers(init.headers);
  const requestId = headers.get("X-Request-ID") ?? crypto.randomUUID();
  headers.set("X-Request-ID", requestId);
  if (init.body !== undefined && init.body !== null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (timedOut) {
      throw new ApiError(
        "BACKEND_API_TIMEOUT",
        "백엔드 응답 제한 시간을 초과했습니다.",
        { path, timeout_ms: timeoutMs },
        requestId,
      );
    }
    if (controller.signal.aborted) {
      throw new ApiError("BACKEND_REQUEST_CANCELLED", "요청이 취소되었습니다.", { path }, requestId);
    }
    throw new ApiError(
      "BACKEND_API_UNREACHABLE",
      "백엔드 API에 연결할 수 없습니다. 백엔드 실행 상태를 확인해주세요.",
      { path },
      requestId,
    );
  } finally {
    window.clearTimeout(timeoutId);
    init.signal?.removeEventListener("abort", abortFromCaller);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch (error) {
    throw new ApiError(
      "API_INVALID_RESPONSE",
      "백엔드가 JSON 응답을 반환하지 않았습니다.",
      { path },
      response.headers.get("X-Request-ID") ?? requestId,
      response.status,
    );
  }
  const responseRequestId = response.headers.get("X-Request-ID") ?? requestId;
  if (!response.ok) {
    const envelope = isErrorEnvelope(body) ? body.error : null;
    throw new ApiError(
      envelope?.code ?? "API_ERROR",
      envelope?.message ?? "API 요청 처리 중 오류가 발생했습니다.",
      envelope?.details ?? {},
      envelope?.request_id ?? responseRequestId,
      response.status,
    );
  }
  if (validate && !validate(body)) {
    throw new ApiError(
      "API_RESPONSE_SCHEMA_INVALID",
      "백엔드 응답 구조가 프론트엔드 계약과 일치하지 않습니다.",
      { path },
      responseRequestId,
      response.status,
    );
  }
  return body as T;
}

function isErrorEnvelope(value: unknown): value is {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
} {
  if (!value || typeof value !== "object" || !("error" in value)) return false;
  const error = (value as { error?: unknown }).error;
  return Boolean(
    error
    && typeof error === "object"
    && typeof (error as { code?: unknown }).code === "string"
    && typeof (error as { message?: unknown }).message === "string",
  );
}
