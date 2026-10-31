import { useEffect, useState } from "react";

type Health = () => Promise<{ reviewer: string; model?: string | null }>;

/** A short description of which reviewer the backend is using, or null while unknown. */
export function useBackendLabel(health: Health | null): string | null {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!health) return;
    let cancelled = false;
    health().then(
      ({ reviewer, model }) => {
        if (cancelled) return;
        setLabel(
          reviewer === "stub"
            ? "Reviewer: placeholder (no AI model connected)"
            : `Reviewer: ${model ?? reviewer}`,
        );
      },
      () => {
        if (!cancelled) setLabel("Backend not reachable");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [health]);

  return health ? label : null;
}
