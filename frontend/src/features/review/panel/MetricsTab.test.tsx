import { render, screen } from "@testing-library/react";
import { MOCK_REVIEW } from "@/mocks/review";
import { MetricsTab } from "./MetricsTab";

describe("MetricsTab", () => {
  it("shows every measured figure", () => {
    render(<MetricsTab metrics={MOCK_REVIEW.metrics} />);
    expect(screen.getByText("Total lines").nextElementSibling).toHaveTextContent("23");
    expect(screen.getByText("Functions").nextElementSibling).toHaveTextContent("2");
    expect(screen.getByText("Deepest nesting").nextElementSibling).toHaveTextContent("3");
    expect(screen.queryByText(/needs the code analyser/)).not.toBeInTheDocument();
  });

  it("says these are measured, not guessed", () => {
    render(<MetricsTab metrics={MOCK_REVIEW.metrics} />);
    expect(screen.getByText(/not estimated by AI/)).toBeInTheDocument();
  });

  it("shows a dash, with an explanation, for figures that were not measured", () => {
    const metrics = { ...MOCK_REVIEW.metrics, functionCount: null, maxNestingDepth: undefined };
    render(<MetricsTab metrics={metrics} />);
    expect(screen.getByText("Functions").nextElementSibling).toHaveTextContent("—");
    expect(screen.getByText(/needs the code analyser/)).toBeInTheDocument();
  });

  it("shows zero as a real value, not as missing", () => {
    render(<MetricsTab metrics={{ ...MOCK_REVIEW.metrics, commentLines: 0 }} />);
    expect(screen.getByText("Comment lines").nextElementSibling).toHaveTextContent("0");
  });
});
