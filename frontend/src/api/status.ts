import { requestJson } from "./client";
import { isRecord, isSystemStatus } from "./validation";

export type OperationalServiceStatus = {
  configured: boolean;
  status: string;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error: string | null;
};

export type SystemStatus = {
  generated_at: string;
  mode: string;
  environment: string;
  services: Record<string, OperationalServiceStatus>;
  data: {
    patients: number;
    hospitals: number;
    emergency_institutions: number;
    emergency_institutions_with_realtime: number;
    emergency_institutions_with_departments: number;
    emergency_institutions_with_equipment: number;
    emergency_institutions_with_capabilities: number;
    source_identities_verified: number;
    source_identities_unverified: number;
    route_snapshots: number;
    active_policies: number;
  };
  readiness: {
    chat_intake: boolean;
    voice_intake: boolean;
    hospital_candidates: boolean;
    live_routes: boolean;
    policy_recommendation: boolean;
  };
  warnings: string[];
};

export type DataSourceStatus = {
  source_name: string;
  dataset_id: string | null;
  provider_name: string;
  enabled: boolean;
  schema_version: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error: string | null;
  status: string;
  age_seconds: number | null;
  freshness_threshold_seconds: number | null;
  reason: string | null;
};

function isDataSourceStatuses(value: unknown): value is DataSourceStatus[] {
  return Array.isArray(value) && value.every((item) => (
    isRecord(item)
    && typeof item.source_name === "string"
    && typeof item.provider_name === "string"
    && typeof item.status === "string"
  ));
}

export function getSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  return requestJson<SystemStatus>("/api/v1/status", { signal, validate: isSystemStatus });
}

export function getDataSources(signal?: AbortSignal): Promise<DataSourceStatus[]> {
  return requestJson<DataSourceStatus[]>("/api/v1/data-sources", {
    signal,
    validate: isDataSourceStatuses,
  });
}
