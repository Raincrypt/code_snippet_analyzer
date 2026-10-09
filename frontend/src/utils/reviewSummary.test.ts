import { CLEAN_REVIEW, MOCK_REVIEW } from "@/mocks/review";
import { summarizeReview } from "./reviewSummary";

describe("summarizeReview", () => {
  it("describes non-success states", () => {
    expect(summarizeReview({ status: "idle" })).toBe("No review yet");
    expect(summarizeReview({ status: "loading" })).toBe("Reviewing…");
    expect(summarizeReview({ status: "error", message: "x" })).toBe("Review failed");
  });

  it("describes a clean review", () => {
    expect(summarizeReview({ status: "success", result: CLEAN_REVIEW })).toBe("No issues found");
  });

  it("says when the code was not assessed", () => {
    const result = { ...MOCK_REVIEW, verdict: "not-assessed" as const };
    expect(summarizeReview({ status: "success", result })).toBe("Not assessed");
  });

  it("lists the score and severity counts in severity order", () => {
    expect(summarizeReview({ status: "success", result: MOCK_REVIEW })).toBe(
      "Score 6 out of 10, 1 error, 3 warnings, 1 info, 1 suggestion",
    );
  });
});
