import { useRef, type KeyboardEvent } from "react";

export type TabItem<T extends string> = { id: T; label: string; badge?: number };

type TabsProps<T extends string> = {
  label: string;
  items: readonly TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Makes element ids unique when several tab sets exist. */
  idPrefix: string;
};

export const tabId = (prefix: string, id: string) => `${prefix}-tab-${id}`;
export const panelId = (prefix: string, id: string) => `${prefix}-panel-${id}`;

/** An accessible tab bar: arrow keys, Home and End move between tabs. */
export function Tabs<T extends string>({ label, items, value, onChange, idPrefix }: TabsProps<T>) {
  const refs = useRef(new Map<T, HTMLButtonElement>());

  function handleKeyDown(e: KeyboardEvent<HTMLButtonElement>) {
    const index = items.findIndex((i) => i.id === value);
    let next = index;
    if (e.key === "ArrowRight") next = (index + 1) % items.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + items.length) % items.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = items.length - 1;
    else return;
    e.preventDefault();
    const target = items[next];
    if (!target) return;
    onChange(target.id);
    refs.current.get(target.id)?.focus();
  }

  return (
    <div
      role="tablist"
      aria-label={label}
      className="flex gap-1 overflow-x-auto border-b border-ink-700 px-4"
    >
      {items.map((item) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            ref={(el) => {
              if (el) refs.current.set(item.id, el);
              else refs.current.delete(item.id);
            }}
            type="button"
            role="tab"
            id={tabId(idPrefix, item.id)}
            aria-selected={selected}
            aria-controls={panelId(idPrefix, item.id)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={handleKeyDown}
            className={`-mb-px inline-flex h-10 shrink-0 items-center gap-1.5 border-b-2 px-3 text-sm whitespace-nowrap transition-colors ${
              selected
                ? "border-chalk font-semibold text-fg"
                : "border-transparent text-fg-muted hover:text-fg"
            }`}
          >
            {item.label}
            {item.badge !== undefined && (
              <span className="rounded-full bg-ink-800 px-1.5 text-xs tabular-nums">
                {item.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
