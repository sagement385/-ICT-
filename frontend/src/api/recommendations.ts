import type { RecommendationResult } from "../types/recommendation";
import { requestJson } from "./client";

export function getLatestRecommendation(incidentId: string): Promise<RecommendationResult> {
  return requestJson<RecommendationResult>(`/api/v1/recommendations/${encodeURIComponent(incidentId)}/latest`);
}

export function runRecommendation(incidentId: string, limit = 3): Promise<RecommendationResult> {
  return requestJson<RecommendationResult>(`/api/v1/recommendations/${encodeURIComponent(incidentId)}/run`, {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, limit }),
  });
}

