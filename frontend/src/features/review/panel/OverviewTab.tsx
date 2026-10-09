import { CircleCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { ScoreRing } from "@/components/ui/ScoreRing";
import type { CodeIssue, ReviewResult } from "@/types/review";
import { formatBigO } from "@/utils/bigO";
import { countBySeverity } from "@/utils/findings";
import { SEVERITY_ORDER, SEVERITY_STYLES, formatLineRange, scoreColor } from "@/utils/severity";
import { VERDICT_STYLES } from "@/utils/verdict";
import { RichText } from "@/components/RichText";
import { Section } from "./Section";

export type TabId = "overview" | "findings" | "complexity" | "metrics";

type OverviewTabProps = {
  result: ReviewResult;
  onLocate: (issue: CodeIssue) => void;
  onOpenTab: (tab: TabId) => void;
};

const AREA_LABELS = {
  correctness: "Correctness",
  security: "Security",
  performance: "Performance",
  readability: "Readability",
} as const;

export function OverviewTab({ result, onLocate, onOpenTab }: OverviewTabProps) {
  const verdict = VERDICT_STYLES[result.verdict];
  const counts = countBySeverity(result.issues);
  const priority = result.priorityFixes
    .map((id) => result.issues.find((i) => i.id === id))
    .filter((i): i is CodeIssue => i !== undefined);

  return (
    <div className="space-y-6 p-4">
      <header className="flex items-start gap-4">
        {result.score != null && <ScoreRing score={result.score} />}
        <div className="min-w-0">
          <p className={`text-base font-semibold ${verdict.text}`}>{verdict.label}</p>
          <p className="mt-1 max-w-prose text-sm leading-relaxed">
            <RichText>{result.summary}</RichText>
          </p>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-muted">
            {SEVERITY_ORDER.filter((sev) => counts[sev] > 0).map((sev) => (
              <li key={sev} className="inline-flex items-center gap-1.5">
                <span className={`size-2 rounded-full ${SEVERITY_STYLES[sev].dot}`} aria-hidden />
                {counts[sev]} {SEVERITY_STYLES[sev].label.toLowerCase()}
                {counts[sev] > 1 ? "s" : ""}
              </li>
            ))}
          </ul>
        </div>
      </header>

      <Section title="What this code does">
        <p className="text-sm leading-relaxed">
          <RichText>{result.purpose}</RichText>
        </p>
      </Section>

      {result.complexity && (
        <Section title="Complexity at a glance">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-md border border-ink-700 bg-ink-900 p-3 text-sm">
            <span>
              <span className="text-xs text-fg-muted">Time </span>
              <span className="font-mono font-semibold">{formatBigO(result.complexity.time)}</span>
            </span>
            <span>
              <span className="text-xs text-fg-muted">Space </span>
              <span className="font-mono font-semibold">{formatBigO(result.complexity.space)}</span>
            </span>
            {result.algorithms.length > 0 && (
              <span>
                <span className="text-xs text-fg-muted">Algorithm </span>
                <span className="font-semibold">
                  {result.algorithms.map((a) => a.name).join(", ")}
                </span>
              </span>
            )}
            <button
              type="button"
              onClick={() => onOpenTab("complexity")}
              className="ml-auto text-xs font-medium text-sev-info underline-offset-2 hover:underline"
            >
              See details
            </button>
          </div>
        </Section>
      )}

      {priority.length > 0 && (
        <Section title="Fix these first">
          <ol className="space-y-2">
            {priority.map((issue, i) => (
              <li key={issue.id}>
                <button
                  type="button"
                  onClick={() => {
                    onLocate(issue);
                    onOpenTab("findings");
                  }}
                  className="flex w-full items-center gap-3 rounded-md border border-ink-700 bg-ink-900 p-3 text-left hover:bg-ink-800"
                >
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-ink-800 text-xs font-semibold tabular-nums">
                    {i + 1}
                  </span>
                  <span className="min-w-0 flex-1 text-sm font-medium">{issue.title}</span>
                  <Badge severity={issue.severity} />
                  <span className="shrink-0 font-mono text-xs text-fg-muted">
                    {formatLineRange(issue.line, issue.endLine ?? undefined)}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {result.scoreBreakdown && (
        <Section title="Score breakdown">
          <ul className="space-y-3">
            {(Object.keys(AREA_LABELS) as (keyof typeof AREA_LABELS)[]).map((area) => {
              const { score, reason } = result.scoreBreakdown![area];
              return (
                <li key={area}>
                  <div className="flex items-center gap-3">
                    <span className="w-24 shrink-0 text-sm">{AREA_LABELS[area]}</span>
                    <div
                      className="h-2 flex-1 overflow-hidden rounded-full bg-ink-800"
                      role="img"
                      aria-label={`${AREA_LABELS[area]} ${score} out of 10`}
                    >
                      <div
                        className={`h-full rounded-full bg-current ${scoreColor(score)}`}
                        style={{ width: `${score * 10}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-sm font-semibold tabular-nums">
                      {score}
                    </span>
                  </div>
                  <p className="mt-1 pl-27 text-xs leading-relaxed text-fg-muted">
                    <RichText>{reason}</RichText>
                  </p>
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      {result.positives.length > 0 && (
        <Section title="What's good">
          <ul className="space-y-1.5">
            {result.positives.map((p) => (
              <li key={`${p.line}-${p.comment}`} className="flex gap-2 text-sm">
                <CircleCheck className="mt-0.5 size-4 shrink-0 text-good" aria-hidden />
                <span>
                  <span className="font-mono text-xs text-fg-muted">L{p.line}</span>{" "}
                  <RichText>{p.comment}</RichText>
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {result.limitations.length > 0 && (
        <Section title="Limits of this review">
          <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-fg-muted">
            {result.limitations.map((text) => (
              <li key={text}>
                <RichText>{text}</RichText>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
