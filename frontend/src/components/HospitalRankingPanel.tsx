import type { Hospital } from "../types/hospital";
import type { RecommendationResult } from "../types/recommendation";
import DataFreshnessBadge from "./DataFreshnessBadge";

type Props = { recommendation: RecommendationResult | null; nearbyHospitals: Hospital[]; loading: boolean; notice: string | null };

export default function HospitalRankingPanel({ recommendation, nearbyHospitals, loading, notice }: Props) {
  if (loading) return <section className="panel"><div className="section-heading"><h2>추천 병원 TOP 3</h2><span className="loading-dot">●</span></div><p className="empty-copy">실시간 상태와 이동시간을 확인하고 있습니다.</p></section>;
  return (
    <section className="panel ranking-panel">
      <div className="section-heading"><div><span className="eyebrow">SOURCE-BACKED CANDIDATES</span><h2>추천 병원 TOP 3</h2></div><span className="status-pill">반경 5~10km</span></div>
      {notice && <div className="notice-box">{notice}</div>}
      {recommendation ? recommendation.recommended_hospitals.map((hospital) => <article className="hospital-card" key={hospital.hospital_id}><div className="rank-number">{hospital.rank}</div><div className="hospital-main"><strong>{hospital.hospital_name}</strong><span>{hospital.travel_time ? `${Math.round(hospital.travel_time.duration_seconds / 60)}분 · ${(hospital.travel_time.distance_meters / 1000).toFixed(1)}km` : "이동시간 확인 불가"}</span><DataFreshnessBadge status="unknown" reason="원본별 최신성 확인 필요" /></div></article>) : nearbyHospitals.slice(0, 3).map((hospital, index) => <article className="hospital-card" key={hospital.hospital_id}><div className="rank-number muted-rank">{index + 1}</div><div className="hospital-main"><strong>{hospital.hospital_name}</strong><span>{hospital.hospital_type_code ?? "종별 미확인"}</span><DataFreshnessBadge status={hospital.freshness.status} reason={hospital.freshness.reason} /></div><span className="candidate-label">후보</span></article>)}
      {!recommendation && nearbyHospitals.length === 0 && <div className="empty-copy">동기화된 충북 병원 데이터가 없거나 위치 좌표가 없습니다.</div>}
      {!recommendation && nearbyHospitals.length > 0 && <p className="muted-note">추천 정책이 설정되기 전에는 실제 후보만 표시하고 순위·점수는 생성하지 않습니다.</p>}
    </section>
  );
}
