import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MOCK_REVIEW } from "@/mocks/review";
import type { ReviewState } from "@/types/review";
import { ResultsSection } from "./ResultsSection";

const success: ReviewState = { status: "success", result: MOCK_REVIEW };

function setup(open: boolean, review: ReviewState = success, stale = false) {
  const onToggle = vi.fn();
  render(
    <ResultsSection
      review={review}
      open={open}
      onToggle={onToggle}
      height={320}
      stale={stale}
      onAsk={() => {}}
      onLocate={() => {}}
      onLocateLines={() => {}}
      activeKey={null}
      onRetry={() => {}}
    />,
  );
  return { onToggle, button: screen.getByRole("button", { name: /^review/i }) };
}

describe("ResultsSection", () => {
  it("hides the analysis while collapsed but still announces the summary", () => {
    const { button } = setup(false);
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("What this code does")).not.toBeVisible();
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("Score 6 out of 10");
  });

  it("shows the analysis when open", () => {
    const { button } = setup(true);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("What this code does")).toBeVisible();
  });

  it("asks to toggle when the header is clicked", async () => {
    const { button, onToggle } = setup(false);
    await userEvent.click(button);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("flags an out-of-date review in the collapsed bar and to screen readers", () => {
    setup(false, success, true);
    expect(screen.getByText("Out of date")).toBeInTheDocument();
    expect(screen.getAllByRole("status")[0]).toHaveTextContent("Out of date");
  });

  it("does not flag a current review", () => {
    setup(false);
    expect(screen.queryByText("Out of date")).not.toBeInTheDocument();
  });
});
