import { MOCK_REVIEW } from "@/mocks/review";
import { findIssueAtLine, issueKey } from "./issues";

describe("issueKey", () => {
  it("is the finding's id", () => {
    expect(issueKey({ id: "f3" })).toBe("f3");
  });
});

describe("findIssueAtLine", () => {
  const { issues } = MOCK_REVIEW;

  it("finds a finding on its first line", () => {
    expect(findIssueAtLine(issues, 3)?.id).toBe("f1");
  });

  it("finds a finding inside a line range", () => {
    expect(findIssueAtLine(issues, 10)?.id).toBe("f3");
  });

  it("returns the most severe finding when several share a line", () => {
    // Line 4 has a warning (bubble sort) and a suggestion (var).
    expect(findIssueAtLine(issues, 4)?.severity).toBe("warning");
  });

  it("returns undefined for a line without findings", () => {
    expect(findIssueAtLine(issues, 15)).toBeUndefined();
  });
});
