import { ChevronDown } from "lucide-react";

type Option = { value: string; label: string };

type SelectProps = {
  label: string;
  value: string;
  options: readonly Option[];
  onChange: (value: string) => void;
};

export function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 appearance-none rounded-md border border-ink-700 bg-ink-800 pr-8 pl-3 text-sm text-fg hover:border-ink-600"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 size-4 text-fg-muted"
        aria-hidden
      />
    </label>
  );
}
