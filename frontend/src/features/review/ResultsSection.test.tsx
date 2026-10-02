import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MOCK_REVIEW } from "@/mocks/review";
import type { ReviewState } from "@/types/review";
import { ResultsSection } from "./ResultsSection";

const success: ReviewState = { status: "success", result: MOCK_REVIEW };

function setup(open: boolean, review: ReviewState = success) {
  const onToggle = vi.fn();
  render(
    <ResultsSection
      review={review}
      open={open}
      onToggle={onToggle}
      height={320}
      onAsk={() => {}}
      onLocate={() => {}}
      activeKey={null}
      onRetry={() => {}}
    />,
  );
  return { onToggle, button: screen.getByRole("button", { name: /review/i }) };
}

describe("ResultsSection", () => {
  it("hides the findings while collapsed but still announces the summary", () => {
    const { button } = setup(false);
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("SQL injection through string concatenation")).not.toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Score 4 out of 10");
  });

  it("shows the findings when open", () => {
    const { button } = setup(true);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("SQL injection through string concatenation")).toBeVisible();
  });

  it("asks to toggle when the header is clicked", async () => {
    const { button, onToggle } = setup(false);
    await userEvent.click(button);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
