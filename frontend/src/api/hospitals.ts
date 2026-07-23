import type { HospitalCandidate } from "../types/hospital";
import { requestJson } from "./client";
import { isHospitalCandidateArray } from "./validation";

export function getNearbyHospitals(
  incidentId: string,
  radiusKm = 10,
  signal?: AbortSignal,
): Promise<HospitalCandidate[]> {
  return requestJson<HospitalCandidate[]>("/api/v1/hospitals/nearby-candidates", {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, radius_km: radiusKm }),
    signal,
    validate: isHospitalCandidateArray,
  });
}
