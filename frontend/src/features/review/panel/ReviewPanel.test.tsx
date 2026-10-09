import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CLEAN_REVIEW, MOCK_REVIEW } from "@/mocks/review";
import type { ReviewState } from "@/types/review";
import { ReviewPanel } from "./ReviewPanel";

function setup(review: ReviewState, props: Partial<Parameters<typeof ReviewPanel>[0]> = {}) {
  const handlers = {
    onAsk: vi.fn(),
    onLocate: vi.fn(),
    onLocateLines: vi.fn(),
    onRetry: vi.fn(),
  };
  const all = { review, stale: false, activeKey: null, ...handlers, ...props };
  const view = render(<ReviewPanel {...all} />);
  return {
    ...handlers,
    rerender: (next: Partial<typeof all>) => view.rerender(<ReviewPanel {...all} {...next} />),
  };
}

const success: ReviewState = { status: "success", result: MOCK_REVIEW };

describe("ReviewPanel states", () => {
  it("explains what a review will contain before one is run", () => {
    setup({ status: "idle" });
    expect(screen.getByText("Nothing reviewed yet")).toBeInTheDocument();
    expect(screen.getByText(/time complexity and any algorithms/)).toBeInTheDocument();
  });

  it("shows progress while reviewing", () => {
    setup({ status: "loading", stage: "complexity" });
    expect(screen.getByRole("status", { name: "Review progress" })).toBeInTheDocument();
    expect(
      screen.getByText("Working out time complexity and algorithms").closest("li"),
    ).toHaveAttribute("aria-current", "step");
  });

  it("offers a retry after an error", async () => {
    const { onRetry } = setup({ status: "error", message: "It timed out." });
    expect(screen.getByText("It timed out.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

describe("ReviewPanel result", () => {
  it("opens on the overview, with four tabs", () => {
    setup(success);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual([
      "Overview",
      "Findings6",
      "Complexity",
      "Metrics",
    ]);
  });

  it("switches between the sections", async () => {
    setup(success);
    await userEvent.click(screen.getByRole("tab", { name: /Findings/ }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Showing 6 of 6 findings");
    await userEvent.click(screen.getByRole("tab", { name: "Complexity" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Bubble sort");
    await userEvent.click(screen.getByRole("tab", { name: "Metrics" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Measured directly from your code");
  });

  it("jumps to the findings tab when the editor selects a finding", () => {
    const { rerender } = setup(success);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    rerender({ activeKey: "f2" });
    expect(screen.getByRole("tab", { name: /Findings/ })).toHaveAttribute("aria-selected", "true");
  });

  it("warns when the code was edited after the review", () => {
    setup(success, { stale: true });
    expect(screen.getByText(/earlier version of your code/)).toBeInTheDocument();
  });

  it("does not warn when the code is unchanged", () => {
    setup(success);
    expect(screen.queryByText(/earlier version of your code/)).not.toBeInTheDocument();
  });

  it("shows a clean review without findings", async () => {
    setup({ status: "success", result: CLEAN_REVIEW });
    await userEvent.click(screen.getByRole("tab", { name: /Findings/ }));
    expect(screen.getByText("No issues found")).toBeInTheDocument();
  });

  it("is honest when the code was not analysed", () => {
    const result = {
      ...MOCK_REVIEW,
      verdict: "not-assessed" as const,
      score: null,
      scoreBreakdown: null,
      issues: [],
      priorityFixes: [],
      complexity: null,
      algorithms: [],
      summary: "No AI reviewer is connected yet.",
    };
    setup({ status: "success", result });
    expect(screen.getByText("Not analysed")).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.getByText("Total lines")).toBeInTheDocument();
  });
});
