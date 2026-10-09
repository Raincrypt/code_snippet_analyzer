const SUPERSCRIPTS: Record<string, string> = {
  "0": "⁰",
  "1": "¹",
  "2": "²",
  "3": "³",
  "4": "⁴",
  "5": "⁵",
  "6": "⁶",
  "7": "⁷",
  "8": "⁸",
  "9": "⁹",
  n: "ⁿ",
};

/** O(n^2) -> O(n²), O(2^n) -> O(2ⁿ). Other text is left alone. */
export function formatBigO(value: string): string {
  return value.replace(/\^(\d+|n)/g, (_, power: string) =>
    [...power].map((c) => SUPERSCRIPTS[c] ?? c).join(""),
  );
}

type GrowthClass = { label: string; name: string; match: RegExp };

// The common growth rates, fastest to slowest. `match` is tested against a lowercase,
// whitespace-free version of the text, so "O(n log n)" and "o(nlogn)" are both recognised.
const GROWTH_CLASSES: readonly GrowthClass[] = [
  { label: "O(1)", name: "Constant", match: /^o\(1\)$/ },
  { label: "O(log n)", name: "Logarithmic", match: /^o\(log\(?n\)?\)$/ },
  { label: "O(n)", name: "Linear", match: /^o\(n\)$/ },
  { label: "O(n log n)", name: "Linearithmic", match: /^o\(nlog\(?n\)?\)$/ },
  { label: "O(n²)", name: "Quadratic", match: /^o\(n(\^2|²)\)$/ },
  { label: "O(n³)", name: "Cubic", match: /^o\(n(\^3|³)\)$/ },
  { label: "O(2ⁿ)", name: "Exponential", match: /^o\(2(\^n|ⁿ)\)$/ },
  { label: "O(n!)", name: "Factorial", match: /^o\(n!\)$/ },
];

export const GROWTH_SCALE = GROWTH_CLASSES.map(({ label, name }) => ({ label, name }));

/** Position on GROWTH_SCALE (0 = fastest), or null for shapes it does not cover, like O(V + E). */
export function complexityRank(value: string): number | null {
  const normalised = value.toLowerCase().replace(/\s+/g, "");
  const index = GROWTH_CLASSES.findIndex((c) => c.match.test(normalised));
  return index === -1 ? null : index;
}

export type GrowthTone = "good" | "fair" | "warn" | "bad";

/** How worrying a growth rate is for typical input sizes. */
export function growthTone(rank: number): GrowthTone {
  if (rank <= 2) return "good";
  if (rank === 3) return "fair";
  if (rank <= 5) return "warn";
  return "bad";
}
