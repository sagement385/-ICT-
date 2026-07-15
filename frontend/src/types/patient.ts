export type PatientLocation = {
  latitude: number | null;
  longitude: number | null;
  address_text: string | null;
};

export type PatientSymptom = {
  code: string;
  label: string;
  confidence: number | null;
};

export type PatientEvent = {
  incident_id: string;
  observed_at: string;
  location: PatientLocation;
  symptoms: PatientSymptom[];
  consciousness_status: string | null;
  breathing_status: string | null;
  bleeding_status: string | null;
  urgency_level: string | null;
  source: { model_name: string; model_version: string };
  created_at?: string;
  updated_at?: string;
};

