import { ChevronUp } from "lucide-react";
import type { CodeIssue, ReviewState } from "@/types/review";
import { countBySeverity } from "@/utils/findings";
import { summarizeReview } from "@/utils/reviewSummary";
import { SEVERITY_ORDER, SEVERITY_STYLES, scoreColor } from "@/utils/severity";
import { ReviewPanel } from "./panel/ReviewPanel";

type ResultsSectionProps = {
  review: ReviewState;
  open: boolean;
  onToggle: () => void;
  /** Total height (header + body) in px while open. */
  height: number;
  /** The code has been edited since the review was made. */
  stale: boolean;
  onAsk: (issue: CodeIssue) => void;
  onLocate: (issue: CodeIssue) => void;
  onLocateLines: (startLine: number, endLine: number) => void;
  activeKey: string | null;
  onRetry: () => void;
};

/** Collapsible bar: a one-line summary while closed, the full analysis while open. */
export function ResultsSection({
  review,
  open,
  onToggle,
  height,
  stale,
  onAsk,
  onLocate,
  onLocateLines,
  activeKey,
  onRetry,
}: ResultsSectionProps) {
  const announcement =
    summarizeReview(review) + (stale ? ". Out of date: the code has changed." : "");
  return (
    <section
      aria-label="Review results"
      className={`flex min-h-10 shrink flex-col bg-ink-950 ${open ? "" : "border-t border-ink-700"}`}
      style={open ? { flexBasis: height, flexGrow: 0 } : undefined}
    >
      <h2 className="text-sm">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-controls="review-results"
          className="flex h-10 w-full items-center gap-3 px-4 text-left hover:bg-ink-900"
        >
          <ChevronUp
            className={`size-4 shrink-0 text-fg-muted motion-safe:transition-transform ${open ? "rotate-180" : ""}`}
            aria-hidden
          />
          <span className="font-semibold">Review</span>
          <InlineSummary review={review} stale={stale} />
        </button>
      </h2>

      {/* Announces results even while the panel is collapsed. */}
      <span role="status" className="sr-only">
        {announcement}
      </span>

      <div id="review-results" hidden={!open} className="min-h-0 flex-1 overflow-y-auto">
        <ReviewPanel
          review={review}
          stale={stale}
          onAsk={onAsk}
          onLocate={onLocate}
          onLocateLines={onLocateLines}
          activeKey={activeKey}
          onRetry={onRetry}
        />
      </div>
    </section>
  );
}

function InlineSummary({ review, stale }: { review: ReviewState; stale: boolean }) {
  const staleTag = stale && (
    <span className="rounded bg-sev-warning/15 px-1.5 py-0.5 text-xs text-sev-warning">
      Out of date
    </span>
  );

  if (review.status === "success") {
    const { score, issues, verdict } = review.result;
    if (verdict !== "not-assessed" && score != null && issues.length > 0) {
      const counts = countBySeverity(issues);
      return (
        <span aria-hidden className="flex items-center gap-3 text-xs text-fg-muted">
          <span className={`font-semibold tabular-nums ${scoreColor(score)}`}>{score}/10</span>
          {SEVERITY_ORDER.filter((sev) => counts[sev] > 0).map((sev) => (
            <span key={sev} className="inline-flex items-center gap-1 tabular-nums">
              <span className={`size-2 rounded-full ${SEVERITY_STYLES[sev].dot}`} />
              {counts[sev]}
            </span>
          ))}
          {staleTag}
        </span>
      );
    }
  }
  return (
    <span aria-hidden className="flex items-center gap-3 truncate text-xs text-fg-muted">
      {summarizeReview(review)}
      {staleTag}
    </span>
  );
}
