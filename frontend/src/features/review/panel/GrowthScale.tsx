import { GROWTH_SCALE, complexityRank, growthTone, type GrowthTone } from "@/utils/bigO";

// Full class names are written out so Tailwind can detect them at build time.
export const TONE_PILL: Record<GrowthTone, string> = {
  good: "bg-good/20 text-good ring-good/60",
  fair: "bg-sev-info/20 text-sev-info ring-sev-info/60",
  warn: "bg-sev-warning/20 text-sev-warning ring-sev-warning/60",
  bad: "bg-sev-error/20 text-sev-error ring-sev-error/60",
};

export const TONE_TEXT: Record<GrowthTone, string> = {
  good: "text-good",
  fair: "text-sev-info",
  warn: "text-sev-warning",
  bad: "text-sev-error",
};

const TONE_HINT: Record<GrowthTone, string> = {
  good: "stays fast as the input grows.",
  fair: "is fine for most input sizes.",
  warn: "slows down quickly on large inputs.",
  bad: "is only practical for very small inputs.",
};

/** Shows where a growth rate sits among the common ones, from fastest to slowest. */
export function GrowthScale({ value }: { value: string }) {
  const rank = complexityRank(value);
  const tone = rank === null ? null : growthTone(rank);
  const current = rank === null ? null : GROWTH_SCALE[rank];

  return (
    <div>
      <ol aria-label="Common growth rates, fastest to slowest" className="flex flex-wrap gap-1.5">
        {GROWTH_SCALE.map((g, i) => (
          <li
            key={g.label}
            aria-current={i === rank ? "true" : undefined}
            className={`rounded-full px-2.5 py-1 font-mono text-xs ${
              i === rank && tone
                ? `font-semibold ring-1 ${TONE_PILL[tone]}`
                : "bg-ink-800 text-fg-muted"
            }`}
          >
            {g.label}
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-fg-muted">
        {current && tone
          ? `${current.name} growth ${TONE_HINT[tone]}`
          : "This growth rate is not one of the common ones shown above."}
      </p>
    </div>
  );
}
