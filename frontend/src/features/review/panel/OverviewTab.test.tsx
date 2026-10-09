import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CLEAN_REVIEW, MOCK_REVIEW } from "@/mocks/review";
import type { ReviewResult } from "@/types/review";
import { OverviewTab } from "./OverviewTab";

function setup(result: ReviewResult = MOCK_REVIEW) {
  const onLocate = vi.fn();
  const onOpenTab = vi.fn();
  render(<OverviewTab result={result} onLocate={onLocate} onOpenTab={onOpenTab} />);
  return { onLocate, onOpenTab };
}

describe("OverviewTab", () => {
  it("leads with the verdict, score and summary", () => {
    setup();
    expect(screen.getByText("Needs work")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Score 6 out of 10" })).toBeInTheDocument();
    expect(screen.getByText(/Both functions return correct answers/)).toBeInTheDocument();
  });

  it("says what the code does", () => {
    setup();
    expect(screen.getByText("What this code does")).toBeInTheDocument();
    expect(screen.getByText(/hand-written sort/)).toBeInTheDocument();
  });

  it("puts complexity and the algorithm at a glance", () => {
    setup();
    const glance = screen.getByText("Complexity at a glance").closest("section")!;
    expect(glance).toHaveTextContent("O(n²)");
    expect(glance).toHaveTextContent("O(1)");
    expect(glance).toHaveTextContent("Bubble sort, Brute-force pairwise duplicate check");
  });

  it("opens the complexity tab from the glance", async () => {
    const { onOpenTab } = setup();
    await userEvent.click(screen.getByRole("button", { name: "See details" }));
    expect(onOpenTab).toHaveBeenCalledWith("complexity");
  });

  it("lists the priority fixes in order and jumps to the finding", async () => {
    const { onLocate, onOpenTab } = setup();
    const list = screen.getByText("Fix these first").closest("section")!;
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("topScores reorders the caller's array");
    await userEvent.click(within(items[1]!).getByRole("button"));
    expect(onLocate).toHaveBeenCalledWith(expect.objectContaining({ id: "f3" }));
    expect(onOpenTab).toHaveBeenCalledWith("findings");
  });

  it("scores each area with a reason", () => {
    setup();
    expect(screen.getByRole("img", { name: "Performance 4 out of 10" })).toBeInTheDocument();
    expect(screen.getByText(/Both helpers do quadratic work/)).toBeInTheDocument();
  });

  it("includes positives and the limits of the review", () => {
    setup();
    expect(screen.getByText(/The comment states what the function returns/)).toBeInTheDocument();
    expect(screen.getByText("Limits of this review")).toBeInTheDocument();
  });

  it("leaves out sections that have nothing to show", () => {
    setup(CLEAN_REVIEW);
    expect(screen.queryByText("Fix these first")).not.toBeInTheDocument();
    expect(screen.queryByText("Limits of this review")).not.toBeInTheDocument();
    expect(screen.getByText("Looks good")).toBeInTheDocument();
  });
});
