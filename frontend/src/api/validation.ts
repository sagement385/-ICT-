import type { RouteBatchResult } from "./routing";
import type { SystemStatus } from "./status";
import type { HospitalCandidate } from "../types/hospital";
import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

export function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

export function isPatientEvent(value: unknown): value is PatientEvent {
  return isRecord(value)
    && typeof value.incident_id === "string"
    && typeof value.observed_at === "string"
    && isRecord(value.location)
    && Array.isArray(value.symptoms)
    && isRecord(value.source);
}

export function isHospitalCandidateArray(value: unknown): value is HospitalCandidate[] {
  return Array.isArray(value) && value.every((item) => (
    isRecord(item)
    && typeof item.hospital_id === "string"
    && typeof item.hospital_name === "string"
    && isRecord(item.location)
    && Array.isArray(item.departments)
    && Array.isArray(item.equipment)
    && Array.isArray(item.capabilities)
    && "realtime_status" in item
  ));
}

export function isRouteBatchResult(value: unknown): value is RouteBatchResult {
  return isRecord(value)
    && Array.isArray(value.routes)
    && Array.isArray(value.errors)
    && typeof value.generated_at === "string";
}

export function isRecommendationResult(value: unknown): value is RecommendationResult {
  return isRecord(value)
    && typeof value.incident_id === "string"
    && typeof value.recommendation_run_id === "string"
    && Array.isArray(value.recommended_hospitals)
    && Array.isArray(value.warnings);
}

export function isSystemStatus(value: unknown): value is SystemStatus {
  return isRecord(value)
    && typeof value.generated_at === "string"
    && typeof value.mode === "string"
    && isRecord(value.services)
    && isRecord(value.data)
    && isRecord(value.readiness)
    && Array.isArray(value.warnings);
}
