import { MOCK_REVIEW } from "@/mocks/review";
import { summarizeReview } from "./reviewSummary";

describe("summarizeReview", () => {
  it("describes non-success states", () => {
    expect(summarizeReview({ status: "idle" })).toBe("No review yet");
    expect(summarizeReview({ status: "loading" })).toBe("Reviewing…");
    expect(summarizeReview({ status: "error", message: "x" })).toBe("Review failed");
  });

  it("describes a clean review", () => {
    const result = { ...MOCK_REVIEW, issues: [] };
    expect(summarizeReview({ status: "success", result })).toBe("No issues found");
  });

  it("lists the score and severity counts in severity order", () => {
    expect(summarizeReview({ status: "success", result: MOCK_REVIEW })).toBe(
      "Score 4 out of 10, 2 errors, 2 warnings, 1 info, 1 suggestion",
    );
  });
});
