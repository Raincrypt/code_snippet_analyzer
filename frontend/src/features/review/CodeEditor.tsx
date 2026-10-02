import { useEffect, useImperativeHandle, useRef, type CSSProperties, type Ref } from "react";
import { closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { bracketMatching, indentOnInput } from "@codemirror/language";
import { Compartment, EditorSelection, EditorState } from "@codemirror/state";
import {
  EditorView,
  drawSelection,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
  placeholder,
} from "@codemirror/view";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { EditorFontSize } from "@/types/settings";
import { LANGUAGES } from "@/utils/languages";
import { loadLanguage } from "./editor/languages";
import { issueMarkers, lineRangeOffsets, setIssues, type EditorIssue } from "./editor/issueMarkers";
import { editorTheme, syntaxTheme } from "./editor/theme";

export type { EditorIssue };

/** Methods the parent can call on the editor. */
export type CodeEditorHandle = {
  /** Select and scroll to whole lines `line`..`endLine`, and focus the editor. */
  revealLines: (line: number, endLine?: number) => void;
};

type CodeEditorProps = {
  code: string;
  onCodeChange: (code: string) => void;
  language: string;
  onLanguageChange: (language: string) => void;
  onReview: () => void;
  loading: boolean;
  /** Findings to mark in the editor (tinted lines + gutter dots). */
  issues: readonly EditorIssue[];
  fontSize: EditorFontSize;
  /** Called when a gutter dot is clicked. */
  onIssueClick?: (line: number) => void;
  ref?: Ref<CodeEditorHandle>;
};

// Font size and line height are exposed to the editor theme as CSS variables.
const FONT_METRICS: Record<EditorFontSize, { fontSize: number; lineHeight: number }> = {
  small: { fontSize: 12, lineHeight: 20 },
  medium: { fontSize: 13, lineHeight: 22 },
  large: { fontSize: 15, lineHeight: 26 },
};

// A Compartment lets us swap the language extension without recreating the editor.
const languageCompartment = new Compartment();

export function CodeEditor({
  code,
  onCodeChange,
  language,
  onLanguageChange,
  onReview,
  loading,
  issues,
  fontSize,
  onIssueClick,
  ref,
}: CodeEditorProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const initialCode = useRef(code);

  // The editor is created once, so it reads the latest callbacks through a ref.
  const callbacks = useRef({ onCodeChange, onReview, onIssueClick });
  useEffect(() => {
    callbacks.current = { onCodeChange, onReview, onIssueClick };
  });

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const view = new EditorView({
      parent: host,
      state: EditorState.create({
        doc: initialCode.current,
        extensions: [
          issueMarkers({ onGutterClick: (line) => callbacks.current.onIssueClick?.(line) }),
          lineNumbers(),
          highlightActiveLineGutter(),
          highlightActiveLine(),
          history(),
          drawSelection(),
          indentOnInput(),
          bracketMatching(),
          closeBrackets(),
          keymap.of([
            // Listed first so it wins over the default Mod-Enter ("insert blank line").
            { key: "Mod-Enter", run: () => (callbacks.current.onReview(), true) },
            ...closeBracketsKeymap,
            ...defaultKeymap,
            ...historyKeymap,
            indentWithTab,
          ]),
          languageCompartment.of([]),
          editorTheme,
          syntaxTheme,
          placeholder("Paste code here…"),
          EditorView.contentAttributes.of({ "aria-label": "Code to review", spellcheck: "false" }),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) callbacks.current.onCodeChange(update.state.doc.toString());
          }),
        ],
      }),
    });
    viewRef.current = view;
    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, []);

  // Parent -> editor: apply outside changes to the text (typing flows the other way).
  useEffect(() => {
    const view = viewRef.current;
    if (view && view.state.doc.toString() !== code) {
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: code } });
    }
  }, [code]);

  // Load the language pack on demand; ignore the result if the choice changed meanwhile.
  useEffect(() => {
    let cancelled = false;
    loadLanguage(language)
      .then((extension) => {
        if (!cancelled)
          viewRef.current?.dispatch({ effects: languageCompartment.reconfigure(extension) });
      })
      .catch(() => {
        // Pack failed to load (offline): keep plain text rather than breaking the editor.
      });
    return () => {
      cancelled = true;
    };
  }, [language]);

  useEffect(() => {
    viewRef.current?.dispatch({ effects: setIssues.of(issues) });
  }, [issues]);

  // Font metrics are CSS variables; ask the editor to re-measure its lines when they change.
  useEffect(() => {
    viewRef.current?.requestMeasure();
  }, [fontSize]);

  useImperativeHandle(
    ref,
    () => ({
      revealLines(line, endLine) {
        const view = viewRef.current;
        if (!view) return;
        const { from, to } = lineRangeOffsets(view.state.doc, line, endLine);
        const range = EditorSelection.range(from, to);
        view.dispatch({
          selection: range,
          effects: EditorView.scrollIntoView(range, { y: "center" }),
        });
        view.focus();
      },
    }),
    [],
  );

  const metrics = FONT_METRICS[fontSize];
  const lineCount = Math.max(code.split("\n").length, 1);

  return (
    <section aria-label="Code editor" className="flex h-full min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-3 border-b border-ink-700 px-4 py-2.5">
        <Select label="Language" value={language} options={LANGUAGES} onChange={onLanguageChange} />
        <span className="ml-auto font-mono text-xs text-fg-muted tabular-nums" aria-live="off">
          {lineCount} {lineCount === 1 ? "line" : "lines"} · {code.length.toLocaleString()} chars
        </span>
        <Button
          icon={<Play className="size-4" aria-hidden />}
          onClick={onReview}
          loading={loading}
          disabled={!code.trim()}
          title="Review (Ctrl/Cmd+Enter)"
        >
          {loading ? "Reviewing" : "Review"}
        </Button>
      </div>

      <div className="relative min-h-0 flex-1 bg-ink-950">
        <div
          ref={hostRef}
          className="absolute inset-0"
          style={
            {
              "--editor-font-size": `${metrics.fontSize}px`,
              "--editor-line-height": `${metrics.lineHeight}px`,
            } as CSSProperties
          }
        />
      </div>
    </section>
  );
}