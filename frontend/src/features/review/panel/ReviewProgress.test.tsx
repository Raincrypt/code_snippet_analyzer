import { render, screen } from "@testing-library/react";
import { STAGE_LABELS, ReviewProgress } from "./ReviewProgress";

describe("ReviewProgress", () => {
  it("lists every step", () => {
    render(<ReviewProgress stage={null} />);
    for (const label of Object.values(STAGE_LABELS)) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("marks earlier steps done, the current one active and later ones pending", () => {
    render(<ReviewProgress stage="analyse" />);
    const item = (stage: keyof typeof STAGE_LABELS) =>
      screen.getByText(STAGE_LABELS[stage]).closest("li")!;
    expect(item("prepare")).toHaveTextContent("(done)");
    expect(item("understand")).toHaveTextContent("(done)");
    expect(item("analyse")).toHaveAttribute("aria-current", "step");
    expect(item("complexity")).toHaveTextContent("(pending)");
    expect(item("verify")).toHaveTextContent("(pending)");
  });

  it("shows everything as pending before the first step starts", () => {
    render(<ReviewProgress stage={null} />);
    expect(screen.getAllByText("(pending)")).toHaveLength(5);
  });
});
