import { Text } from "@codemirror/state";
import { lineRangeOffsets, worstSeverityByLine } from "./issueMarkers";

describe("worstSeverityByLine", () => {
  it("marks every line in a range", () => {
    const map = worstSeverityByLine([{ line: 2, endLine: 4, severity: "warning" }], 10);
    expect([...map.keys()]).toEqual([2, 3, 4]);
  });

  it("keeps the most severe finding on a shared line", () => {
    const map = worstSeverityByLine(
      [
        { line: 3, severity: "info" },
        { line: 3, severity: "error" },
        { line: 3, severity: "suggestion" },
      ],
      10,
    );
    expect(map.get(3)).toBe("error");
  });

  it("ignores lines past the end of the document", () => {
    const map = worstSeverityByLine([{ line: 8, endLine: 12, severity: "error" }], 9);
    expect([...map.keys()]).toEqual([8, 9]);
  });

  it("returns nothing for no findings", () => {
    expect(worstSeverityByLine([], 5).size).toBe(0);
  });
});

describe("lineRangeOffsets", () => {
  const doc = Text.of(["first", "second", "third"]); // offsets: 0-5, 6-12, 13-18

  it("covers one whole line", () => {
    expect(lineRangeOffsets(doc, 2)).toEqual({ from: 6, to: 12 });
  });

  it("covers a range of lines", () => {
    expect(lineRangeOffsets(doc, 1, 3)).toEqual({ from: 0, to: 18 });
  });

  it("clamps out-of-range lines to the document", () => {
    expect(lineRangeOffsets(doc, 0, 99)).toEqual({ from: 0, to: 18 });
  });

  it("never ends before it starts", () => {
    expect(lineRangeOffsets(doc, 3, 1)).toEqual({ from: 13, to: 18 });
  });
});
