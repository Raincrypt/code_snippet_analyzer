import type { Metrics } from "@/types/review";

const TILES: readonly { key: keyof Metrics; label: string }[] = [
  { key: "totalLines", label: "Total lines" },
  { key: "codeLines", label: "Lines of code" },
  { key: "commentLines", label: "Comment lines" },
  { key: "blankLines", label: "Blank lines" },
  { key: "longestLine", label: "Longest line (characters)" },
  { key: "functionCount", label: "Functions" },
  { key: "longestFunctionLines", label: "Longest function (lines)" },
  { key: "maxNestingDepth", label: "Deepest nesting" },
];

export function MetricsTab({ metrics }: { metrics: Metrics }) {
  const missing = TILES.some(({ key }) => metrics[key] == null);
  return (
    <div className="space-y-4 p-4">
      <p className="text-sm text-fg-muted">
        Measured directly from your code, not estimated by AI.
      </p>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {TILES.map(({ key, label }) => {
          const value = metrics[key];
          return (
            <div key={key} className="rounded-md border border-ink-700 bg-ink-900 p-3">
              <dt className="text-xs text-fg-muted">{label}</dt>
              <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
                {value ?? <span title="Not measured yet">—</span>}
              </dd>
            </div>
          );
        })}
      </dl>
      {missing && (
        <p className="text-xs text-fg-muted">
          A dash means that figure needs the code analyser, which isn’t connected yet.
        </p>
      )}
    </div>
  );
}
