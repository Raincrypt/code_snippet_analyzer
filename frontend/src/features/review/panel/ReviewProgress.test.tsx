import { act, render, screen } from "@testing-library/react";
import { SLOW_AFTER_MS, STAGE_LABELS, ReviewProgress } from "./ReviewProgress";

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

  it("reassures the person only when the review is taking a while", () => {
    vi.useFakeTimers();
    try {
      render(<ReviewProgress stage="analyse" />);
      expect(screen.queryByText(/still working/i)).not.toBeInTheDocument();
      act(() => {
        vi.advanceTimersByTime(SLOW_AFTER_MS);
      });
      expect(screen.getByText(/still working/i)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});
