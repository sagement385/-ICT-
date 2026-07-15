type Props = { status: "fresh" | "stale" | "unknown"; reason?: string | null };

export default function DataFreshnessBadge({ status, reason }: Props) {
  const label = status === "fresh" ? "최신 확인" : status === "stale" ? "오래된 데이터" : "최신성 확인 불가";
  return <span className={`freshness freshness-${status}`} title={reason ?? undefined}>● {label}</span>;
}
