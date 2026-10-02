import { useCallback, useEffect, useState } from "react";
import { DEFAULT_SETTINGS, SettingsSchema, type Settings } from "@/types/settings";

// Keep in sync with the inline script in index.html, which reads `theme` before first paint.
export const SETTINGS_STORAGE_KEY = "code-snippet-analyzer:settings";

export function readSettings(): Settings {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    return SettingsSchema.parse(raw ? JSON.parse(raw) : {});
  } catch {
    return DEFAULT_SETTINGS; // storage blocked, or the stored JSON is corrupt
  }
}

/** User settings, validated on load and remembered in localStorage. */
export function useSettings() {
  const [settings, setSettings] = useState<Settings>(readSettings);

  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // Storage may be blocked; settings still apply for this session.
    }
  }, [settings]);

  const update = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => ({ ...prev, ...patch }));
  }, []);

  return [settings, update] as const;
}
