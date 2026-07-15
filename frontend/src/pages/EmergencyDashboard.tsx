import { useState } from "react";
import { getLatestRecommendation, runRecommendation } from "../api/recommendations";
import { getPatient } from "../api/patients";
import { ApiError } from "../api/client";
import EmergencyMap from "../components/EmergencyMap";
import HospitalRankingPanel from "../components/HospitalRankingPanel";
import PatientStatusPanel from "../components/PatientStatusPanel";
import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

export default function EmergencyDashboard() {
  const [incidentId, setIncidentId] = useState("");
  const [patient, setPatient] = useState<PatientEvent | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("추천 데이터를 자동으로 만들지 않습니다.");

  async function loadPatient() {
    if (!incidentId.trim()) return setMessage("incident_id를 입력하세요.");
    setLoading(true);
    setMessage("환자 정보 조회 중");
    try {
      setPatient(await getPatient(incidentId.trim()));
      setRecommendation(await getLatestRecommendation(incidentId.trim()).catch(() => null));
      setMessage("환자 정보 확인됨");
    } catch (error) {
      setPatient(null);
      setRecommendation(null);
      setMessage(error instanceof ApiError ? `${error.code}: ${error.message}` : "환자 정보 조회 실패");
    } finally {
      setLoading(false);
    }
  }

  async function run() {
    if (!incidentId.trim()) return setMessage("incident_id를 입력하세요.");
    setLoading(true);
    setMessage("추천 실행 중");
    try {
      setRecommendation(await runRecommendation(incidentId.trim()));
      setMessage("추천 결과 있음");
    } catch (error) {
      setRecommendation(null);
      setMessage(error instanceof ApiError ? `${error.code}: ${error.message}` : "추천 실행 실패");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      <h1>충북 119 응급환자 지원</h1>
      <p>의료진·구급대원의 판단을 보조하며, 데이터가 없으면 결과를 표시하지 않습니다.</p>
      <div>
        <input value={incidentId} onChange={(event) => setIncidentId(event.target.value)} placeholder="incident_id" />
        <button onClick={loadPatient} disabled={loading}>환자 조회</button>
        <button onClick={run} disabled={loading || !patient}>추천 실행</button>
      </div>
      <p role="status">상태: {message}</p>
      <PatientStatusPanel patient={patient} />
      <EmergencyMap patient={patient} recommendation={recommendation} />
      <HospitalRankingPanel recommendation={recommendation} loading={loading} />
    </main>
  );
}

