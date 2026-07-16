export type Hospital = {
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
  freshness: {
    status: "fresh" | "stale" | "unknown" | "unavailable";
    observed_at: string | null;
    reason: string | null;
  };
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
    coordinate_warning: boolean;
    freshness: {
      status: "fresh" | "stale" | "unknown" | "unavailable";
      observed_at: string | null;
      reason: string | null;
    };
  } | null;
};
