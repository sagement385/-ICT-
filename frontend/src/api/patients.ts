import type { PatientEvent } from "../types/patient";
import { requestJson } from "./client";

export function getPatient(incidentId: string): Promise<PatientEvent> {
  return requestJson<PatientEvent>(`/api/v1/patients/${encodeURIComponent(incidentId)}`);
}

