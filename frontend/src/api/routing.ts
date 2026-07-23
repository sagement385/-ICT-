import { requestJson } from "./client";

export type RoutingStatus = {
  provider: string;
  configured: boolean;
  calls_used: number;
  calls_limit: number | null;
  cache_max_age_seconds: number | null;
  max_concurrency: number;
  status: string;
};

export type RouteQuery = {
  origin_latitude: number;
  origin_longitude: number;
  destination_latitude: number;
  destination_longitude: number;
};

export type RouteSnapshot = {
  provider_name: string;
  distance_meters: number;
  duration_seconds: number;
  traffic_summary: string | null;
  fetched_at: string;
  path: Array<[number, number]> | null;
  source_name: string;
  source_record_id: string | null;
  raw_payload_id: string | null;
  schema_version: string;
  source_metadata: Record<string, unknown>;
};

export type RouteDestination = {
  hospital_id: string;
  latitude: number;
  longitude: number;
};

export type HospitalRoute = {
  hospital_id: string;
  route: RouteSnapshot;
  cache_status: "hit" | "miss";
};

export type RouteBatchResult = {
  routes: HospitalRoute[];
  errors: Array<{ hospital_id: string; code: string; message: string }>;
  generated_at: string;
};

export function getRoutingStatus(signal?: AbortSignal): Promise<RoutingStatus> {
  return requestJson<RoutingStatus>("/api/v1/routing/status", { signal });
}

export function testRoute(query: RouteQuery): Promise<RouteSnapshot> {
  return requestJson<RouteSnapshot>("/api/v1/routing/test", {
    method: "POST",
    body: JSON.stringify(query),
  });
}

export function getHospitalRoutes(
  incidentId: string,
  hospitalIds: string[],
  signal?: AbortSignal,
): Promise<RouteBatchResult> {
  return requestJson<RouteBatchResult>("/api/v1/routing/batch", {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, hospital_ids: hospitalIds }),
    signal,
    timeoutMs: 45_000,
  });
}
