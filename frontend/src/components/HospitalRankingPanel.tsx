import type { RecommendationResult } from "../types/recommendation";
import DataFreshnessBadge from "./DataFreshnessBadge";

type Props = { recommendation: RecommendationResult | null; loading: boolean };

export default function HospitalRankingPanel({ recommendation, loading }: Props) {
  if (loading) return <section><h2>추천 병원</h2><p>추천 실행 중</p></section>;
  if (!recommendation) return <section><h2>추천 병원</h2><p>추천 결과 없음</p></section>;
  return (
    <section>
      <h2>추천 병원</h2>
      <p>정책: {recommendation.policy.policy_name} / {recommendation.policy.policy_version}</p>
      {recommendation.warnings.map((warning) => <p key={warning}>경고: {warning}</p>)}
      {recommendation.recommended_hospitals.map((hospital) => (
        <article key={hospital.hospital_id}>
          <h3>{hospital.rank}. {hospital.hospital_name}</h3>
          <p>추천 점수: {hospital.total_score}</p>
          <p>{hospital.recommendation_reasons.join(" · ") || "근거 없음"}</p>
          <DataFreshnessBadge status="unknown" reason="결과 freshness 원본 확인 필요" />
        </article>
      ))}
    </section>
  );
}

