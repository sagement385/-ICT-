import type { Hospital } from "../types/hospital";
import type { RecommendationResult } from "../types/recommendation";
import DataFreshnessBadge from "./DataFreshnessBadge";

type Props = {
  recommendation: RecommendationResult | null;
  nearbyHospitals: Hospital[];
  loading: boolean;
  notice: string | null;
  onRetry: () => void;
};

type FreshnessStatus = "fresh" | "stale" | "unknown" | "unavailable";

function resultFreshness(payload: Record<string, unknown>): FreshnessStatus {
  const statuses = Object.values(payload).flatMap((value) => {
    if (!value || typeof value !== "object" || !("status" in value)) return [];
    const status = (value as { status?: unknown }).status;
    return typeof status === "string" ? [status] : [];
  });
  if (statuses.includes("unavailable")) return "unavailable";
  if (statuses.includes("stale")) return "stale";
  if (statuses.length > 0 && statuses.every((status) => status === "fresh")) return "fresh";
  return "unknown";
}

export default function HospitalRankingPanel({ recommendation, nearbyHospitals, loading, notice, onRetry }: Props) {
  if (loading) {
    return (
      <section className="panel">
        <div className="section-heading"><h2>병원 후보 확인 중</h2><span className="loading-dot">●</span></div>
        <p className="empty-copy">실제 병원 데이터와 이동시간을 확인하고 있습니다.</p>
      </section>
    );
  }
  return (
    <section className="panel ranking-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SOURCE-BACKED {recommendation ? "RECOMMENDATION" : "CANDIDATES"}</span>
          <h2>{recommendation ? "정책 기반 추천 병원" : "주변 병원 후보"}</h2>
        </div>
        <span className="status-pill">반경 5~10km</span>
      </div>
      {notice && <div className="notice-box">{notice}<div><button className="choice-button" type="button" onClick={onRetry}>다시 조회</button></div></div>}
      {recommendation
        ? recommendation.recommended_hospitals.map((hospital) => (
            <article className="hospital-card" key={hospital.hospital_id}>
              <div className="rank-number">{hospital.rank}</div>
              <div className="hospital-main">
                <strong>{hospital.hospital_name}</strong>
                <span>
                  {hospital.travel_time
                    ? `${Math.round(hospital.travel_time.duration_seconds / 60)}분 · ${(hospital.travel_time.distance_meters / 1000).toFixed(1)}km`
                    : "이동시간 확인 불가"}
                </span>
                <span>정책 점수: {hospital.total_score}</span>
                {hospital.recommendation_reasons.map((reason) => <span key={reason}>• {reason}</span>)}
                <DataFreshnessBadge
                  status={resultFreshness(hospital.data_freshness)}
                  reason="원본별 최신성 상태를 종합한 표시입니다."
                />
              </div>
            </article>
          ))
        : nearbyHospitals.slice(0, 3).map((hospital) => (
            <article className="hospital-card" key={hospital.hospital_id}>
              <div className="rank-number muted-rank">후보</div>
              <div className="hospital-main">
                <strong>{hospital.hospital_name}</strong>
                <span>{hospital.hospital_type_code ?? "종별 미확인"}</span>
                <DataFreshnessBadge status={hospital.freshness.status} reason={hospital.freshness.reason} />
              </div>
              <span className="candidate-label">순위 없음</span>
            </article>
          ))}
      {!recommendation && nearbyHospitals.length === 0 && (
        <div className="empty-copy">동기화된 충북 병원 데이터가 없거나 위치 좌표가 없습니다.</div>
      )}
      {!recommendation && nearbyHospitals.length > 0 && (
        <p className="muted-note">활성 추천 정책이 없으면 후보에 순위·점수를 부여하지 않습니다.</p>
      )}
    </section>
  );
}
