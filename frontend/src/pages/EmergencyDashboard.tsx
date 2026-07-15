import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { getNearbyHospitals } from "../api/hospitals";
import { getHospitalRoutes, getRoutingStatus, type HospitalRoute, type RouteSnapshot, type RoutingStatus } from "../api/routing";
import { runRecommendation } from "../api/recommendations";
import ChatIntake from "../components/ChatIntake";
import EmergencyMap from "../components/EmergencyMap";
import HospitalRankingPanel from "../components/HospitalRankingPanel";
import PatientStatusPanel from "../components/PatientStatusPanel";
import type { Hospital } from "../types/hospital";
import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

export default function EmergencyDashboard() {
  const [patient, setPatient] = useState<PatientEvent | null>(null);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);
  const [route, setRoute] = useState<RouteSnapshot | null>(null);
  const [routes, setRoutes] = useState<HospitalRoute[]>([]);
  const [routingStatus, setRoutingStatus] = useState<RoutingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void getRoutingStatus().then(setRoutingStatus).catch(() => setRoutingStatus(null));
  }, []);

  async function handlePatientCompleted(created: PatientEvent): Promise<void> {
    setPatient(created);
    setRecommendation(null);
    setRoute(null);
    setRoutes([]);
    setHospitals([]);
    setLoading(true);
    setNotice(null);
    try {
      const messages: string[] = [];
      if (created.location.latitude !== null && created.location.longitude !== null) {
        const nearbyHospitals = await getNearbyHospitals(created.location.latitude, created.location.longitude, 10);
        setHospitals(nearbyHospitals);
        const destinations = nearbyHospitals.slice(0, 10).flatMap((hospital) => {
          const latitude = hospital.location.latitude;
          const longitude = hospital.location.longitude;
          return latitude !== null && longitude !== null
            ? [{ hospital_id: hospital.hospital_id, latitude, longitude }]
            : [];
        });
        if (destinations.length > 0) {
          try {
            const batch = await getHospitalRoutes(
              {
                origin_latitude: created.location.latitude,
                origin_longitude: created.location.longitude,
              },
              destinations,
            );
            setRoutes(batch.routes);
            setRoute(batch.routes[0]?.route ?? null);
            if (batch.errors.length > 0) {
              const errorCodes = [...new Set(batch.errors.map((item) => item.code))].join(", ");
              messages.push(`경로 ${batch.errors.length}건을 확인하지 못했습니다. (${errorCodes})`);
            }
          } catch (error) {
            messages.push(error instanceof ApiError ? `경로: ${error.code}: ${error.message}` : "실제 경로를 확인하지 못했습니다.");
          }
        }
      } else {
        messages.push("환자 좌표가 없어 주변 병원과 경로를 조회할 수 없습니다.");
      }
      try {
        setRecommendation(await runRecommendation(created.incident_id));
      } catch (error) {
        if (error instanceof ApiError && error.code === "RECOMMENDATION_POLICY_NOT_CONFIGURED") {
          messages.push("추천 정책이 아직 설정되지 않아 지도와 주변 후보 병원만 표시합니다.");
        } else {
          const message = error instanceof ApiError ? `${error.code}: ${error.message}` : "추천 결과를 생성하지 못했습니다.";
          messages.push(`추천: ${message}`);
        }
      }
      setNotice(messages.length > 0 ? messages.join(" | ") : null);
    } catch (error) {
      setNotice(error instanceof ApiError ? `${error.code}: ${error.message}` : "주변 병원 조회에 실패했습니다.");
    } finally {
      setLoading(false);
      void getRoutingStatus().then(setRoutingStatus).catch(() => undefined);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar"><div className="brand-mark">119</div><div className="brand-caption">충북<br />응급의료</div><nav><button className="nav-item active">⌂ <span>실시간 상황</span></button><button className="nav-item">▣ <span>신고 목록</span></button><button className="nav-item">▦ <span>병원 조회</span></button><button className="nav-item">▥ <span>통계 현황</span></button><button className="nav-item">▤ <span>데이터 현황</span></button><button className="nav-item">⚙ <span>설정</span></button></nav><div className="system-card"><span>시스템 상태</span><strong>정상</strong><small>음성 입력 보류 · 채팅 모드</small></div></aside>
      <main className="main-content">
        <header className="topbar"><div><h1>충북 119 AI 응급의료 지원 시스템</h1><p>AI 기반 병원 추천 및 이송 경로 안내</p></div><div className="topbar-actions"><span>↻ 데이터 업데이트: 1분 전 <b>● 정상</b></span><button className="emergency-button">☎ 신고 접수 중</button></div></header>
        <div className="dashboard-grid">
          <div className="left-column"><ChatIntake onCompleted={handlePatientCompleted} disabled={loading} /><PatientStatusPanel patient={patient} /></div>
          <div className="center-column"><EmergencyMap patient={patient} hospitals={hospitals} recommendation={recommendation} route={route} routes={routes} /><section className="panel data-panel"><div className="section-heading"><h2>데이터 연계 현황</h2><span className="status-pill">실제 응답 기반</span></div><div className="data-status-row"><span>HIRA 병원정보</span><strong>{hospitals.length > 0 ? "연결" : "대기"}</strong></div><div className="data-status-row"><span>국립중앙의료원 실시간 상태</span><strong>원본 저장 구조 연결</strong></div><div className="data-status-row"><span>네이버 Directions</span><strong>{route ? `${routes.length}개 실제 경로 확인` : routingStatus ? (routingStatus.calls_limit === null ? `${routingStatus.calls_used}회 · 제한 없음` : `${routingStatus.calls_used}/${routingStatus.calls_limit}회`) : "확인 중"}</strong></div></section></div>
          <div className="right-column"><HospitalRankingPanel recommendation={recommendation} nearbyHospitals={hospitals} loading={loading} notice={notice} /><section className="panel limitation-panel"><h2>운영 제한</h2><p>음성 AI 데이터는 보류 중입니다. 현재는 채팅 입력을 사용합니다.</p><p>추천 정책이 없으면 임의 점수와 병원 순위를 생성하지 않습니다.</p><p>의료진·구급대원의 판단을 대체하지 않습니다.</p></section></div>
        </div>
      </main>
    </div>
  );
}
