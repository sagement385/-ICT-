import type { PatientEvent } from "../types/patient";
import { requestJson } from "./client";
import { isPatientEvent, isRecord } from "./validation";

export type CreatePatientEvent = Omit<PatientEvent, "created_at" | "updated_at">;

export type PatientAssistResult = {
  symptoms: Array<{ code: string; label: string; confidence: number | null }>;
  consciousness_status: string | null;
  breathing_status: string | null;
  bleeding_status: string | null;
  urgency_level: string | null;
  location_text: string | null;
  extracted_by_ai: boolean;
  needs_human_review: boolean;
  confidence: number | null;
  warnings: string[];
  source: { model_name: string; model_version: string };
};

export type GeocodedLocation = {
  address: string;
  latitude: number;
  longitude: number;
  source_name: string;
  fetched_at: string;
};

export function createPatient(event: CreatePatientEvent, signal?: AbortSignal): Promise<PatientEvent> {
  return requestJson<PatientEvent>("/api/v1/patients", {
    method: "POST",
    body: JSON.stringify(event),
    signal,
    validate: isPatientEvent,
  });
}

function isGeocodedLocation(value: unknown): value is GeocodedLocation {
  return isRecord(value)
    && typeof value.address === "string"
    && typeof value.latitude === "number"
    && typeof value.longitude === "number"
    && typeof value.source_name === "string"
    && typeof value.fetched_at === "string";
}

export function geocodeAddress(address: string, signal?: AbortSignal): Promise<GeocodedLocation> {
  return requestJson<GeocodedLocation>("/api/v1/locations/geocode", {
    method: "POST",
    body: JSON.stringify({ address }),
    signal,
    validate: isGeocodedLocation,
  });
}

export function getPatient(incidentId: string, signal?: AbortSignal): Promise<PatientEvent> {
  return requestJson<PatientEvent>(`/api/v1/patients/${encodeURIComponent(incidentId)}`, {
    signal,
    validate: isPatientEvent,
  });
}

export function assistPatientText(text: string, signal?: AbortSignal): Promise<PatientAssistResult> {
  return requestJson<PatientAssistResult>("/api/v1/patients/assist", {
    method: "POST",
    body: JSON.stringify({ text }),
    signal,
    timeoutMs: 30_000,
  });
}
