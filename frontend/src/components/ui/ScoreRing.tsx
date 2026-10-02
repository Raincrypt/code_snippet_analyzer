import { scoreColor } from "@/utils/severity";

const RADIUS = 26;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function ScoreRing({ score }: { score: number }) {
  const offset = CIRCUMFERENCE * (1 - score / 10);
  return (
    <div
      className={`relative size-16 shrink-0 ${scoreColor(score)}`}
      role="img"
      aria-label={`Score ${score} out of 10`}
    >
      <svg viewBox="0 0 64 64" className="size-full -rotate-90">
        <circle cx="32" cy="32" r={RADIUS} fill="none" strokeWidth="5" className="stroke-ink-700" />
        <circle
          cx="32"
          cy="32"
          r={RADIUS}
          fill="none"
          strokeWidth="5"
          strokeLinecap="round"
          stroke="currentColor"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className="motion-safe:transition-[stroke-dashoffset] motion-safe:duration-700"
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-lg font-semibold text-fg tabular-nums">
        {score}
      </span>
    </div>
  );
}
