import { useEffect, useRef } from "react";
import { ChevronDown, ExternalLink, MessageSquareText } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { CodeIssue } from "@/types/review";
import { SEVERITY_STYLES, formatLineRange } from "@/utils/severity";
import { CATEGORY_META, CONFIDENCE_LABELS, EFFORT_LABELS } from "./categories";
import { CodeBlock, CopyButton } from "./CodeBlock";
import { RichText } from "@/components/RichText";

type FindingCardProps = {
  issue: CodeIssue;
  open: boolean;
  onToggle: () => void;
  /** True while this finding is the one selected in the editor. */
  active?: boolean;
  /** Jump to this finding's lines in the editor. */
  onLocate: (issue: CodeIssue) => void;
  onAsk: (issue: CodeIssue) => void;
  index?: number;
};

function Field({ label, children }: { label: string; children: string }) {
  return (
    <div>
      <h5 className="mb-0.5 text-xs font-semibold text-fg-muted">{label}</h5>
      <p className="text-sm leading-relaxed text-fg">
        <RichText>{children}</RichText>
      </p>
    </div>
  );
}

export function FindingCard({
  issue,
  open,
  onToggle,
  active = false,
  onLocate,
  onAsk,
  index = 0,
}: FindingCardProps) {
  const ref = useRef<HTMLElement>(null);
  const styles = SEVERITY_STYLES[issue.severity];
  const { Icon, label: categoryLabel } = CATEGORY_META[issue.category];
  const bodyId = `finding-body-${issue.id}`;

  // When selected from the editor, bring the card into view.
  useEffect(() => {
    if (active) ref.current?.scrollIntoView?.({ block: "nearest" });
  }, [active]);

  return (
    <article
      ref={ref}
      aria-current={active ? "true" : undefined}
      className={`rounded-md border border-l-4 border-ink-700 motion-safe:animate-note-in ${
        active ? "bg-ink-800 ring-1 ring-fg-muted/40" : "bg-ink-900"
      } ${styles.rail}`}
      style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
    >
      <header className="flex items-start gap-2 p-3 pr-3">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-controls={bodyId}
          className="flex min-w-0 flex-1 items-start gap-2 rounded text-left"
        >
          <ChevronDown
            className={`mt-1 size-4 shrink-0 text-fg-muted motion-safe:transition-transform ${
              open ? "" : "-rotate-90"
            }`}
            aria-hidden
          />
          <span className="min-w-0">
            <span className="flex flex-wrap items-center gap-2">
              <Badge severity={issue.severity} />
              <span className="inline-flex items-center gap-1 text-xs text-fg-muted">
                <Icon className="size-3.5" aria-hidden />
                {categoryLabel}
              </span>
            </span>
            <h4 className="mt-1 text-[0.95rem] leading-snug font-semibold text-fg">
              {issue.title}
            </h4>
          </span>
        </button>
        <button
          type="button"
          onClick={() => onLocate(issue)}
          title="Show in editor"
          className="shrink-0 rounded bg-ink-800 px-1.5 py-0.5 font-mono text-xs text-fg-muted hover:bg-ink-700 hover:text-fg"
        >
          {formatLineRange(issue.line, issue.endLine ?? undefined)}
        </button>
      </header>

      <div id={bodyId} hidden={!open} className="space-y-3 px-4 pb-4 pl-9">
        <Field label="What's wrong">{issue.explanation}</Field>
        <Field label="Why it matters">{issue.impact}</Field>
        <CodeBlock label="The code" code={issue.evidence} startLine={issue.line} />

        {issue.fix && (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <h5 className="text-xs font-semibold text-fg-muted">Suggested fix</h5>
              <CopyButton text={issue.fix.after} label="Copy fix" />
            </div>
            <p className="text-sm leading-relaxed text-fg">
              <RichText>{issue.fix.description}</RichText>
            </p>
            {issue.fix.before && <CodeBlock label="Before" code={issue.fix.before} tone="remove" />}
            <CodeBlock label="After" code={issue.fix.after} tone="add" />
          </div>
        )}

        {issue.references.length > 0 && (
          <div>
            <h5 className="mb-1 text-xs font-semibold text-fg-muted">Learn more</h5>
            <ul className="space-y-1 text-sm">
              {issue.references.map((ref) => (
                <li key={ref.label}>
                  {ref.url ? (
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sev-info underline-offset-2 hover:underline"
                    >
                      {ref.label}
                      <ExternalLink className="size-3.5" aria-hidden />
                    </a>
                  ) : (
                    ref.label
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1">
          <span className="text-xs text-fg-muted">{CONFIDENCE_LABELS[issue.confidence]}</span>
          <span className="text-xs text-fg-muted">{EFFORT_LABELS[issue.effort]}</span>
          <button
            type="button"
            onClick={() => onAsk(issue)}
            className="ml-auto inline-flex h-8 items-center gap-1.5 rounded px-2 text-xs font-medium text-fg-muted hover:bg-ink-800 hover:text-fg"
          >
            <MessageSquareText className="size-4" aria-hidden />
            Ask about this
          </button>
        </div>
      </div>
    </article>
  );
}
