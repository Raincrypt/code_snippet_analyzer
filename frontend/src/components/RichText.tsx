/**
 * Plain text with `inline code` shown in code style. It only ever creates text and <code>
 * elements, never HTML, so model output cannot inject markup.
 */
export function RichText({ children }: { children: string }) {
  // An unmatched backtick is just a character, so leave such text alone.
  if ((children.match(/`/g) ?? []).length % 2 !== 0) return <>{children}</>;
  return (
    <>
      {children.split("`").map((part, i) =>
        i % 2 === 1 ? (
          <code key={i} className="rounded bg-ink-800 px-1 py-0.5 font-mono text-[0.85em]">
            {part}
          </code>
        ) : (
          part
        ),
      )}
    </>
  );
}
