import { ReviewResultSchema, type ReviewResult } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";
// The sample code and its review live in /shared/demo so the backend's stub uses the very same
// files. Both sides validate them against their own schema, so the contract cannot drift.
import sampleCode from "../../../shared/demo/sample-code.txt?raw";
import demoReview from "../../../shared/demo/review.json";

export const SAMPLE_CODE = sampleCode.replace(/\r\n/g, "\n").replace(/\n+$/, "");

// Parsing through the schema means a mistake in the data fails loudly,
// exactly like a malformed API response will later.
export const MOCK_REVIEW: ReviewResult = ReviewResultSchema.parse(demoReview);

/** What the mock returns for the "finds nothing" preview. */
export const CLEAN_REVIEW: ReviewResult = ReviewResultSchema.parse({
  purpose: "Adds two numbers and returns the result.",
  summary:
    "Nothing to flag. The code is small, clear and handles its inputs correctly. The work is constant, regardless of the input.",
  verdict: "looks-good",
  score: 9,
  scoreBreakdown: {
    correctness: { score: 9, reason: "Does exactly what its name says." },
    security: { score: 10, reason: "Nothing here touches untrusted data." },
    performance: { score: 10, reason: "A single addition." },
    readability: { score: 9, reason: "Clear names and no surprises." },
  },
  priorityFixes: [],
  issues: [],
  positives: [{ line: 1, comment: "A single, focused responsibility." }],
  complexity: {
    time: "O(1)",
    space: "O(1)",
    explanation: "One addition, no loops and no allocation, so both time and memory are constant.",
    functions: [
      {
        name: "add",
        startLine: 1,
        endLine: 3,
        bestCase: "O(1)",
        averageCase: "O(1)",
        worstCase: "O(1)",
        space: "O(1)",
        explanation: "A single operation regardless of the input.",
      },
    ],
  },
  algorithms: [],
  metrics: { totalLines: 3, codeLines: 3, commentLines: 0, blankLines: 0, longestLine: 24 },
  limitations: [],
});

export const MOCK_REPLIES: Record<ReplyStyle, string> = {
  brief:
    "Sort a copy instead: `[...scores].sort((a, b) => b - a).slice(0, n)`. It leaves the input alone and runs in O(n log n).",
  balanced:
    "Good question. The loops swap items inside `scores` itself, because `var sorted = scores` only copies the reference. Sorting a copy, `[...scores].sort((a, b) => b - a)`, leaves the caller's array untouched and also replaces the quadratic bubble sort with an O(n log n) sort. I can show the same change for hasDuplicates if that helps.",
  detailed: [
    "Good question. Here is the reasoning, step by step.",
    "1. The problem: `var sorted = scores;` does not copy the array. Both names point at the same list, so every swap in the loops changes the caller's data too.",
    "2. The fix: make a real copy first with `[...scores]`. Now the sort works on its own list and the input stays as it was.",
    "3. While you are there, the hand-written loops can go. `.sort((a, b) => b - a)` orders numbers from highest to lowest in O(n log n) time instead of O(n²). The comparator matters: without it, JavaScript sorts numbers as text and puts 10 before 9.",
    "4. Final version: `return [...scores].sort((a, b) => b - a).slice(0, n);`",
    "I can walk through the same idea for hasDuplicates if you would like.",
  ].join("\n\n"),
};
