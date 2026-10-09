import { Bug, Gauge, ListChecks, Paintbrush, ShieldAlert } from "lucide-react";
import type { Category, Confidence, Effort } from "@/types/review";

export const CATEGORY_META: Record<Category, { label: string; Icon: typeof Bug }> = {
  bug: { label: "Bug", Icon: Bug },
  security: { label: "Security", Icon: ShieldAlert },
  performance: { label: "Performance", Icon: Gauge },
  style: { label: "Style", Icon: Paintbrush },
  "best-practice": { label: "Best practice", Icon: ListChecks },
};

export const CONFIDENCE_LABELS: Record<Confidence, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

export const EFFORT_LABELS: Record<Effort, string> = {
  quick: "Quick fix",
  moderate: "Moderate effort",
  larger: "Larger change",
};
