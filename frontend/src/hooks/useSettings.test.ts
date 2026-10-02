import { act, renderHook } from "@testing-library/react";
import { DEFAULT_SETTINGS } from "@/types/settings";
import { SETTINGS_STORAGE_KEY, readSettings, useSettings } from "./useSettings";

beforeEach(() => localStorage.clear());

describe("readSettings", () => {
  it("returns defaults when nothing is stored", () => {
    expect(readSettings()).toEqual(DEFAULT_SETTINGS);
  });

  it("follows the system theme by default", () => {
    expect(readSettings().theme).toBe("system");
  });

  it("restores saved settings", () => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({ theme: "system", editorFontSize: "large", replyStyle: "brief" }),
    );
    expect(readSettings()).toEqual({
      theme: "system",
      editorFontSize: "large",
      replyStyle: "brief",
    });
  });

  it("falls back per field, keeping the valid ones", () => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({ theme: "purple", replyStyle: "detailed" }),
    );
    expect(readSettings()).toEqual({ ...DEFAULT_SETTINGS, replyStyle: "detailed" });
  });

  it("returns defaults for corrupt JSON", () => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, "{not json");
    expect(readSettings()).toEqual(DEFAULT_SETTINGS);
  });
});

describe("useSettings", () => {
  it("merges a patch and saves it", () => {
    const { result } = renderHook(() => useSettings());
    act(() => result.current[1]({ editorFontSize: "small" }));
    expect(result.current[0]).toEqual({ ...DEFAULT_SETTINGS, editorFontSize: "small" });
    expect(JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) ?? "{}")).toMatchObject({
      editorFontSize: "small",
    });
  });
});
