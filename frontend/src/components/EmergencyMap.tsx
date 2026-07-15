import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

type Props = { patient: PatientEvent | null; recommendation: RecommendationResult | null };

export default function EmergencyMap({ patient, recommendation }: Props) {
  const mapClientId = import.meta.env.VITE_NAVER_MAP_CLIENT_ID as string | undefined;
  if (!mapClientId) return <section><h2>지도</h2><p>지도 API 미설정. 지도와 마커를 표시하지 않습니다.</p></section>;
  if (!patient) return <section><h2>지도</h2><p>환자 정보 대기 중</p></section>;
  return (
    <section>
      <h2>지도</h2>
      <p>네이버 지도 SDK 연결 대기 중</p>
      <p>환자 위치: {patient.location.address_text ?? "좌표 확인 필요"}</p>
      <p>표시할 추천 병원: {recommendation?.recommended_hospitals.length ?? 0}개</p>
    </section>
  );
}

