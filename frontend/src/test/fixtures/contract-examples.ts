import type { HospitalCandidate, HospitalSummary } from "../../types/hospital";
import type { PatientEvent } from "../../types/patient";
import type { RecommendationRequest, RecommendationResult } from "../../types/recommendation";
import type { HospitalRoute } from "../../api/routing";
import type { RoutingStatus } from "../../api/routing";
import type { DataSourceStatus, SystemStatus } from "../../api/status";

/** Compile-time TEST-only examples that detect TypeScript contract drift. */
export const patientEventExample = {
  incident_id: "TEST_PATIENT_001",
  observed_at: "2026-01-01T00:00:00Z",
  location: { latitude: null, longitude: null, address_text: "TEST_ADDRESS_REDACTED" },
  symptoms: [],
  consciousness_status: null,
  breathing_status: null,
  bleeding_status: null,
  urgency_level: null,
  source: { model_name: "TEST_MODEL", model_version: "TEST_VERSION" },
} satisfies PatientEvent;

export const hospitalSummaryExample = {
  hospital_id: "TEST_HOSPITAL_001",
  hospital_name: "TEST_HOSPITAL_NAME",
  hospital_type_code: null,
  location: { latitude: null, longitude: null, address: "TEST_ADDRESS_REDACTED" },
  phone: null,
  source_name: "TEST_SOURCE",
  source_record_id: "TEST_RECORD_001",
  raw_payload_id: "TEST_RAW_001",
  schema_version: "TEST_SCHEMA_V1",
  source_updated_at: null,
  freshness: { status: "unknown", observed_at: null, reason: "TEST_DATA" },
  emergency_profile: null,
} satisfies HospitalSummary;

export const hospitalCandidateExample = {
  ...hospitalSummaryExample,
  departments: [],
  equipment: [],
  capabilities: [],
  realtime_status: null,
} satisfies HospitalCandidate;

export const recommendationRequestExample = { limit: 3 } satisfies RecommendationRequest;

export const recommendationResultExample = {
  incident_id: "TEST_PATIENT_001",
  recommendation_run_id: "TEST_RUN_001",
  generated_at: "2026-01-01T00:00:00Z",
  policy: { policy_name: "TEST_POLICY", policy_version: "TEST_VERSION" },
  recommended_hospitals: [
    {
      rank: 1,
      hospital_id: "TEST_HOSPITAL_001",
      hospital_name: "TEST_HOSPITAL_NAME",
      location: { latitude: null, longitude: null, address: "TEST_ADDRESS_REDACTED" },
      total_score: 0,
      score_breakdown: {},
      travel_time: null,
      recommendation_reasons: [],
      data_freshness: {},
    },
  ],
  warnings: ["TEST_WARNING"],
} satisfies RecommendationResult;

export const hospitalRouteExample = {
  hospital_id: "TEST_HOSPITAL_001",
  cache_status: "miss",
  route: {
    provider_name: "TEST_ROUTE_PROVIDER",
    distance_meters: 1200,
    duration_seconds: 300,
    traffic_summary: "TEST_TRAFFIC",
    fetched_at: "2026-01-01T00:00:00Z",
    path: null,
    source_name: "TEST_ROUTE_SOURCE",
    source_record_id: "TEST_ROUTE_001",
    raw_payload_id: null,
    schema_version: "TEST_ROUTE_V1",
    source_metadata: {},
  },
} satisfies HospitalRoute;

export const systemStatusExample = {
  generated_at: "2026-01-01T00:00:00Z",
  mode: "limited",
  environment: "test",
  services: {},
  data: {
    patients: 0,
    hospitals: 1,
    emergency_institutions: 1,
    emergency_institutions_with_realtime: 0,
    emergency_institutions_with_departments: 1,
    emergency_institutions_with_equipment: 1,
    emergency_institutions_with_capabilities: 0,
    source_identities_verified: 0,
    source_identities_unverified: 1,
    route_snapshots: 0,
    active_policies: 0,
  },
  readiness: {
    chat_intake: true,
    voice_intake: false,
    hospital_candidates: true,
    live_routes: true,
    policy_recommendation: false,
  },
  warnings: [
    "HOSPITAL_SOURCE_IDENTITIES_UNVERIFIED",
    "RECOMMENDATION_POLICY_NOT_CONFIGURED",
  ],
} satisfies SystemStatus;

export const dataSourceStatusExample = {
  source_name: "nemc-emergency-medical",
  dataset_id: "TEST_DATASET",
  provider_name: "TEST_PROVIDER",
  enabled: true,
  schema_version: "TEST_SCHEMA",
  last_success_at: "2026-01-01T00:00:00Z",
  last_failure_at: null,
  last_error: null,
  status: "unknown",
  age_seconds: null,
  freshness_threshold_seconds: null,
  reason: "TEST_THRESHOLD_NOT_CONFIGURED",
} satisfies DataSourceStatus;

export const routingStatusExample = {
  provider: "TEST_ROUTE_PROVIDER",
  configured: true,
  calls_used: 0,
  calls_limit: null,
  cache_max_age_seconds: null,
  max_concurrency: 1,
  status: "configured",
} satisfies RoutingStatus;
