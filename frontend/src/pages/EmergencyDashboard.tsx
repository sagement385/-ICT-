import { useEffect, useMemo, useState } from "react";
import { ApiError, formatApiError } from "../api/client";
import ChatIntake from "../components/ChatIntake";
import EmergencyMap from "../components/EmergencyMap";
import HospitalRankingPanel from "../components/HospitalRankingPanel";
import OperationalStatusPanel from "../components/OperationalStatusPanel";
import PatientStatusPanel from "../components/PatientStatusPanel";
import {
  useDataSources,
  useHospitalRoutes,
  useNearbyHospitals,
  useRoutingStatus,
  useRunRecommendation,
  useSystemStatus,
} from "../hooks/useEmergencyData";
import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

function errorMessage(error: unknown, fallback: string): string | null {
  if (!error) return null;
  return error instanceof ApiError ? formatApiError(error) : fallback;
}

function newestSuccess(values: Array<string | null | undefined>): string | null {
  const timestamps = values.flatMap((value) => value ? [new Date(value).getTime()] : []);
  if (!timestamps.length) return null;
  return new Date(Math.max(...timestamps)).toISOString();
}

function relativeTime(value: string | null): string {
  if (!value) return "수집 이력 없음";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}초 전`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
  return `${Math.floor(seconds / 3600)}시간 전`;
}

export default function EmergencyDashboard() {
  const [patient, setPatient] = useState<PatientEvent | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);
  const [recommendationError, setRecommendationError] = useState<unknown>(null);
  const [recommendationNotice, setRecommendationNotice] = useState<string | null>(null);
  const [selectedHospitalId, setSelectedHospitalId] = useState<string | null>(null);
  const incidentId = patient?.incident_id ?? null;
  const systemStatus = useSystemStatus();
  const dataSources = useDataSources();
  const routingStatus = useRoutingStatus();
  const nearbyQuery = useNearbyHospitals(incidentId);
  const hospitals = nearbyQuery.data ?? [];
  const hospitalIds = useMemo(
    () => hospitals.slice(0, 10).map((hospital) => hospital.hospital_id),
    [hospitals],
  );
  const routesQuery = useHospitalRoutes(incidentId, hospitalIds);
  const routes = routesQuery.data?.routes ?? [];
  const runRecommendation = useRunRecommendation();

  useEffect(() => {
    if (!selectedHospitalId && hospitals.length > 0) {
      setSelectedHospitalId(hospitals[0].hospital_id);
    }
  }, [hospitals, selectedHospitalId]);

  async function handlePatientCompleted(created: PatientEvent): Promise<void> {
    setPatient(created);
    setRecommendation(null);
    setRecommendationError(null);
    setRecommendationNotice(null);
    setSelectedHospitalId(null);
    if (systemStatus.data?.readiness.policy_recommendation !== true) {
      setRecommendationNotice(
        "승인된 추천 정책이 없어 점수·순위를 생성하지 않습니다. 현재는 공식 응급기관과 실제 이동 경로만 비교합니다.",
      );
      return;
    }
    try {
      const result = await runRecommendation.mutateAsync({ incidentId: created.incident_id });
      setRecommendation(result);
    } catch (error) {
      setRecommendationError(error);
    }
  }

  function resetIncident(): void {
    setPatient(null);
    setRecommendation(null);
    setRecommendationError(null);
    setRecommendationNotice(null);
    setSelectedHospitalId(null);
    runRecommendation.reset();
  }

  async function retryCurrentPatient(): Promise<void> {
    if (!patient) return;
    setRecommendationError(null);
    setRecommendationNotice(null);
    const tasks: Promise<unknown>[] = [nearbyQuery.refetch()];
    if (hospitalIds.length > 0) tasks.push(routesQuery.refetch());
    if (systemStatus.data?.readiness.policy_recommendation === true) {
      tasks.push(
        runRecommendation.mutateAsync({ incidentId: patient.incident_id })
          .then(setRecommendation)
          .catch(setRecommendationError),
      );
    } else {
      setRecommendationNotice(
        "추천 정책 미설정 상태입니다. 후보·경로 데이터만 다시 조회했습니다.",
      );
    }
    await Promise.allSettled(tasks);
  }

  async function refreshOperationalStatus(): Promise<void> {
    // Refresh non-billable readiness data without triggering route API calls.
    await Promise.allSettled([
      systemStatus.refetch(),
      dataSources.refetch(),
      routingStatus.refetch(),
      ...(patient ? [nearbyQuery.refetch()] : []),
    ]);
  }

  const notices = [
    errorMessage(nearbyQuery.error, "주변 병원 조회에 실패했습니다."),
    errorMessage(routesQuery.error, "실제 경로 조회에 실패했습니다."),
    errorMessage(recommendationError, "추천 실행에 실패했습니다."),
    recommendationNotice,
    ...(routesQuery.data?.errors.map((error) => `${error.code}: ${error.message}`) ?? []),
  ].filter((value): value is string => Boolean(value));
  const latestDataAt = newestSuccess(
    dataSources.data?.map((source) => source.last_success_at) ?? [],
  );
  const loading = nearbyQuery.isFetching || routesQuery.isFetching || runRecommendation.isPending;
  const selectedRoute = routes.find((item) => item.hospital_id === selectedHospitalId)?.route
    ?? routes[0]?.route
    ?? null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">119</div>
        <div className="brand-caption">충북<br />응급의료</div>
        <nav aria-label="주요 메뉴">
          <button className="nav-item active">⌂ <span>실시간 상황</span></button>
          <button className="nav-item" disabled>▣ <span>신고 목록</span></button>
          <button className="nav-item" disabled>▦ <span>병원 조회</span></button>
          <button className="nav-item" disabled>▥ <span>통계 현황</span></button>
          <button className="nav-item" disabled>▤ <span>데이터 현황</span></button>
        </nav>
        <div className="system-card">
          <span>시스템 상태</span>
          <strong>
            {systemStatus.isError
              ? "연결 실패"
              : systemStatus.isPending
                ? "확인 중"
                : systemStatus.data?.mode === "operational"
                  ? "운영"
                  : "제한"}
          </strong>
          <small>
            채팅 {systemStatus.data?.readiness.chat_intake ? "가능" : "불가"}
            {" · "}음성 {systemStatus.data?.readiness.voice_intake ? "가능" : "보류"}
          </small>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div>
            <h1>충북 119 AI 응급의료 지원 시스템</h1>
            <p>실제 병원·경로 데이터를 비교하는 의료 의사결정 보조 화면</p>
          </div>
          <div className="topbar-actions">
            <span className="live-indicator">
              <i className={systemStatus.isError ? "offline" : systemStatus.isFetching ? "pending" : "online"} />
              {systemStatus.isError
                ? "상태 API 연결 실패"
                : systemStatus.isFetching
                  ? "상태 확인 중"
                  : `데이터 ${relativeTime(latestDataAt)}`}
            </span>
            <button
              className="refresh-button"
              type="button"
              onClick={() => void refreshOperationalStatus()}
              disabled={systemStatus.isFetching || dataSources.isFetching}
            >
              상태 새로고침
            </button>
            <button className="emergency-button" type="button" disabled>
              의료진 판단 우선
            </button>
          </div>
        </header>
        <div className="dashboard-grid">
          <div className="left-column">
            <ChatIntake
              onCompleted={handlePatientCompleted}
              onReset={resetIncident}
              disabled={loading}
            />
            <PatientStatusPanel patient={patient} />
          </div>
          <div className="center-column">
            <EmergencyMap
              patient={patient}
              hospitals={hospitals}
              recommendation={recommendation}
              route={selectedRoute}
              routes={routes}
              selectedHospitalId={selectedHospitalId}
              onSelectHospital={setSelectedHospitalId}
            />
            <OperationalStatusPanel
              status={systemStatus.data ?? null}
              dataSources={dataSources.data ?? []}
              routing={routingStatus.data ?? null}
              candidateCount={hospitals.length}
              routeCount={routes.length}
            />
          </div>
          <div className="right-column">
            <HospitalRankingPanel
              recommendation={recommendation}
              nearbyHospitals={hospitals}
              routes={routes}
              loading={loading}
              notice={notices.length ? notices.join(" | ") : null}
              selectedHospitalId={selectedHospitalId}
              onSelectHospital={setSelectedHospitalId}
              onRetry={() => void retryCurrentPatient()}
            />
            <section className="panel limitation-panel">
              <div className="section-heading"><h2>운영 안전 경계</h2><span className="status-pill">필수 확인</span></div>
              <p>음성 STT·의료 엔터티 모델은 아직 연결되지 않아 채팅 확인 입력을 사용합니다.</p>
              <p>수용 가능 여부와 병상 의미는 공식 코드표 확인 전까지 표시하지 않습니다.</p>
              <p>승인된 추천 정책이 없으면 후보에 순위·점수를 부여하지 않습니다.</p>
              <p>이 화면은 의료진·구급대원·의료지도의사의 판단을 대체하지 않습니다.</p>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
