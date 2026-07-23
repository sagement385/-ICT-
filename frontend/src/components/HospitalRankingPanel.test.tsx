import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  hospitalCandidateExample,
  hospitalRouteExample,
} from "../test/fixtures/contract-examples";
import HospitalRankingPanel from "./HospitalRankingPanel";

describe("HospitalRankingPanel", () => {
  it("labels source-backed hospitals as unranked candidates", () => {
    render(
      <HospitalRankingPanel
        recommendation={null}
        nearbyHospitals={[hospitalCandidateExample]}
        routes={[hospitalRouteExample]}
        loading={false}
        notice={null}
        selectedHospitalId={hospitalCandidateExample.hospital_id}
        onSelectHospital={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("주변 응급기관 후보")).toBeInTheDocument();
    expect(screen.getByText("순위 없음")).toBeInTheDocument();
    expect(screen.getByText(/5분 · 1.2km · 실시간 호출/)).toBeInTheDocument();
    expect(screen.queryByText(/정책 점수/)).not.toBeInTheDocument();
  });
});
