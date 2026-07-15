import type { Hospital } from "../types/hospital";
import { requestJson } from "./client";

export function getNearbyHospitals(
  latitude: number,
  longitude: number,
  radiusKm = 10,
): Promise<Hospital[]> {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    radius_km: String(radiusKm),
  });
  return requestJson<Hospital[]>(`/api/v1/hospitals?${params.toString()}`);
}
