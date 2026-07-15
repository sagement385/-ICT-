export type RecommendationResult = {
  incident_id: string;
  recommendation_run_id: string;
  generated_at: string;
  policy: { policy_name: string; policy_version: string };
  recommended_hospitals: Array<{
    rank: number;
    hospital_id: string;
    hospital_name: string;
    location: { latitude: number | null; longitude: number | null; address: string | null };
    total_score: number;
    score_breakdown: Record<string, unknown>;
    travel_time: {
      duration_seconds: number;
      distance_meters: number;
      provider_name: string;
      fetched_at: string;
    } | null;
    recommendation_reasons: string[];
    data_freshness: Record<string, unknown>;
  }>;
  warnings: string[];
};

