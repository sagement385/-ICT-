import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  dataSourceStatusExample,
  routingStatusExample,
  systemStatusExample,
} from "../test/fixtures/contract-examples";
import OperationalStatusPanel from "./OperationalStatusPanel";

describe("OperationalStatusPanel", () => {
  it("explains limited readiness and unverified identities in Korean", () => {
    render(
      <OperationalStatusPanel
        status={systemStatusExample}
        dataSources={[dataSourceStatusExample]}
        routing={routingStatusExample}
        candidateCount={1}
        routeCount={0}
      />,
    );

    expect(screen.getByText("제한 모드")).toBeInTheDocument();
    expect(screen.getByText(/기관 식별자 자동 매칭 1건/)).toBeInTheDocument();
    expect(screen.getByText("기준 미설정")).toBeInTheDocument();
    expect(screen.getByText("운영 경고 2건")).toBeInTheDocument();
  });
});
