import { useEffect, useRef, useSyncExternalStore } from "react";
import type { ThemePreference } from "@/types/settings";

export type ResolvedTheme = "light" | "dark";

const DARK_QUERY = "(prefers-color-scheme: dark)";
const TRANSITION_CLASS = "theme-transition"; // styled in index.css
const TRANSITION_MS = 350;

function subscribeToSystemTheme(onChange: () => void) {
  const query = window.matchMedia?.(DARK_QUERY);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}

const getSystemPrefersDark = () => window.matchMedia?.(DARK_QUERY).matches ?? true;

export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme {
  if (preference === "system") return systemPrefersDark ? "dark" : "light";
  return preference;
}

/**
 * Applies the theme as <html data-theme="light|dark">. "system" follows the OS live.
 * Changes after the first render fade smoothly via a short-lived CSS class.
 */
export function useApplyTheme(preference: ThemePreference): ResolvedTheme {
  const systemPrefersDark = useSyncExternalStore(
    subscribeToSystemTheme,
    getSystemPrefersDark,
    () => true,
  );
  const resolved = resolveTheme(preference, systemPrefersDark);
  const isFirstRun = useRef(true);

  useEffect(() => {
    const root = document.documentElement;
    let timer: number | undefined;

    // Skip the fade on first load (the inline script in index.html already set the theme).
    if (!isFirstRun.current && root.dataset.theme !== resolved) {
      root.classList.add(TRANSITION_CLASS);
      timer = window.setTimeout(() => root.classList.remove(TRANSITION_CLASS), TRANSITION_MS);
    }
    isFirstRun.current = false;
    root.dataset.theme = resolved;

    return () => {
      window.clearTimeout(timer);
      root.classList.remove(TRANSITION_CLASS);
    };
  }, [resolved]);

  return resolved;
}
