import type { ReviewState } from "@/types/review";
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
      const { issues, score } = review.result;
      if (issues.length === 0) return "No issues found";
      const counts = SEVERITY_ORDER.flatMap((sev) => {
        const n = issues.filter((i) => i.severity === sev).length;
        return n > 0 ? [`${n} ${SEVERITY_STYLES[sev].label.toLowerCase()}${n > 1 ? "s" : ""}`] : [];
      });
      return `Score ${score} out of 10, ${counts.join(", ")}`;
    }
  }
}
