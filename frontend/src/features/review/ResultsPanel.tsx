import type { ReactNode } from "react";
import { CircleCheck, FileSearch, TriangleAlert } from "lucide-react";
import type { CodeIssue, ReviewResult, ReviewState } from "@/types/review";
import { SEVERITY_ORDER, SEVERITY_STYLES } from "@/utils/severity";
import { Button } from "@/components/ui/Button";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { issueKey } from "@/utils/issues";
import { AnnotationCard } from "./AnnotationCard";

type ResultsPanelProps = {
  review: ReviewState;
  onAsk: (issue: CodeIssue) => void;
  onLocate: (issue: CodeIssue) => void;
  activeKey: string | null;
  onRetry: () => void;
};

export function ResultsPanel({ review, onAsk, onLocate, activeKey, onRetry }: ResultsPanelProps) {
  return (
    <div className="p-4">
      {review.status === "idle" && (
        <Message icon={<FileSearch className="size-6" />} title="Nothing reviewed yet">
          Paste code into the editor and choose Review. Findings will appear here, sorted by line.
        </Message>
      )}
      {review.status === "loading" && <Skeleton />}
      {review.status === "error" && (
        <Message
          icon={<TriangleAlert className="size-6 text-sev-error" />}
          title="The review didn’t finish"
        >
          {review.message}
          <Button variant="ghost" className="mt-3" onClick={onRetry}>
            Try again
          </Button>
        </Message>
      )}
      {review.status === "success" && (
        <Results result={review.result} onAsk={onAsk} onLocate={onLocate} activeKey={activeKey} />
      )}
    </div>
  );
}

type ResultsProps = {
  result: ReviewResult;
  onAsk: (issue: CodeIssue) => void;
  onLocate: (issue: CodeIssue) => void;
  activeKey: string | null;
};

function Results({ result, onAsk, onLocate, activeKey }: ResultsProps) {
  if (result.issues.length === 0) {
    return (
      <Message icon={<CircleCheck className="size-6 text-good" />} title="No issues found">
        {result.summary}
      </Message>
    );
  }
  const sorted = [...result.issues].sort((a, b) => a.line - b.line);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <ScoreRing score={result.score} />
        <div className="min-w-0">
          <p className="max-w-prose text-sm leading-relaxed text-fg">{result.summary}</p>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-muted">
            {SEVERITY_ORDER.map((sev) => {
              const count = result.issues.filter((i) => i.severity === sev).length;
              if (count === 0) return null;
              return (
                <li key={sev} className="inline-flex items-center gap-1.5">
                  <span className={`size-2 rounded-full ${SEVERITY_STYLES[sev].dot}`} aria-hidden />
                  {count} {SEVERITY_STYLES[sev].label.toLowerCase()}
                  {count > 1 ? "s" : ""}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <div className="space-y-3">
        {sorted.map((issue, i) => (
          <AnnotationCard
            key={issueKey(issue)}
            issue={issue}
            onAsk={onAsk}
            onLocate={onLocate}
            active={issueKey(issue) === activeKey}
            index={i}
          />
        ))}
      </div>
      {result.positives.length > 0 && (
        <ul className="space-y-1 border-t border-ink-700 pt-3 text-sm text-fg-muted">
          {result.positives.map((p) => (
            <li key={`${p.line}-${p.comment}`} className="flex gap-2">
              <CircleCheck className="mt-0.5 size-4 shrink-0 text-good" aria-hidden />
              <span>
                <span className="font-mono text-xs">L{p.line}</span> {p.comment}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Message({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex h-full max-w-sm flex-col items-center justify-center gap-2 py-8 text-center">
      <div className="text-fg-muted">{icon}</div>
      <h3 className="font-semibold text-fg">{title}</h3>
      <div className="flex flex-col items-center text-sm leading-relaxed text-fg-muted">
        {children}
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Reviewing your code">
      <div className="flex items-center gap-4">
        <div className="size-16 rounded-full bg-ink-800 motion-safe:animate-pulse" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-full rounded bg-ink-800 motion-safe:animate-pulse" />
          <div className="h-3 w-2/3 rounded bg-ink-800 motion-safe:animate-pulse" />
        </div>
      </div>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-24 rounded-md border border-ink-700 bg-ink-900 motion-safe:animate-pulse"
        />
      ))}
    </div>
  );
}
