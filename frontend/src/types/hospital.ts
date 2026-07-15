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
};
