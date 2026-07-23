import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ChatIntake from "./ChatIntake";

vi.mock("../hooks/useEmergencyData", () => ({
  useCreatePatient: () => ({ mutateAsync: vi.fn() }),
  useAssistPatient: () => ({ mutateAsync: vi.fn() }),
  useGeocodeAddress: () => ({ mutateAsync: vi.fn() }),
}));

describe("ChatIntake", () => {
  it("accepts an explicit coordinate pair and advances without geocoding", async () => {
    render(<ChatIntake onCompleted={vi.fn()} />);
    const input = screen.getByPlaceholderText("답변을 입력하세요");
    fireEvent.change(input, { target: { value: "36.0,127.0" } });
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(await screen.findByText("환자는 의식이 있나요?")).toBeInTheDocument();
    expect(screen.getByText("단계 2 / 7")).toBeInTheDocument();
  });
});
