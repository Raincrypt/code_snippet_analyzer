import { MOCK_REVIEW } from "@/mocks/review";
import type { CodeIssue } from "@/types/review";
import { DEFAULT_FILTERS, countBySeverity, organiseFindings } from "./findings";

const { issues } = MOCK_REVIEW;
const ids = (list: CodeIssue[]) => list.map((i) => i.id);

describe("organiseFindings", () => {
  it("sorts by severity, then line", () => {
    expect(ids(organiseFindings(issues, DEFAULT_FILTERS).main)).toEqual([
      "f1", // error
      "f3", // warnings by line: 4, 5, 17
      "f2",
      "f4",
      "f6", // info
      "f5", // suggestion
    ]);
  });

  it("can sort by line, using severity to break ties", () => {
    const sorted = organiseFindings(issues, { ...DEFAULT_FILTERS, sort: "line" }).main;
    expect(ids(sorted)).toEqual(["f6", "f1", "f3", "f5", "f2", "f4"]);
  });

  it("filters by severity", () => {
    const filters = { ...DEFAULT_FILTERS, severities: new Set(["error" as const]) };
    expect(ids(organiseFindings(issues, filters).main)).toEqual(["f1"]);
  });

  it("filters by category", () => {
    const filters = { ...DEFAULT_FILTERS, category: "performance" as const };
    expect(ids(organiseFindings(issues, filters).main)).toEqual(["f3", "f4"]);
  });

  it("combines filters", () => {
    const filters = {
      ...DEFAULT_FILTERS,
      severities: new Set(["warning" as const]),
      category: "bug" as const,
    };
    expect(ids(organiseFindings(issues, filters).main)).toEqual(["f2"]);
  });

  it("keeps low-confidence findings apart", () => {
    const unsure = issues.map((i) => (i.id === "f6" ? { ...i, confidence: "low" as const } : i));
    const result = organiseFindings(unsure, DEFAULT_FILTERS);
    expect(ids(result.doubleCheck)).toEqual(["f6"]);
    expect(ids(result.main)).not.toContain("f6");
  });

  it("does not modify the input", () => {
    const before = ids([...issues]);
    organiseFindings(issues, { ...DEFAULT_FILTERS, sort: "line" });
    expect(ids([...issues])).toEqual(before);
  });
});

describe("countBySeverity", () => {
  it("counts every severity, including zeros", () => {
    expect(countBySeverity(issues)).toEqual({ error: 1, warning: 3, info: 1, suggestion: 1 });
    expect(countBySeverity([])).toEqual({ error: 0, warning: 0, info: 0, suggestion: 0 });
  });
});
