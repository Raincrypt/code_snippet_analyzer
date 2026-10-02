import { useEffect, useState } from "react";

/** Like useState for a number, remembered in localStorage (safe if storage is unavailable). */
export function usePersistentNumber(key: string, initial: number) {
  const [value, setValue] = useState(() => {
    try {
      const stored = localStorage.getItem(key);
      const parsed = stored === null ? NaN : Number(stored);
      return Number.isFinite(parsed) ? parsed : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, String(value));
    } catch {
      // Storage may be blocked (private mode, quota); the value just won't persist.
    }
  }, [key, value]);

  return [value, setValue] as const;
}
