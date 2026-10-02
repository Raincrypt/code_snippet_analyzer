import type { LucideIcon } from "lucide-react";

export type SegmentedOption<T extends string> = {
  value: T;
  label: string;
  Icon?: LucideIcon;
  /** Shown under the control while this option is selected. */
  hint?: string;
};

type SegmentedControlProps<T extends string> = {
  legend: string;
  /** Radio group name; must be unique on the page. */
  name: string;
  value: T;
  options: readonly SegmentedOption<T>[];
  onChange: (value: T) => void;
};

export function SegmentedControl<T extends string>({
  legend,
  name,
  value,
  options,
  onChange,
}: SegmentedControlProps<T>) {
  const selected = options.find((o) => o.value === value);
  return (
    <fieldset>
      <legend className="text-xs font-semibold tracking-wide text-fg-muted uppercase">
        {legend}
      </legend>
      <div
        className="mt-2 grid gap-1 rounded-md bg-ink-800 p-1"
        style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
      >
        {options.map(({ value: optionValue, label, Icon }) => (
          <label key={optionValue}>
            <input
              type="radio"
              name={name}
              value={optionValue}
              checked={value === optionValue}
              onChange={() => onChange(optionValue)}
              className="peer sr-only"
            />
            <span className="flex h-8 cursor-pointer items-center justify-center gap-1.5 rounded text-sm text-fg-muted peer-checked:bg-chalk peer-checked:font-semibold peer-checked:text-chalk-ink peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-chalk">
              {Icon && <Icon className="size-4" aria-hidden />}
              {label}
            </span>
          </label>
        ))}
      </div>
      {selected?.hint && <p className="mt-1.5 text-xs text-fg-muted">{selected.hint}</p>}
    </fieldset>
  );
}
