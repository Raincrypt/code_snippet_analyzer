import { MOCK_REVIEW } from "@/mocks/review";
import { findIssueAtLine, issueKey } from "./issues";

describe("issueKey", () => {
  it("combines line and title", () => {
    expect(issueKey({ line: 3, title: "SQL injection" })).toBe("3-SQL injection");
  });
});

describe("findIssueAtLine", () => {
  const { issues } = MOCK_REVIEW;

  it("finds a finding on its first line", () => {
    expect(findIssueAtLine(issues, 3)?.category).toBe("security");
  });

  it("finds a finding inside a line range", () => {
    expect(findIssueAtLine(issues, 10)?.category).toBe("performance");
  });

  it("returns the most severe finding when several share a line", () => {
    // Line 5 has an error (crash) and an info (strict equality).
    expect(findIssueAtLine(issues, 5)?.severity).toBe("error");
  });

  it("returns undefined for a line without findings", () => {
    expect(findIssueAtLine(issues, 2)).toBeUndefined();
  });
});
