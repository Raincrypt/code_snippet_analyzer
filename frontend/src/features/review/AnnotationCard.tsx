import { useEffect, useRef, useState } from "react";
import {
  Bug,
  ChevronDown,
  Gauge,
  ListChecks,
  MessageSquareText,
  Paintbrush,
  ShieldAlert,
} from "lucide-react";
import type { Category, CodeIssue } from "@/types/review";
import { SEVERITY_STYLES, formatLineRange } from "@/utils/severity";
import { Badge } from "@/components/ui/Badge";

const CATEGORY_ICONS: Record<Category, typeof Bug> = {
  bug: Bug,
  security: ShieldAlert,
  performance: Gauge,
  style: Paintbrush,
  "best-practice": ListChecks,
};

type AnnotationCardProps = {
  issue: CodeIssue;
  onAsk: (issue: CodeIssue) => void;
  /** Jump to this finding's lines in the editor. */
  onLocate: (issue: CodeIssue) => void;
  /** True while this finding is the one selected in the editor. */
  active?: boolean;
  index?: number;
};

export function AnnotationCard({
  issue,
  onAsk,
  onLocate,
  active = false,
  index = 0,
}: AnnotationCardProps) {
  const [showFix, setShowFix] = useState(false);
  const ref = useRef<HTMLElement>(null);

  // When selected from the editor, bring the card into view.
  useEffect(() => {
    if (active) ref.current?.scrollIntoView?.({ block: "nearest" });
  }, [active]);
  const CategoryIcon = CATEGORY_ICONS[issue.category];
  const styles = SEVERITY_STYLES[issue.severity];

  return (
    <article
      ref={ref}
      aria-current={active ? "true" : undefined}
      className={`rounded-md border border-l-4 border-ink-700 p-4 motion-safe:animate-note-in ${
        active ? "bg-ink-800 ring-1 ring-fg-muted/40" : "bg-ink-900"
      } ${styles.rail}`}
      style={{ animationDelay: `${index * 70}ms` }}
    >
      <header className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onLocate(issue)}
          title="Show in editor"
          className="rounded bg-ink-800 px-1.5 py-0.5 font-mono text-xs text-fg-muted hover:bg-ink-700 hover:text-fg"
        >
          {formatLineRange(issue.line, issue.endLine)}
        </button>
        <Badge severity={issue.severity} />
        <span className="ml-auto inline-flex items-center gap-1 text-xs text-fg-muted">
          <CategoryIcon className="size-3.5" aria-hidden />
          {issue.category}
        </span>
      </header>

      <h3 className="mt-2.5 text-[0.95rem] font-semibold text-fg">{issue.title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-fg-muted">{issue.description}</p>

      {showFix && issue.suggestion && (
        <pre
          id={`fix-${index}`}
          className="mt-3 overflow-x-auto rounded bg-ink-950 p-3 font-mono text-xs leading-relaxed text-fg"
        >
          {issue.suggestion}
        </pre>
      )}

      <div className="mt-3 flex items-center gap-1">
        {issue.suggestion && (
          <button
            type="button"
            onClick={() => setShowFix((v) => !v)}
            aria-expanded={showFix}
            aria-controls={`fix-${index}`}
            className="inline-flex h-8 items-center gap-1 rounded px-2 text-xs font-medium text-fg-muted hover:bg-ink-800 hover:text-fg"
          >
            <ChevronDown
              className={`size-4 motion-safe:transition-transform ${showFix ? "rotate-180" : ""}`}
              aria-hidden
            />
            {showFix ? "Hide fix" : "Show fix"}
          </button>
        )}
        <button
          type="button"
          onClick={() => onAsk(issue)}
          className="inline-flex h-8 items-center gap-1.5 rounded px-2 text-xs font-medium text-fg-muted hover:bg-ink-800 hover:text-fg"
        >
          <MessageSquareText className="size-4" aria-hidden />
          Ask about this
        </button>
      </div>
    </article>
  );
}
