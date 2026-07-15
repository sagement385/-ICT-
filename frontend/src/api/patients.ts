import type { PatientEvent } from "../types/patient";
import { requestJson } from "./client";

export type CreatePatientEvent = Omit<PatientEvent, "created_at" | "updated_at">;

export type PatientAssistResult = {
  symptoms: Array<{ code: string; label: string; confidence: number | null }>;
  consciousness_status: string | null;
  breathing_status: string | null;
  bleeding_status: string | null;
  urgency_level: string | null;
  location_text: string | null;
  needs_human_review: boolean;
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

export function createPatient(event: CreatePatientEvent): Promise<PatientEvent> {
  return requestJson<PatientEvent>("/api/v1/patients", {
    method: "POST",
    body: JSON.stringify(event),
  });
}

export function geocodeAddress(address: string): Promise<GeocodedLocation> {
  return requestJson<GeocodedLocation>(`/api/v1/locations/geocode?address=${encodeURIComponent(address)}`);
}

export function getPatient(incidentId: string): Promise<PatientEvent> {
  return requestJson<PatientEvent>(`/api/v1/patients/${encodeURIComponent(incidentId)}`);
}

export function assistPatientText(text: string): Promise<PatientAssistResult> {
  return requestJson<PatientAssistResult>("/api/v1/patients/assist", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}
