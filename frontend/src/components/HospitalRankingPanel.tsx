import type { HospitalRoute } from "../api/routing";
import type { HospitalCandidate } from "../types/hospital";
import type { RecommendationResult } from "../types/recommendation";
import DataFreshnessBadge from "./DataFreshnessBadge";

type Props = {
  recommendation: RecommendationResult | null;
  nearbyHospitals: HospitalCandidate[];
  routes: HospitalRoute[];
  loading: boolean;
  notice: string | null;
  selectedHospitalId: string | null;
  onSelectHospital: (hospitalId: string) => void;
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

function routeLabel(route: HospitalRoute | undefined): string {
  if (!route) return "실제 경로 확인 불가";
  const minutes = Math.max(1, Math.round(route.route.duration_seconds / 60));
  const distance = (route.route.distance_meters / 1000).toFixed(1);
  return `${minutes}분 · ${distance}km · ${route.cache_status === "hit" ? "캐시" : "실시간 호출"}`;
}

export default function HospitalRankingPanel({
  recommendation,
  nearbyHospitals,
  routes,
  loading,
  notice,
  selectedHospitalId,
  onSelectHospital,
  onRetry,
}: Props) {
  const routeByHospital = new Map(routes.map((item) => [item.hospital_id, item]));
  return (
    <section className="panel ranking-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">SOURCE-BACKED {recommendation ? "RECOMMENDATION" : "CANDIDATES"}</span>
          <h2>{recommendation ? "정책 기반 추천 병원" : "주변 응급기관 후보"}</h2>
        </div>
        <span className="status-pill">반경 10km</span>
      </div>
      {loading && <div className="loading-banner"><span />실제 데이터 확인 중</div>}
      {notice && (
        <div className="notice-box">
          {notice}
          <div><button className="choice-button" type="button" onClick={onRetry}>다시 조회</button></div>
        </div>
      )}
      <div className="hospital-list">
        {recommendation
          ? recommendation.recommended_hospitals.map((hospital) => (
              <button
                type="button"
                className={`hospital-card ${selectedHospitalId === hospital.hospital_id ? "selected" : ""}`}
                key={hospital.hospital_id}
                onClick={() => onSelectHospital(hospital.hospital_id)}
              >
                <div className="rank-number">{hospital.rank}</div>
                <div className="hospital-main">
                  <strong>{hospital.hospital_name}</strong>
                  <span>
                    {hospital.travel_time
                      ? `${Math.max(1, Math.round(hospital.travel_time.duration_seconds / 60))}분 · ${(hospital.travel_time.distance_meters / 1000).toFixed(1)}km`
                      : "이동시간 확인 불가"}
                  </span>
                  <span>정책 점수: {hospital.total_score}</span>
                  {hospital.recommendation_reasons.map((reason) => <span key={reason}>• {reason}</span>)}
                  <DataFreshnessBadge
                    status={resultFreshness(hospital.data_freshness)}
                    reason="원본별 최신성 상태를 종합한 표시입니다."
                  />
                </div>
              </button>
            ))
          : nearbyHospitals.map((hospital) => {
              const realtime = hospital.realtime_status;
              return (
                <button
                  type="button"
                  className={`hospital-card ${selectedHospitalId === hospital.hospital_id ? "selected" : ""}`}
                  key={hospital.hospital_id}
                  onClick={() => onSelectHospital(hospital.hospital_id)}
                >
                  <div className="rank-number muted-rank">후보</div>
                  <div className="hospital-main">
                    <strong>{hospital.hospital_name}</strong>
                    <span>{hospital.emergency_profile?.emergency_type_name ?? "응급기관 분류 미확인"}</span>
                    <span className="route-value">{routeLabel(routeByHospital.get(hospital.hospital_id))}</span>
                    <div className="detail-counts">
                      <span>진료과 {hospital.departments.length}</span>
                      <span>장비 {hospital.equipment.length}</span>
                      <span>특수진료 {hospital.capabilities.length}</span>
                    </div>
                    <span>
                      {realtime
                        ? "NEMC 원본 연결 · 수용/병상 코드 의미 확인 전"
                        : "NEMC 실시간 원본 미연결"}
                    </span>
                    {hospital.emergency_profile?.coordinate_warning && (
                      <span className="warning-text">기관 간 좌표 차이 확인 필요</span>
                    )}
                    {hospital.emergency_profile && !hospital.emergency_profile.identity_verified && (
                      <span className="warning-text">기관 식별자 자동 매칭 · 사람 검토 필요</span>
                    )}
                    <DataFreshnessBadge
                      status={realtime?.freshness.status ?? hospital.emergency_profile?.freshness.status ?? "unavailable"}
                      reason={realtime?.freshness.reason ?? hospital.emergency_profile?.freshness.reason ?? "출처 없음"}
                    />
                  </div>
                  <span className="candidate-label">순위 없음</span>
                </button>
              );
            })}
      </div>
      {!recommendation && nearbyHospitals.length === 0 && !loading && (
        <div className="empty-copy">반경 안에 동기화된 공식 응급의료기관이 없거나 위치 좌표가 없습니다.</div>
      )}
      {!recommendation && nearbyHospitals.length > 0 && (
        <p className="muted-note">표시 순서는 거리 조회 후보 순서이며 추천 순위가 아닙니다.</p>
      )}
      {recommendation?.warnings.length ? (
        <div className="result-warnings">{recommendation.warnings.join(" · ")}</div>
      ) : null}
    </section>
  );
}
