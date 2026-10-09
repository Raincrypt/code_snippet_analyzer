import type { ReviewState } from "@/types/review";
import { countBySeverity } from "./findings";
import { SEVERITY_ORDER, SEVERITY_STYLES } from "./severity";

/** One-line, screen-reader-friendly description of the review state. */
export function summarizeReview(review: ReviewState): string {
  switch (review.status) {
    case "idle":
      return "No review yet";
    case "loading":
      return "Reviewing…";
    case "error":
      return "Review failed";
    case "success": {
      const { issues, score, verdict } = review.result;
      if (verdict === "not-assessed") return "Not assessed";
      if (issues.length === 0) return "No issues found";
      const counts = countBySeverity(issues);
      const parts = SEVERITY_ORDER.filter((sev) => counts[sev] > 0).map(
        (sev) =>
          `${counts[sev]} ${SEVERITY_STYLES[sev].label.toLowerCase()}${counts[sev] > 1 ? "s" : ""}`,
      );
      return `Score ${score} out of 10, ${parts.join(", ")}`;
    }
  }
}
