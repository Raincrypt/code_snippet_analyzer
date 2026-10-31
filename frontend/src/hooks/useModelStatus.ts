import { useEffect, useState } from "react";

export type ModelLevel = "checking" | "ok" | "warn" | "down";
export type ModelIndicator = { level: ModelLevel; text: string };

type Fetcher = (signal?: AbortSignal) => Promise<{
  state: "ready" | "model-missing" | "unreachable";
  detail: string;
}>;

const CHECKING: ModelIndicator = { level: "checking", text: "AI model: checking…" };
export const POLL_MS = 30_000;

/**
 * Whether the AI model can take a review right now, re-checked every 30 seconds:
 * green = ready, yellow = checking or the model is not installed yet, red = not reachable.
 * Null when there is no backend to ask.
 */
export function useModelStatus(fetchStatus: Fetcher | null): ModelIndicator | null {
  const [indicator, setIndicator] = useState<ModelIndicator>(CHECKING);

  useEffect(() => {
    if (!fetchStatus) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const { state, detail } = await fetchStatus!(controller.signal);
        if (controller.signal.aborted) return;
        setIndicator(
          state === "ready"
            ? { level: "ok", text: "AI model: available" }
            : state === "model-missing"
              ? { level: "warn", text: `AI model: ${detail}` }
              : { level: "down", text: "AI model: not reachable" },
        );
      } catch {
        if (controller.signal.aborted) return;
        // The backend itself did not answer, so the model's state cannot be known either.
        setIndicator({ level: "down", text: "AI model: backend not reachable" });
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, POLL_MS);
    }

    setIndicator(CHECKING);
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [fetchStatus]);

  return fetchStatus ? indicator : null;
}
