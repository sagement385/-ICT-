import { useMemo, useState } from "react";
import { ApiError } from "../api/client";
import { assistPatientText, createPatient, geocodeAddress, type CreatePatientEvent } from "../api/patients";
import type { PatientEvent } from "../types/patient";

type ChatMessage = { id: number; role: "assistant" | "user"; text: string };
type Step = "location" | "consciousness" | "breathing" | "bleeding" | "symptom" | "urgency";
type Props = { onCompleted: (patient: PatientEvent) => Promise<void>; disabled?: boolean };

const prompts: Record<Step, string> = {
  location: "환자 위치를 주소로 입력해주세요. 좌표를 알고 있다면 위도,경도 형식도 가능합니다.",
  consciousness: "환자는 의식이 있나요?",
  breathing: "호흡 상태는 어떤가요?",
  bleeding: "출혈이 있나요?",
  symptom: "현재 가장 중요한 증상을 입력해주세요.",
  urgency: "긴급도를 선택해주세요. 현장 판단을 우선하며 참고용으로만 사용합니다.",
};

const choices: Partial<Record<Step, string[]>> = {
  consciousness: ["의식 있음", "의식 없음", "확인 불가"],
  breathing: ["정상 호흡", "호흡 곤란", "호흡 없음", "확인 불가"],
  bleeding: ["출혈 있음", "출혈 없음", "확인 불가"],
  urgency: ["Level 1", "Level 2", "Level 3", "Level 4"],
};

export default function ChatIntake({ onCompleted, disabled = false }: Props) {
  const [step, setStep] = useState<Step>("location");
  const [value, setValue] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 1, role: "assistant", text: "음성 대신 채팅으로 신고 내용을 순서대로 확인하겠습니다." },
    { id: 2, role: "assistant", text: prompts.location },
  ]);
  const [draft, setDraft] = useState<Partial<CreatePatientEvent>>({ symptoms: [] });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nextStep = useMemo(() => {
    const order: Step[] = ["location", "consciousness", "breathing", "bleeding", "symptom", "urgency"];
    return order[order.indexOf(step) + 1];
  }, [step]);

  async function submitAnswer(answer = value): Promise<void> {
    const trimmed = answer.trim();
    if (!trimmed || submitting || disabled) return;
    setError(null);
    setMessages((current) => [...current, { id: Date.now(), role: "user", text: trimmed }]);
    setValue("");

    if (step === "location") {
      const coordinate = trimmed.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
      if (coordinate) {
        await moveNext({ location: { latitude: Number(coordinate[1]), longitude: Number(coordinate[2]), address_text: null } });
        return;
      }
      try {
        const location = await geocodeAddress(trimmed);
        await moveNext({ location: { latitude: location.latitude, longitude: location.longitude, address_text: location.address } });
      } catch (locationError) {
        const message = locationError instanceof ApiError
          ? `${locationError.code}: ${locationError.message}`
          : "주소 좌표를 확인하지 못했습니다.";
        setError(message);
        setMessages((current) => [
          ...current,
          {
            id: Date.now() + 1,
            role: "assistant",
            text: `${message} 주소를 다시 입력하거나 위도,경도 형식으로 입력해주세요.`,
          },
        ]);
      }
      return;
    }

    if (step === "symptom") {
      try {
        const assisted = await assistPatientText(trimmed);
        const symptoms = assisted.symptoms.length > 0
          ? assisted.symptoms
          : [{ code: "CHAT_SYMPTOM", label: trimmed, confidence: null }];
        if (assisted.warnings.length > 0) {
          setMessages((current) => [
            ...current,
            { id: Date.now() + 1, role: "assistant", text: assisted.warnings.join(" ") },
          ]);
        }
        await moveNext({ symptoms });
      } catch (assistError) {
        const message = assistError instanceof ApiError
          ? `AI assist unavailable: ${assistError.code}`
          : "AI assist unavailable; the entered symptom will be kept for human review.";
        setMessages((current) => [...current, { id: Date.now() + 1, role: "assistant", text: message }]);
        await moveNext({ symptoms: [{ code: "CHAT_SYMPTOM", label: trimmed, confidence: null }] });
      }
      return;
    }
    const field = step === "consciousness" ? "consciousness_status" : step === "breathing" ? "breathing_status" : step === "bleeding" ? "bleeding_status" : "urgency_level";
    await moveNext({ [field]: trimmed } as Partial<CreatePatientEvent>);
  }

  async function moveNext(update: Partial<CreatePatientEvent>): Promise<void> {
    const updated = { ...draft, ...update };
    setDraft(updated);
    if (nextStep) {
      setStep(nextStep);
      setMessages((current) => [...current, { id: Date.now() + 2, role: "assistant", text: prompts[nextStep] }]);
      return;
    }
    await finalize(updated);
  }

  async function finalize(completed: Partial<CreatePatientEvent>): Promise<void> {
    const location = completed.location;
    if (!location || location.latitude === null || location.longitude === null) {
      const message = "환자 위치 좌표가 확인되지 않아 등록을 진행할 수 없습니다.";
      setError(message);
      setMessages((current) => [...current, { id: Date.now(), role: "assistant", text: message }]);
      return;
    }
    setSubmitting(true);
    const incidentId = `CHAT-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}-${Math.floor(Math.random() * 900 + 100)}`;
    const event: CreatePatientEvent = {
      incident_id: incidentId,
      observed_at: new Date().toISOString(),
      location,
      symptoms: completed.symptoms ?? [],
      consciousness_status: completed.consciousness_status ?? null,
      breathing_status: completed.breathing_status ?? null,
      bleeding_status: completed.bleeding_status ?? null,
      urgency_level: completed.urgency_level ?? null,
      source: { model_name: "chat-intake", model_version: "manual-v1" },
    };
    try {
      const patient = await createPatient(event);
      setMessages((current) => [...current, { id: Date.now(), role: "assistant", text: "환자 정보가 등록되었습니다. 주변 병원과 추천 상태를 확인합니다." }]);
      try {
        await onCompleted(patient);
      } catch (dashboardError) {
        const message = dashboardError instanceof ApiError
          ? `환자 정보는 등록됐지만 후속 조회에 실패했습니다: ${dashboardError.code}`
          : "환자 정보는 등록됐지만 병원·지도 후속 조회에 실패했습니다.";
        setError(message);
        setMessages((current) => [...current, { id: Date.now(), role: "assistant", text: message }]);
      }
    } catch (submissionError) {
      const message = submissionError instanceof ApiError ? `${submissionError.code}: ${submissionError.message}` : "환자 정보 등록에 실패했습니다.";
      setError(message);
      setMessages((current) => [...current, { id: Date.now(), role: "assistant", text: message }]);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="chat-card">
      <div className="section-heading"><div><span className="eyebrow">VOICE INPUT PAUSED</span><h2>상황 전달 채팅</h2></div><span className="status-pill">단계 {step === "location" ? 1 : step === "consciousness" ? 2 : step === "breathing" ? 3 : step === "bleeding" ? 4 : step === "symptom" ? 5 : 6} / 6</span></div>
      <div className="chat-messages" aria-live="polite">
        {messages.map((message) => <div className={`chat-bubble ${message.role}`} key={message.id}>{message.text}</div>)}
      </div>
      {choices[step] && <div className="choice-row">{choices[step]?.map((choice) => <button className="choice-button" key={choice} onClick={() => void submitAnswer(choice)} disabled={submitting || disabled}>{choice}</button>)}</div>}
      <form className="chat-input-row" onSubmit={(event) => { event.preventDefault(); void submitAnswer(); }}>
        <input value={value} onChange={(event) => setValue(event.target.value)} placeholder={step === "symptom" ? "예: 가슴 통증과 호흡 곤란" : "답변을 입력하세요"} disabled={submitting || disabled} />
        <button className="primary-button" type="submit" disabled={!value.trim() || submitting || disabled}>{submitting ? "등록 중" : "전송"}</button>
      </form>
      {error && <p className="error-text">{error}</p>}
      <p className="muted-note">의료진·구급대원의 판단을 대체하지 않는 의사결정 지원용 입력입니다.</p>
    </section>
  );
}
