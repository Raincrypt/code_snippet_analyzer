import { Sigma } from "lucide-react";
import type { Complexity, DetectedAlgorithm } from "@/types/review";
import { complexityRank, formatBigO, growthTone } from "@/utils/bigO";
import { formatLineRange } from "@/utils/severity";
import { AlgorithmCard } from "./AlgorithmCard";
import { GrowthScale, TONE_TEXT } from "./GrowthScale";
import { Message } from "./Message";
import { RichText } from "@/components/RichText";
import { Section } from "./Section";

type ComplexityTabProps = {
  complexity: Complexity | null | undefined;
  algorithms: readonly DetectedAlgorithm[];
  onLocateLines: (startLine: number, endLine: number) => void;
};

function Stat({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="rounded-md border border-ink-700 bg-ink-900 p-4">
      <div className="text-xs text-fg-muted">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold ${className}`}>
        {formatBigO(value)}
      </div>
    </div>
  );
}

const orDash = (value: string | null | undefined) => (value ? formatBigO(value) : "—");

export function ComplexityTab({ complexity, algorithms, onLocateLines }: ComplexityTabProps) {
  if (!complexity) {
    return (
      <Message icon={<Sigma className="size-6" />} title="Complexity wasn't determined">
        The reviewer could not work out time and space complexity for this code.
      </Message>
    );
  }

  const rank = complexityRank(complexity.time);
  const timeTone = rank === null ? "" : TONE_TEXT[growthTone(rank)];

  return (
    <div className="space-y-6 p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Stat label="Time (worst case)" value={complexity.time} className={timeTone} />
        <Stat label="Extra space" value={complexity.space} />
      </div>

      <GrowthScale value={complexity.time} />

      <Section title="How this was worked out">
        <p className="text-sm leading-relaxed">
          <RichText>{complexity.explanation}</RichText>
        </p>
      </Section>

      {complexity.functions.length > 0 && (
        <Section title="By function">
          <ul className="space-y-3">
            {complexity.functions.map((fn) => (
              <li key={fn.name} className="rounded-md border border-ink-700 bg-ink-900 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-mono text-sm font-semibold">{fn.name}</h4>
                  <button
                    type="button"
                    onClick={() => onLocateLines(fn.startLine, fn.endLine)}
                    title="Show in editor"
                    className="ml-auto rounded bg-ink-800 px-1.5 py-0.5 font-mono text-xs text-fg-muted hover:bg-ink-700 hover:text-fg"
                  >
                    {formatLineRange(fn.startLine, fn.endLine)}
                  </button>
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {(
                    [
                      ["Best case", fn.bestCase],
                      ["Average case", fn.averageCase],
                      ["Worst case", fn.worstCase],
                      ["Extra space", fn.space],
                    ] as const
                  ).map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-xs text-fg-muted">{label}</dt>
                      <dd className="font-mono text-sm font-semibold">{orDash(value)}</dd>
                    </div>
                  ))}
                </dl>
                <p className="mt-3 text-sm leading-relaxed text-fg-muted">
                  <RichText>{fn.explanation}</RichText>
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Algorithms recognised">
        {algorithms.length === 0 ? (
          <p className="text-sm text-fg-muted">
            No named algorithm was recognised in this code. That is normal for ordinary application
            logic.
          </p>
        ) : (
          <div className="space-y-3">
            {algorithms.map((algorithm) => (
              <AlgorithmCard
                key={`${algorithm.name}-${algorithm.startLine}`}
                algorithm={algorithm}
                onLocateLines={onLocateLines}
              />
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
