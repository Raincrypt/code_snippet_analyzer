import { formatLineRange, scoreColor } from "./severity";

describe("formatLineRange", () => {
  it("formats a single line", () => {
    expect(formatLineRange(4)).toBe("Line 4");
  });
  it("formats a range", () => {
    expect(formatLineRange(9, 11)).toBe("Lines 9–11");
  });
  it("ignores an end line that is not after the start", () => {
    expect(formatLineRange(9, 9)).toBe("Line 9");
  });
});

describe("scoreColor", () => {
  it.each([
    [9, "text-good"],
    [5, "text-sev-warning"],
    [2, "text-sev-error"],
  ])("maps score %i to %s", (score, cls) => {
    expect(scoreColor(score)).toBe(cls);
  });
});
