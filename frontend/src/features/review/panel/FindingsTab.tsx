import { useMemo, useState } from "react";
import { CircleCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { Category, CodeIssue, Severity } from "@/types/review";
import {
  DEFAULT_FILTERS,
  countBySeverity,
  organiseFindings,
  type SortMode,
} from "@/utils/findings";
import { issueKey } from "@/utils/issues";
import { SEVERITY_ORDER, SEVERITY_STYLES } from "@/utils/severity";
import { CATEGORY_META } from "./categories";
import { FindingCard } from "./FindingCard";
import { Message } from "./Message";

type FindingsTabProps = {
  issues: readonly CodeIssue[];
  priorityFixes: readonly string[];
  activeKey: string | null;
  onLocate: (issue: CodeIssue) => void;
  onAsk: (issue: CodeIssue) => void;
};

const SORT_OPTIONS = [
  { value: "severity", label: "Most severe first" },
  { value: "line", label: "By line number" },
] as const;

export function FindingsTab({
  issues,
  priorityFixes,
  activeKey,
  onLocate,
  onAsk,
}: FindingsTabProps) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  // The most important findings start open; the rest stay collapsed until asked for.
  const [expanded, setExpanded] = useState(
    () =>
      new Set([...priorityFixes, ...issues.filter((i) => i.severity === "error").map((i) => i.id)]),
  );

  // When the editor selects a finding, open its card (adjusting state while rendering is
  // React's recommended way to react to a changed prop).
  const [seenKey, setSeenKey] = useState(activeKey);
  if (activeKey !== seenKey) {
    setSeenKey(activeKey);
    if (activeKey) setExpanded((prev) => new Set(prev).add(activeKey));
  }

  const counts = countBySeverity(issues);
  const { main, doubleCheck } = useMemo(() => organiseFindings(issues, filters), [issues, filters]);
  const categories = useMemo(
    () => [...new Set(issues.map((i) => i.category))] as Category[],
    [issues],
  );
  const shown = main.length + doubleCheck.length;

  if (issues.length === 0) {
    return (
      <Message icon={<CircleCheck className="size-6 text-good" />} title="No issues found">
        Nothing to flag in correctness, security, performance or readability.
      </Message>
    );
  }

  function toggleSeverity(severity: Severity) {
    setFilters((f) => {
      const next = new Set(f.severities);
      if (!next.delete(severity)) next.add(severity);
      return { ...f, severities: next };
    });
  }

  function toggleOpen(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }

  const allOpen = shown > 0 && [...main, ...doubleCheck].every((i) => expanded.has(i.id));
  const setAll = (open: boolean) =>
    setExpanded(open ? new Set(issues.map((i) => i.id)) : new Set());

  const renderCard = (issue: CodeIssue, index: number) => (
    <FindingCard
      key={issueKey(issue)}
      issue={issue}
      index={index}
      open={expanded.has(issue.id)}
      onToggle={() => toggleOpen(issue.id)}
      active={issueKey(issue) === activeKey}
      onLocate={onLocate}
      onAsk={onAsk}
    />
  );

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter findings">
        {SEVERITY_ORDER.filter((sev) => counts[sev] > 0).map((sev) => {
          const pressed = filters.severities.has(sev);
          return (
            <button
              key={sev}
              type="button"
              aria-pressed={pressed}
              onClick={() => toggleSeverity(sev)}
              className={`inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors ${
                pressed
                  ? "border-chalk bg-ink-800 text-fg"
                  : "border-ink-700 text-fg-muted hover:bg-ink-900 hover:text-fg"
              }`}
            >
              <span className={`size-2 rounded-full ${SEVERITY_STYLES[sev].dot}`} aria-hidden />
              {SEVERITY_STYLES[sev].label} <span className="tabular-nums">{counts[sev]}</span>
            </button>
          );
        })}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Select
            label="Category"
            value={filters.category}
            options={[
              { value: "all", label: "All categories" },
              ...categories.map((c) => ({ value: c, label: CATEGORY_META[c].label })),
            ]}
            onChange={(category) =>
              setFilters((f) => ({ ...f, category: category as Category | "all" }))
            }
          />
          <Select
            label="Sort"
            value={filters.sort}
            options={SORT_OPTIONS}
            onChange={(sort) => setFilters((f) => ({ ...f, sort: sort as SortMode }))}
          />
          <Button variant="ghost" className="h-8 px-2 text-xs" onClick={() => setAll(!allOpen)}>
            {allOpen ? "Collapse all" : "Expand all"}
          </Button>
        </div>
      </div>

      <p className="text-xs text-fg-muted" role="status">
        Showing {shown} of {issues.length} findings
      </p>

      {shown === 0 && (
        <Message icon={<CircleCheck className="size-6" />} title="No findings match these filters">
          <Button variant="ghost" className="mt-2" onClick={() => setFilters(DEFAULT_FILTERS)}>
            Clear filters
          </Button>
        </Message>
      )}

      <div className="space-y-3">{main.map(renderCard)}</div>

      {doubleCheck.length > 0 && (
        <section aria-labelledby="double-check-title" className="space-y-3 pt-2">
          <div>
            <h3 id="double-check-title" className="text-sm font-semibold">
              Worth double-checking
            </h3>
            <p className="text-xs text-fg-muted">The reviewer was less sure about these.</p>
          </div>
          {doubleCheck.map((issue, i) => renderCard(issue, main.length + i))}
        </section>
      )}
    </div>
  );
}
