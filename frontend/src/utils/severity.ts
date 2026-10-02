import type { Severity } from "@/types/review";

export const SEVERITY_ORDER: Severity[] = ["error", "warning", "info", "suggestion"];

// Full class names are written out (not built with template strings)
// so Tailwind can detect them at build time.
export const SEVERITY_STYLES: Record<
  Severity,
  { label: string; text: string; rail: string; chip: string; dot: string }
> = {
  error: {
    label: "Error",
    text: "text-sev-error",
    rail: "border-l-sev-error",
    chip: "bg-sev-error/15 text-sev-error",
    dot: "bg-sev-error",
  },
  warning: {
    label: "Warning",
    text: "text-sev-warning",
    rail: "border-l-sev-warning",
    chip: "bg-sev-warning/15 text-sev-warning",
    dot: "bg-sev-warning",
  },
  info: {
    label: "Info",
    text: "text-sev-info",
    rail: "border-l-sev-info",
    chip: "bg-sev-info/15 text-sev-info",
    dot: "bg-sev-info",
  },
  suggestion: {
    label: "Suggestion",
    text: "text-sev-suggestion",
    rail: "border-l-sev-suggestion",
    chip: "bg-sev-suggestion/15 text-sev-suggestion",
    dot: "bg-sev-suggestion",
  },
};

export function formatLineRange(line: number, endLine?: number): string {
  return endLine && endLine > line ? `Lines ${line}–${endLine}` : `Line ${line}`;
}

export function scoreColor(score: number): string {
  if (score >= 8) return "text-good";
  if (score >= 5) return "text-sev-warning";
  return "text-sev-error";
}
