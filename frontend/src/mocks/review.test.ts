import { MOCK_REVIEW, SAMPLE_CODE } from "./review";

const normalise = (text: string) => text.replace(/\s+/g, " ").trim();
const lines = SAMPLE_CODE.split("\n");

describe("the example review matches the example code", () => {
  it("quotes real code starting on the cited line", () => {
    for (const issue of MOCK_REVIEW.issues) {
      issue.evidence.split("\n").forEach((quoted, offset) => {
        expect(normalise(quoted), `${issue.id} line ${issue.line + offset}`).toBe(
          normalise(lines[issue.line - 1 + offset] ?? ""),
        );
      });
    }
  });

  it("only cites lines that exist", () => {
    const ranges = [
      ...MOCK_REVIEW.issues.map((i) => [i.line, i.endLine ?? i.line]),
      ...MOCK_REVIEW.positives.map((p) => [p.line, p.line]),
      ...MOCK_REVIEW.algorithms.map((a) => [a.startLine, a.endLine]),
      ...(MOCK_REVIEW.complexity?.functions.map((f) => [f.startLine, f.endLine]) ?? []),
    ];
    for (const [start, end] of ranges) {
      expect(start).toBeGreaterThanOrEqual(1);
      expect(end).toBeLessThanOrEqual(lines.length);
    }
  });

  it("reports line counts that match the code", () => {
    const { metrics } = MOCK_REVIEW;
    expect(metrics.totalLines).toBe(lines.length);
    expect(metrics.blankLines).toBe(lines.filter((l) => !l.trim()).length);
    expect(metrics.commentLines).toBe(lines.filter((l) => l.trim().startsWith("//")).length);
    expect(metrics.longestLine).toBe(Math.max(...lines.map((l) => l.length)));
  });

  it("covers every severity so the interface can be judged", () => {
    expect(new Set(MOCK_REVIEW.issues.map((i) => i.severity)).size).toBe(4);
  });
});
