import type { ReviewState } from "@/types/review";

import type { MockOutcome } from "@/api/mockApi";

const STATUS_TEXT: Record<ReviewState["status"], string> = {
  idle: "Ready",
  loading: "Reviewing…",
  success: "Review complete",
  error: "Review failed",
};

type StatusBarProps = {
  status: ReviewState["status"];
  outcome: MockOutcome;
  onOutcomeChange: (outcome: MockOutcome) => void;
};

export function StatusBar({ status, outcome, onOutcomeChange }: StatusBarProps) {
  return (
    <footer className="flex h-9 shrink-0 items-center gap-4 border-t border-ink-700 bg-ink-900 px-4 text-xs text-fg-muted">
      <span role="status">{STATUS_TEXT[status]}</span>
      <span className="hidden sm:inline">Model: not connected (mock data)</span>
      <label className="ml-auto flex items-center gap-2">
        Next mock review
        <select
          value={outcome}
          onChange={(e) => onOutcomeChange(e.target.value as MockOutcome)}
          className="rounded border border-ink-700 bg-ink-800 px-1.5 py-0.5 text-fg"
        >
          <option value="issues">finds issues</option>
          <option value="clean">finds nothing</option>
          <option value="error">fails</option>
        </select>
      </label>
    </footer>
  );
}
