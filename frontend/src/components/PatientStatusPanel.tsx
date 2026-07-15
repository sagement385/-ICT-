import type { PatientEvent } from "../types/patient";

type Props = { patient: PatientEvent | null };

export default function PatientStatusPanel({ patient }: Props) {
  if (!patient) return <section className="panel"><div className="section-heading"><h2>현재 신고 정보</h2><span className="new-badge">대기</span></div><p className="empty-copy">채팅으로 신고 상황을 입력해주세요.</p></section>;
  return (
    <section className="panel patient-panel">
      <div className="section-heading"><div><span className="eyebrow">CURRENT INCIDENT</span><h2>현재 신고 정보</h2></div><span className="new-badge">신규</span></div>
      <dl className="info-list"><div><dt>사건 번호</dt><dd>{patient.incident_id}</dd></div><div><dt>접수 시각</dt><dd>{new Date(patient.observed_at).toLocaleString("ko-KR")}</dd></div><div><dt>발생 위치</dt><dd>{patient.location.address_text ?? "좌표 입력"}</dd></div></dl>
      <div className="subsection-title">환자 상태 <span>(채팅 입력 결과)</span></div>
      <div className="status-grid"><Status label="의식 상태" value={patient.consciousness_status} /><Status label="호흡 상태" value={patient.breathing_status} /><Status label="출혈 여부" value={patient.bleeding_status} /><Status label="긴급도" value={patient.urgency_level} /></div>
      <div className="symptom-box"><span>주요 증상</span><strong>{patient.symptoms.map((symptom) => symptom.label).join(", ") || "확인되지 않음"}</strong></div>
    </section>
  );
}

function Status({ label, value }: { label: string; value: string | null }) {
  return <div className="status-row"><span>{label}</span><strong className={value ? "has-value" : "missing-value"}>{value ?? "확인되지 않음"}</strong></div>;
}
