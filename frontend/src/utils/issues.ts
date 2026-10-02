import type { CodeIssue } from "@/types/review";
import { SEVERITY_ORDER } from "./severity";

/** Stable identity for a finding, used for React keys and for linking cards to code. */
export const issueKey = (issue: Pick<CodeIssue, "line" | "title">) =>
  `${issue.line}-${issue.title}`;

/** The most severe finding that covers `line`, if any. */
export function findIssueAtLine(issues: readonly CodeIssue[], line: number): CodeIssue | undefined {
  return issues
    .filter((i) => line >= i.line && line <= (i.endLine ?? i.line))
    .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity))[0];
}
