import { act, renderHook } from "@testing-library/react";
import { resolveTheme, useApplyTheme } from "./useTheme";

type Listener = () => void;

/** Controllable stand-in for window.matchMedia("(prefers-color-scheme: dark)"). */
function mockSystemTheme(initialDark: boolean) {
  let dark = initialDark;
  const listeners = new Set<Listener>();
  vi.stubGlobal("matchMedia", () => ({
    get matches() {
      return dark;
    },
    addEventListener: (_: string, l: Listener) => listeners.add(l),
    removeEventListener: (_: string, l: Listener) => listeners.delete(l),
  }));
  return {
    set(next: boolean) {
      dark = next;
      listeners.forEach((l) => l());
    },
  };
}

beforeEach(() => {
  delete document.documentElement.dataset.theme;
  document.documentElement.className = "";
  mockSystemTheme(true);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("resolveTheme", () => {
  it("returns explicit choices unchanged", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
  it("follows the system for 'system'", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });
});

describe("useApplyTheme", () => {
  it("applies the theme to <html> without a transition on first render", () => {
    renderHook(() => useApplyTheme("light"));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement).not.toHaveClass("theme-transition");
  });

  it("fades between themes, then removes the transition class", () => {
    vi.useFakeTimers();
    const { rerender } = renderHook(({ pref }) => useApplyTheme(pref), {
      initialProps: { pref: "dark" as const } as { pref: "dark" | "light" },
    });
    rerender({ pref: "light" });
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement).toHaveClass("theme-transition");
    act(() => void vi.advanceTimersByTime(400));
    expect(document.documentElement).not.toHaveClass("theme-transition");
  });

  it("follows the OS live while set to 'system'", () => {
    const system = mockSystemTheme(true);
    const { result } = renderHook(() => useApplyTheme("system"));
    expect(result.current).toBe("dark");
    act(() => system.set(false));
    expect(result.current).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("ignores OS changes when a theme is chosen explicitly", () => {
    const system = mockSystemTheme(true);
    renderHook(() => useApplyTheme("dark"));
    act(() => system.set(false));
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
