import type { Severity } from "@/types/review";
import { SEVERITY_STYLES } from "@/utils/severity";

type BadgeProps = { severity: Severity };

export function Badge({ severity }: BadgeProps) {
  const s = SEVERITY_STYLES[severity];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${s.chip}`}
    >
      <span className={`size-1.5 rounded-full ${s.dot}`} aria-hidden />
      {s.label}
    </span>
  );
}
