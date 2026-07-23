import type { RecommendationResult } from "../types/recommendation";
import { requestJson } from "./client";
import { isRecommendationResult } from "./validation";

export function getLatestRecommendation(
  incidentId: string,
  signal?: AbortSignal,
): Promise<RecommendationResult> {
  return requestJson<RecommendationResult>(
    `/api/v1/recommendations/${encodeURIComponent(incidentId)}/latest`,
    { signal, validate: isRecommendationResult },
  );
}

export function runRecommendation(
  incidentId: string,
  limit = 3,
  signal?: AbortSignal,
): Promise<RecommendationResult> {
  return requestJson<RecommendationResult>(`/api/v1/recommendations/${encodeURIComponent(incidentId)}/run`, {
    method: "POST",
    body: JSON.stringify({ limit }),
    signal,
    timeoutMs: 60_000,
    validate: isRecommendationResult,
  });
}
