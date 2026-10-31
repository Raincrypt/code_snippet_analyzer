import type { MockOutcome } from "@/api/mockApi";
import type { ModelIndicator, ModelLevel } from "@/hooks/useModelStatus";
import type { ReviewState } from "@/types/review";

const DOT_COLOUR: Record<ModelLevel, string> = {
  ok: "bg-good",
  checking: "bg-sev-warning",
  warn: "bg-sev-warning",
  down: "bg-sev-error",
};

/** What the footer says about the review; nothing while idle (the dot shows readiness). */
const STATUS_TEXT: Record<ReviewState["status"], string | null> = {
  idle: null,
  loading: "Reviewing…",
  success: "Review complete",
  error: "Review failed",
};

type StatusBarProps = {
  status: ReviewState["status"];
  /** Which reviewer is behind the app, or null when unknown. */
  reviewerLabel: string | null;
  /** Whether the AI model is available: shown as a green, yellow or red dot after the label. */
  modelStatus?: ModelIndicator | null;
  /** Only given while working on the interface with the mock API. */
  mock?: { outcome: MockOutcome; onOutcomeChange: (outcome: MockOutcome) => void };
};

export function StatusBar({ status, reviewerLabel, modelStatus, mock }: StatusBarProps) {
  return (
    <footer className="flex h-9 shrink-0 items-center gap-4 border-t border-ink-700 bg-ink-900 px-4 text-xs text-fg-muted">
      {STATUS_TEXT[status] && <span role="status">{STATUS_TEXT[status]}</span>}
      {reviewerLabel && (
        <span
          className="hidden truncate sm:inline"
          title="The model name comes from the backend setting LLM_MODEL"
        >
          {reviewerLabel}
        </span>
      )}
      {modelStatus && (
        <span
          role="img"
          aria-label={modelStatus.text}
          title={modelStatus.text}
          data-level={modelStatus.level}
          className={`-ml-2 size-2.5 shrink-0 rounded-full ${DOT_COLOUR[modelStatus.level]}`}
        />
      )}
      {mock && (
        <label className="ml-auto flex items-center gap-2">
          Next mock review
          <select
            value={mock.outcome}
            onChange={(e) => mock.onOutcomeChange(e.target.value as MockOutcome)}
            className="rounded border border-ink-700 bg-ink-800 px-1.5 py-0.5 text-fg"
          >
            <option value="issues">finds issues</option>
            <option value="clean">finds nothing</option>
            <option value="error">fails</option>
          </select>
        </label>
      )}
    </footer>
  );
}
