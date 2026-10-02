import { loadLanguage } from "./languages";

describe("loadLanguage", () => {
  it.each(["javascript", "typescript", "python", "go", "rust", "java"])(
    "loads %s",
    async (language) => {
      expect(await loadLanguage(language)).toBeTruthy();
    },
  );

  it("falls back to plain text for an unknown language", async () => {
    expect(await loadLanguage("cobol")).toEqual([]);
  });

  it("reuses the loaded pack", () => {
    expect(loadLanguage("python")).toBe(loadLanguage("python"));
  });
});
