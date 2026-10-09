import type { DetectedAlgorithm } from "@/types/review";
import { formatBigO } from "@/utils/bigO";
import { formatLineRange } from "@/utils/severity";
import { CONFIDENCE_LABELS } from "./categories";
import { RichText } from "@/components/RichText";

type AlgorithmCardProps = {
  algorithm: DetectedAlgorithm;
  onLocateLines: (startLine: number, endLine: number) => void;
};

function Field({ label, children }: { label: string; children: string }) {
  return (
    <div>
      <h5 className="mb-0.5 text-xs font-semibold text-fg-muted">{label}</h5>
      <p className="text-sm leading-relaxed text-fg">
        <RichText>{children}</RichText>
      </p>
    </div>
  );
}

export function AlgorithmCard({ algorithm, onLocateLines }: AlgorithmCardProps) {
  return (
    <article className="space-y-3 rounded-md border border-ink-700 bg-ink-900 p-4">
      <header className="flex flex-wrap items-center gap-2">
        <h4 className="text-[0.95rem] font-semibold">{algorithm.name}</h4>
        <span className="rounded bg-ink-800 px-1.5 py-0.5 text-xs text-fg-muted">
          {algorithm.category}
        </span>
        <span className="text-xs text-fg-muted">{CONFIDENCE_LABELS[algorithm.confidence]}</span>
        <button
          type="button"
          onClick={() => onLocateLines(algorithm.startLine, algorithm.endLine)}
          title="Show in editor"
          className="ml-auto rounded bg-ink-800 px-1.5 py-0.5 font-mono text-xs text-fg-muted hover:bg-ink-700 hover:text-fg"
        >
          {formatLineRange(algorithm.startLine, algorithm.endLine)}
        </button>
      </header>

      <p className="text-sm leading-relaxed text-fg">
        <RichText>{algorithm.summary}</RichText>
      </p>
      <Field label="How the code shows it">{algorithm.evidence}</Field>

      <dl className="flex gap-6">
        <div>
          <dt className="text-xs text-fg-muted">Time</dt>
          <dd className="font-mono text-sm font-semibold">{formatBigO(algorithm.time)}</dd>
        </div>
        <div>
          <dt className="text-xs text-fg-muted">Space</dt>
          <dd className="font-mono text-sm font-semibold">{formatBigO(algorithm.space)}</dd>
        </div>
      </dl>

      <Field label="Is it a good fit here?">{algorithm.assessment}</Field>

      {algorithm.alternatives.length > 0 && (
        <div>
          <h5 className="mb-1.5 text-xs font-semibold text-fg-muted">Alternatives</h5>
          <ul className="space-y-2">
            {algorithm.alternatives.map((alt) => (
              <li key={alt.name} className="rounded bg-ink-950 p-3 text-sm">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-semibold">{alt.name}</span>
                  <span className="font-mono text-xs text-fg-muted">
                    time {formatBigO(alt.time)} · space {formatBigO(alt.space)}
                  </span>
                </div>
                <p className="mt-1 leading-relaxed text-fg-muted">
                  <RichText>{alt.tradeoff}</RichText>
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
