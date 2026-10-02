import { ChevronUp } from "lucide-react";
import type { CodeIssue, ReviewState } from "@/types/review";
import { summarizeReview } from "@/utils/reviewSummary";
import { SEVERITY_ORDER, SEVERITY_STYLES, scoreColor } from "@/utils/severity";
import { ResultsPanel } from "./ResultsPanel";

type ResultsSectionProps = {
  review: ReviewState;
  open: boolean;
  onToggle: () => void;
  /** Total height (header + body) in px while open. */
  height: number;
  onAsk: (issue: CodeIssue) => void;
  onLocate: (issue: CodeIssue) => void;
  activeKey: string | null;
  onRetry: () => void;
};

/** Collapsible bar: a one-line summary while closed, the full findings while open. */
export function ResultsSection({
  review,
  open,
  onToggle,
  height,
  onAsk,
  onLocate,
  activeKey,
  onRetry,
}: ResultsSectionProps) {
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
          <InlineSummary review={review} />
        </button>
      </h2>

      {/* Announces results even while the panel is collapsed. */}
      <span role="status" className="sr-only">
        {summarizeReview(review)}
      </span>

      <div id="review-results" hidden={!open} className="min-h-0 flex-1 overflow-y-auto">
        <ResultsPanel
          review={review}
          onAsk={onAsk}
          onLocate={onLocate}
          activeKey={activeKey}
          onRetry={onRetry}
        />
      </div>
    </section>
  );
}

function InlineSummary({ review }: { review: ReviewState }) {
  if (review.status === "success" && review.result.issues.length > 0) {
    const { score, issues } = review.result;
    return (
      <span aria-hidden className="flex items-center gap-3 text-xs text-fg-muted">
        <span className={`font-semibold tabular-nums ${scoreColor(score)}`}>{score}/10</span>
        {SEVERITY_ORDER.map((sev) => {
          const count = issues.filter((i) => i.severity === sev).length;
          if (count === 0) return null;
          return (
            <span key={sev} className="inline-flex items-center gap-1 tabular-nums">
              <span className={`size-2 rounded-full ${SEVERITY_STYLES[sev].dot}`} />
              {count}
            </span>
          );
        })}
      </span>
    );
  }
  return (
    <span aria-hidden className="truncate text-xs text-fg-muted">
      {summarizeReview(review)}
    </span>
  );
}
