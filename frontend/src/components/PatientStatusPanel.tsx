import type { PatientEvent } from "../types/patient";

type Props = { patient: PatientEvent | null };

export default function PatientStatusPanel({ patient }: Props) {
  if (!patient) return <section><h2>환자 상태</h2><p>환자 정보 대기 중</p></section>;
  return (
    <section>
      <h2>환자 상태</h2>
      <p>사건 ID: {patient.incident_id}</p>
      <p>의식: {patient.consciousness_status ?? "확인되지 않음"}</p>
      <p>호흡: {patient.breathing_status ?? "확인되지 않음"}</p>
      <p>출혈: {patient.bleeding_status ?? "확인되지 않음"}</p>
      <p>긴급도: {patient.urgency_level ?? "확인되지 않음"}</p>
      <p>증상 수: {patient.symptoms.length}</p>
    </section>
  );
}

