import { Check, Circle, LoaderCircle } from "lucide-react";
import { REVIEW_STAGES, type ReviewStage } from "@/types/review";

export const STAGE_LABELS: Record<ReviewStage, string> = {
  prepare: "Preparing your code",
  understand: "Understanding what it does",
  analyse: "Checking for bugs, security and performance issues",
  complexity: "Working out time complexity and algorithms",
  verify: "Verifying the findings",
};

export function ReviewProgress({ stage }: { stage: ReviewStage | null }) {
  const current = stage ? REVIEW_STAGES.indexOf(stage) : -1;
  return (
    <div role="status" aria-label="Review progress" className="mx-auto max-w-md px-4 py-8">
      <h3 className="mb-4 text-sm font-semibold">Reviewing your code…</h3>
      <ol className="space-y-3">
        {REVIEW_STAGES.map((s, i) => {
          const state = i < current ? "done" : i === current ? "current" : "pending";
          return (
            <li
              key={s}
              aria-current={state === "current" ? "step" : undefined}
              className={`flex items-center gap-3 text-sm ${
                state === "pending"
                  ? "text-fg-muted/60"
                  : state === "current"
                    ? "text-fg"
                    : "text-fg-muted"
              }`}
            >
              {state === "done" && <Check className="size-4 shrink-0 text-good" aria-hidden />}
              {state === "current" && (
                <LoaderCircle className="size-4 shrink-0 motion-safe:animate-spin" aria-hidden />
              )}
              {state === "pending" && <Circle className="size-4 shrink-0" aria-hidden />}
              <span>{STAGE_LABELS[s]}</span>
              <span className="sr-only">({state})</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
