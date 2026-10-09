import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type CodeBlockProps = {
  code: string;
  /** When set, lines are numbered starting here. */
  startLine?: number;
  /** "remove" and "add" tint the block, for before/after comparisons. */
  tone?: "neutral" | "remove" | "add";
  label: string;
};

const TONES = {
  neutral: "border-ink-700 bg-ink-950",
  remove: "border-sev-error bg-sev-error/10",
  add: "border-good bg-good/10",
} as const;

export function CodeBlock({ code, startLine, tone = "neutral", label }: CodeBlockProps) {
  return (
    <figure className="min-w-0">
      <figcaption className="mb-1 text-xs text-fg-muted">{label}</figcaption>
      {/* Focusable so keyboard users can scroll long lines sideways (WCAG scrollable regions). */}
      {/* eslint-disable jsx-a11y/no-noninteractive-tabindex */}
      <pre
        tabIndex={0}
        aria-label={label}
        className={`overflow-x-auto rounded border-l-2 py-2 font-mono text-xs leading-relaxed ${TONES[tone]}`}
      >
        <code className="block min-w-max">
          {code.split("\n").map((line, i) => (
            <span key={i} className="flex px-3">
              {startLine !== undefined && (
                <span
                  className="w-8 shrink-0 pr-3 text-right text-fg-muted/60 select-none"
                  aria-hidden
                >
                  {startLine + i}
                </span>
              )}
              <span className="whitespace-pre">{line || " "}</span>
            </span>
          ))}
        </code>
      </pre>
      {/* eslint-enable jsx-a11y/no-noninteractive-tabindex */}
    </figure>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can be blocked (insecure page, permissions); there is nothing to show.
    }
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      className="inline-flex h-7 items-center gap-1.5 rounded px-2 text-xs font-medium text-fg-muted hover:bg-ink-800 hover:text-fg"
    >
      {copied ? (
        <Check className="size-3.5 text-good" aria-hidden />
      ) : (
        <Copy className="size-3.5" aria-hidden />
      )}
      <span aria-live="polite">{copied ? "Copied" : label}</span>
    </button>
  );
}
