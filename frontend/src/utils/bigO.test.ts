import { GROWTH_SCALE, complexityRank, formatBigO, growthTone } from "./bigO";

describe("formatBigO", () => {
  it.each([
    ["O(n^2)", "O(n²)"],
    ["O(n^3)", "O(n³)"],
    ["O(2^n)", "O(2ⁿ)"],
    ["O(n^10)", "O(n¹⁰)"],
    ["O(n log n)", "O(n log n)"],
    ["O(n²)", "O(n²)"],
  ])("turns %s into %s", (input, expected) => {
    expect(formatBigO(input)).toBe(expected);
  });
});

describe("complexityRank", () => {
  it.each([
    ["O(1)", 0],
    ["O(log n)", 1],
    ["O(n)", 2],
    ["O(n log n)", 3],
    ["O(n²)", 4],
    ["O(n^2)", 4],
    ["O(n³)", 5],
    ["O(2^n)", 6],
    ["O(2ⁿ)", 6],
    ["O(n!)", 7],
    ["o(nlogn)", 3],
    ["O( n log(n) )", 3],
  ])("ranks %s as %i", (input, rank) => {
    expect(complexityRank(input)).toBe(rank);
  });

  it("returns null for shapes outside the common classes", () => {
    expect(complexityRank("O(V + E)")).toBeNull();
    expect(complexityRank("O(n·m)")).toBeNull();
  });

  it("orders the scale from fastest to slowest", () => {
    expect(GROWTH_SCALE.map((g) => g.name)[0]).toBe("Constant");
    expect(GROWTH_SCALE.at(-1)?.name).toBe("Factorial");
  });
});

describe("growthTone", () => {
  it("grades growth rates", () => {
    expect(growthTone(0)).toBe("good");
    expect(growthTone(2)).toBe("good");
    expect(growthTone(3)).toBe("fair");
    expect(growthTone(4)).toBe("warn");
    expect(growthTone(7)).toBe("bad");
  });
});
