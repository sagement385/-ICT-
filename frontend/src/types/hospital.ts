export type DataFreshness = {
  status: "fresh" | "stale" | "unknown" | "unavailable";
  observed_at: string | null;
  reason: string | null;
};

export type HospitalSummary = {
  hospital_id: string;
  hospital_name: string;
  hospital_type_code: string | null;
  location: {
    latitude: number | null;
    longitude: number | null;
    address: string | null;
  };
  phone: string | null;
  source_name: string;
  source_record_id: string | null;
  raw_payload_id: string | null;
  schema_version: string;
  source_updated_at: string | null;
  freshness: DataFreshness;
  emergency_profile: {
    emergency_type_code: string | null;
    emergency_type_name: string | null;
    representative_phone: string | null;
    emergency_phone: string | null;
    source_name: string;
    source_record_id: string;
    raw_payload_id: string | null;
    schema_version: string;
    fetched_at: string;
    source_updated_at: string | null;
    match_method: string;
    identity_verified: boolean;
    coordinate_warning: boolean;
    freshness: DataFreshness;
  } | null;
};

export type Hospital = HospitalSummary;

export type HospitalCandidate = HospitalSummary & {
  departments: Array<{
    department_code: string | null;
    department_name: string;
    specialist_count: number | null;
    source_name: string | null;
    source_record_id: string | null;
    raw_payload_id: string | null;
    schema_version: string | null;
    source_updated_at: string | null;
    fetched_at: string | null;
  }>;
  equipment: Array<{
    equipment_code: string | null;
    equipment_name: string;
    equipment_count: number | null;
    source_name: string | null;
    source_record_id: string | null;
    raw_payload_id: string | null;
    schema_version: string | null;
    source_updated_at: string | null;
    fetched_at: string | null;
  }>;
  capabilities: Array<{
    capability_code: string | null;
    capability_name: string;
    available: boolean | null;
    source_name: string | null;
    source_record_id: string | null;
    raw_payload_id: string | null;
    schema_version: string | null;
    source_updated_at: string | null;
    fetched_at: string | null;
  }>;
  realtime_status: {
    acceptance_status: string | null;
    available_beds: number | null;
    source_name: string;
    source_record_id: string | null;
    raw_payload_id: string | null;
    schema_version: string;
    source_updated_at: string | null;
    source_updated_at_raw: string | null;
    source_timezone: string;
    fetched_at: string;
    freshness: DataFreshness;
  } | null;
};
