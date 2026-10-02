import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags as t } from "@lezer/highlight";
import type { Severity } from "@/types/review";
import { SEVERITY_ORDER } from "@/utils/severity";

// Every color is a CSS variable from index.css, so Light / Dark / System (and the smooth
// theme fade) apply to the editor automatically, with no reconfiguration.
const mix = (color: string, percent: number) =>
  `color-mix(in oklab, var(${color}) ${percent}%, transparent)`;
const sev = (s: Severity) => `--color-sev-${s}`;

const severityRules = Object.fromEntries(
  SEVERITY_ORDER.flatMap((s) => [
    [
      `.cm-issue-line-${s}`,
      {
        // A gradient (not background-color) so it layers with the active-line highlight.
        backgroundImage: `linear-gradient(${mix(sev(s), 13)}, ${mix(sev(s), 13)})`,
        boxShadow: `inset 3px 0 0 var(${sev(s)})`,
      },
    ],
    [`.cm-issue-dot-${s}`, { backgroundColor: `var(${sev(s)})` }],
  ]),
);

export const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    color: "var(--color-fg)",
    backgroundColor: "var(--color-ink-950)",
    fontSize: "var(--editor-font-size, 13px)",
  },
  "&.cm-focused": { outline: "2px solid var(--color-chalk)", outlineOffset: "-2px" },
  ".cm-content:focus-visible": { outline: "none" },
  ".cm-scroller": {
    fontFamily: "var(--font-mono)",
    lineHeight: "var(--editor-line-height, 22px)",
    overflow: "auto",
  },
  ".cm-content": { caretColor: "var(--color-chalk)", padding: "12px 0" },
  ".cm-line": { padding: "0 16px 0 8px" },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "var(--color-chalk)", borderLeftWidth: "2px" },
  ".cm-placeholder": { color: mix("--color-fg-muted", 70) },

  ".cm-gutters": {
    backgroundColor: "var(--color-ink-950)",
    color: mix("--color-fg-muted", 65),
    border: "none",
    borderRight: "1px solid var(--color-ink-800)",
  },
  ".cm-lineNumbers .cm-gutterElement": { padding: "0 12px 0 4px", minWidth: "32px" },
  ".cm-issue-gutter .cm-gutterElement": {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "0 4px 0 10px",
  },
  ".cm-issue-dot": { width: "8px", height: "8px", borderRadius: "50%", cursor: "pointer" },
  ...severityRules,

  ".cm-activeLine": { backgroundColor: mix("--color-fg", 5) },
  ".cm-activeLineGutter": { backgroundColor: "transparent", color: "var(--color-fg)" },
  ".cm-selectionBackground": { backgroundColor: mix("--color-sev-info", 28) },
  "&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground": {
    backgroundColor: mix("--color-sev-info", 38),
  },
  "&.cm-focused .cm-matchingBracket": {
    backgroundColor: mix("--color-sev-info", 25),
    outline: `1px solid ${mix("--color-sev-info", 55)}`,
  },
});

export const syntaxTheme = syntaxHighlighting(
  HighlightStyle.define([
    { tag: t.keyword, color: "var(--syn-keyword)" },
    { tag: [t.string, t.regexp, t.special(t.string)], color: "var(--syn-string)" },
    { tag: [t.number, t.bool, t.null, t.atom], color: "var(--syn-number)" },
    { tag: t.comment, color: "var(--syn-comment)", fontStyle: "italic" },
    {
      tag: [
        t.function(t.variableName),
        t.function(t.propertyName),
        t.definition(t.function(t.variableName)),
      ],
      color: "var(--syn-function)",
    },
    { tag: [t.typeName, t.className, t.namespace], color: "var(--syn-type)" },
    { tag: [t.propertyName, t.attributeName], color: "var(--syn-property)" },
    { tag: [t.operator, t.punctuation], color: "var(--syn-operator)" },
    { tag: [t.meta, t.annotation, t.tagName], color: "var(--syn-meta)" },
  ]),
);
