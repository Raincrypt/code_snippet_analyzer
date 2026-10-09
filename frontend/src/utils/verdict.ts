import type { Verdict } from "@/types/review";

// Full class names are written out so Tailwind can detect them at build time.
export const VERDICT_STYLES: Record<Verdict, { label: string; text: string }> = {
  "fix-before-use": { label: "Fix before using", text: "text-sev-error" },
  "needs-work": { label: "Needs work", text: "text-sev-warning" },
  "mostly-fine": { label: "Mostly fine", text: "text-good" },
  "looks-good": { label: "Looks good", text: "text-good" },
  "not-assessed": { label: "Not assessed", text: "text-fg-muted" },
};
