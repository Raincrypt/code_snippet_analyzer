import type { Category, CodeIssue, Severity } from "@/types/review";
import { SEVERITY_ORDER } from "./severity";

export type SortMode = "severity" | "line";

export type FindingFilters = {
  /** Empty means every severity. */
  severities: ReadonlySet<Severity>;
  category: Category | "all";
  sort: SortMode;
};

export const DEFAULT_FILTERS: FindingFilters = {
  severities: new Set(),
  category: "all",
  sort: "severity",
};

const severityRank = (s: Severity) => SEVERITY_ORDER.indexOf(s);

function compare(sort: SortMode) {
  return (a: CodeIssue, b: CodeIssue) =>
    sort === "severity"
      ? severityRank(a.severity) - severityRank(b.severity) || a.line - b.line
      : a.line - b.line || severityRank(a.severity) - severityRank(b.severity);
}

/**
 * Applies the filters and sorting. Low-confidence findings are kept apart, in `doubleCheck`,
 * so they never get mixed in with the solid ones.
 */
export function organiseFindings(issues: readonly CodeIssue[], filters: FindingFilters) {
  const visible = issues
    .filter((i) => filters.severities.size === 0 || filters.severities.has(i.severity))
    .filter((i) => filters.category === "all" || i.category === filters.category)
    .sort(compare(filters.sort));
  return {
    main: visible.filter((i) => i.confidence !== "low"),
    doubleCheck: visible.filter((i) => i.confidence === "low"),
  };
}

export function countBySeverity(issues: readonly CodeIssue[]): Record<Severity, number> {
  const counts: Record<Severity, number> = { error: 0, warning: 0, info: 0, suggestion: 0 };
  for (const issue of issues) counts[issue.severity] += 1;
  return counts;
}
