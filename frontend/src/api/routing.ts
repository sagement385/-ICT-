import { requestJson } from "./client";

export type RoutingStatus = {
  provider: string;
  configured: boolean;
  calls_used: number;
  calls_limit: number | null;
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
};

export type RouteBatchResult = {
  routes: HospitalRoute[];
  errors: Array<{ hospital_id: string; code: string; message: string }>;
};

export function getRoutingStatus(): Promise<RoutingStatus> {
  return requestJson<RoutingStatus>("/api/v1/routing/status");
}

export function testRoute(query: RouteQuery): Promise<RouteSnapshot> {
  return requestJson<RouteSnapshot>("/api/v1/routing/test", {
    method: "POST",
    body: JSON.stringify(query),
  });
}

export function getHospitalRoutes(
  incidentId: string,
  origin: Pick<RouteQuery, "origin_latitude" | "origin_longitude">,
  destinations: RouteDestination[],
): Promise<RouteBatchResult> {
  return requestJson<RouteBatchResult>("/api/v1/routing/batch", {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, ...origin, destinations }),
  });
}
