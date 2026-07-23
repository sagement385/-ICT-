import type { RoutingStatus } from "../api/routing";
import type { DataSourceStatus, SystemStatus } from "../api/status";

type Props = {
  status: SystemStatus | null;
  dataSources: DataSourceStatus[];
  routing: RoutingStatus | null;
  candidateCount: number;
  routeCount: number;
};

function relativeTime(value: string | null | undefined): string {
  if (!value) return "수집 이력 없음";
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return "1분 이내";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

function sourceLabel(sourceName: string): string {
  const labels: Record<string, string> = {
    "hira-hospital-info": "HIRA 병원 기본정보",
    "hira-hospital-detail": "HIRA 병원 상세정보",
    "nemc-emergency-institution-list": "NEMC 응급기관 목록",
    "nemc-emergency-medical": "NEMC 실시간 원본",
  };
  return labels[sourceName] ?? sourceName;
}

function sourceStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ready: "연결됨",
    configured: "설정됨",
    fresh: "최신",
    stale: "오래됨",
    unknown: "기준 미설정",
    unavailable: "데이터 없음",
    error: "최근 수집 실패",
    not_configured: "미설정",
  };
  return labels[status] ?? status;
}

function warningLabel(code: string): string {
  const labels: Record<string, string> = {
    RECOMMENDATION_POLICY_NOT_CONFIGURED: "승인된 추천 정책이 없습니다.",
    EMERGENCY_HOSPITAL_DETAIL_DATA_UNAVAILABLE: "응급기관 상세 데이터가 없습니다.",
    HOSPITAL_REALTIME_STATUS_PARTIAL: "일부 응급기관의 실시간 원본이 없습니다.",
    HOSPITAL_SOURCE_IDENTITIES_UNVERIFIED: "기관 식별자 자동 매칭에 사람 검토가 필요합니다.",
    HOSPITAL_STATUS_FRESHNESS_POLICY_NOT_CONFIGURED: "병원 상태 최신성 기준이 설정되지 않았습니다.",
    ROUTE_FRESHNESS_POLICY_NOT_CONFIGURED: "경로 최신성 기준이 설정되지 않았습니다.",
    NEMC_SYNC_INTERVAL_NOT_CONFIGURED: "NEMC 자동 수집 주기가 설정되지 않았습니다.",
    SPEECH_AI_NOT_CONFIGURED: "승인된 음성 AI provider가 없습니다.",
  };
  return labels[code] ?? code;
}

export default function OperationalStatusPanel({
  status,
  dataSources,
  routing,
  candidateCount,
  routeCount,
}: Props) {
  return (
    <section className="panel data-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">LIVE READINESS</span>
          <h2>데이터 연결 현황</h2>
        </div>
        <span className={`status-pill mode-${status?.mode ?? "unknown"}`}>
          {status?.mode === "operational" ? "운영 가능" : "제한 모드"}
        </span>
      </div>
      <div className="coverage-grid">
        <div><strong>{status?.data.emergency_institutions ?? "-"}</strong><span>공식 응급기관</span></div>
        <div><strong>{candidateCount}</strong><span>현재 반경 후보</span></div>
        <div><strong>{routeCount}</strong><span>확인된 실제 경로</span></div>
        <div><strong>{status?.data.active_policies ?? "-"}</strong><span>활성 추천 정책</span></div>
      </div>
      {status && status.data.source_identities_unverified > 0 ? (
        <p className="inline-warning" role="status">
          기관 식별자 자동 매칭 {status.data.source_identities_unverified}건은 운영 사용 전 사람의 검증이 필요합니다.
        </p>
      ) : null}
      <div className="source-list">
        {dataSources.map((source) => (
          <div className="data-status-row" key={source.source_name}>
            <span>{sourceLabel(source.source_name)}</span>
            <div>
              <strong className={`source-${source.status}`}>{sourceStatusLabel(source.status)}</strong>
              <small>{relativeTime(source.last_success_at)}</small>
            </div>
          </div>
        ))}
        <div className="data-status-row">
          <span>Naver Directions</span>
          <div>
            <strong className={routing?.configured ? "source-ready" : "source-error"}>
              {routing?.configured ? "설정됨" : "미설정"}
            </strong>
            <small>
              {routing?.calls_limit === null
                ? `${routing.calls_used}회 사용 · 앱 제한 없음`
                : `${routing?.calls_used ?? 0}/${routing?.calls_limit ?? "-"}회`}
            </small>
          </div>
        </div>
      </div>
      {status?.warnings.length ? (
        <details className="warning-details">
          <summary>운영 경고 {status.warnings.length}건</summary>
          <ul>
            {status.warnings.map((warning) => (
              <li key={warning}>
                <span>{warningLabel(warning)}</span>
                <code>{warning}</code>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
