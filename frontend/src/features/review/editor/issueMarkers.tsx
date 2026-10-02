import { RangeSet, StateEffect, StateField, type EditorState, type Text } from "@codemirror/state";
import { Decoration, EditorView, GutterMarker, gutter } from "@codemirror/view";
import type { Severity } from "@/types/review";
import { SEVERITY_ORDER } from "@/utils/severity";

export type EditorIssue = { line: number; endLine?: number; severity: Severity };

/** Send findings into the editor: `view.dispatch({ effects: setIssues.of(issues) })`. */
export const setIssues = StateEffect.define<readonly EditorIssue[]>();

const issuesField = StateField.define<readonly EditorIssue[]>({
  create: () => [],
  update(value, tr) {
    for (const effect of tr.effects) if (effect.is(setIssues)) return effect.value;
    return value;
  },
});

/** For every affected line, the most severe finding on it. Lines past the end are ignored. */
export function worstSeverityByLine(
  issues: readonly EditorIssue[],
  lineCount: number,
): Map<number, Severity> {
  const result = new Map<number, Severity>();
  for (const { line, endLine, severity } of issues) {
    const last = Math.min(endLine ?? line, lineCount);
    for (let l = Math.max(line, 1); l <= last; l++) {
      const current = result.get(l);
      if (!current || SEVERITY_ORDER.indexOf(severity) < SEVERITY_ORDER.indexOf(current)) {
        result.set(l, severity);
      }
    }
  }
  return result;
}

/** Document offsets covering whole lines `line`..`endLine`, clamped to the document. */
export function lineRangeOffsets(doc: Text, line: number, endLine = line) {
  const clamp = (n: number) => Math.min(Math.max(n, 1), doc.lines);
  const first = clamp(line);
  const last = Math.max(first, clamp(endLine));
  return { from: doc.line(first).from, to: doc.line(last).to };
}

class IssueDot extends GutterMarker {
  constructor(readonly severity: Severity) {
    super();
  }
  eq(other: GutterMarker) {
    return other instanceof IssueDot && other.severity === this.severity;
  }
  toDOM() {
    const dot = document.createElement("span");
    dot.className = `cm-issue-dot cm-issue-dot-${this.severity}`;
    return dot;
  }
}

const dots = Object.fromEntries(SEVERITY_ORDER.map((s) => [s, new IssueDot(s)])) as Record<
  Severity,
  IssueDot
>;
const lineDecorations = Object.fromEntries(
  SEVERITY_ORDER.map((s) => [s, Decoration.line({ class: `cm-issue-line cm-issue-line-${s}` })]),
) as Record<Severity, Decoration>;

const severities = (state: EditorState) =>
  worstSeverityByLine(state.field(issuesField), state.doc.lines);

const lineHighlights = EditorView.decorations.compute([issuesField, "doc"], (state) =>
  Decoration.set(
    [...severities(state)].map(([line, sev]) =>
      lineDecorations[sev].range(state.doc.line(line).from),
    ),
    true,
  ),
);

type IssueMarkerOptions = { onGutterClick?: (line: number) => void };

/** Tinted lines + colored dots in the gutter for findings. Clicking a dot calls `onGutterClick`. */
export function issueMarkers({ onGutterClick }: IssueMarkerOptions = {}) {
  return [
    issuesField,
    lineHighlights,
    gutter({
      class: "cm-issue-gutter",
      initialSpacer: () => dots.error, // reserves the column so the layout doesn't shift
      markers: (view) =>
        RangeSet.of<GutterMarker>(
          [...severities(view.state)].map(([line, sev]) =>
            dots[sev].range(view.state.doc.line(line).from),
          ),
          true,
        ),
      domEventHandlers: {
        mousedown(view, block) {
          const line = view.state.doc.lineAt(block.from).number;
          if (!severities(view.state).has(line)) return false;
          onGutterClick?.(line);
          return true;
        },
      },
    }),
  ];
}
