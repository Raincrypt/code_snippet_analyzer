import demoReview from "../../../shared/demo/review.json";
import { MOCK_REVIEW } from "@/mocks/review";
import { ReviewResultSchema } from "./review";

const base = () => structuredClone(demoReview) as Record<string, unknown>;
const assessedBase = () => {
  const data = base();
  delete data.score;
  delete data.scoreBreakdown;
  return data;
};

describe("ReviewResultSchema", () => {
  it("accepts the shared example review", () => {
    expect(ReviewResultSchema.safeParse(demoReview).success).toBe(true);
    expect(MOCK_REVIEW.complexity?.time).toBe("O(n²)");
  });

  it("accepts nulls where the backend leaves fields out", () => {
    const data = base() as { issues: Record<string, unknown>[] };
    data.issues[0] = { ...data.issues[0], endLine: null, fix: null };
    expect(ReviewResultSchema.safeParse(data).success).toBe(true);
  });

  it("rejects duplicate finding ids", () => {
    const data = base() as { issues: { id: string }[] };
    data.issues[1]!.id = data.issues[0]!.id;
    expect(ReviewResultSchema.safeParse(data).success).toBe(false);
  });

  it("rejects priority fixes that point at nothing", () => {
    expect(ReviewResultSchema.safeParse({ ...base(), priorityFixes: ["nope"] }).success).toBe(
      false,
    );
  });

  it("allows at most three priority fixes", () => {
    const data = { ...base(), priorityFixes: ["f1", "f2", "f3", "f4"] };
    expect(ReviewResultSchema.safeParse(data).success).toBe(false);
  });

  it("requires a score for an assessed review", () => {
    expect(ReviewResultSchema.safeParse(assessedBase()).success).toBe(false);
  });

  it("allows no score when the code was not assessed", () => {
    const data = { ...assessedBase(), verdict: "not-assessed", issues: [], priorityFixes: [] };
    expect(ReviewResultSchema.safeParse(data).success).toBe(true);
  });

  it.each(["n squared", "fast", "O()", "O(n"])("rejects %j as Big-O", (bad) => {
    const data = base() as { complexity: { time: string } };
    data.complexity.time = bad;
    expect(ReviewResultSchema.safeParse(data).success).toBe(false);
  });
});
