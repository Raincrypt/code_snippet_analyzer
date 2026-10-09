import { z } from "zod";

// Zod schemas are the source of truth for the shape of a review ("format v2"): they validate
// data at runtime AND give us TypeScript types. The backend defines the same shape in
// backend/app/schemas.py. Fields the backend may leave out arrive as null, hence `.nullish()`.

export const SeveritySchema = z.enum(["error", "warning", "info", "suggestion"]);
export const CategorySchema = z.enum(["bug", "security", "performance", "style", "best-practice"]);
export const ConfidenceSchema = z.enum(["high", "medium", "low"]);
export const EffortSchema = z.enum(["quick", "moderate", "larger"]);
export const VerdictSchema = z.enum([
  "fix-before-use",
  "needs-work",
  "mostly-fine",
  "looks-good",
  "not-assessed", // the placeholder reviewer did not look at the code
]);

/** Big-O notation such as O(1), O(n log n), O(n²), O(2^n). */
export const BigOSchema = z
  .string()
  .max(40)
  .regex(/^O\(.+\)$/, "Expected Big-O notation like O(n)");

const LineSchema = z.number().int().positive();

export const ReferenceSchema = z.object({
  label: z.string().min(1).max(120),
  url: z.string().nullish(),
});

export const FixSchema = z.object({
  description: z.string().min(1),
  before: z.string().nullish(),
  after: z.string().min(1),
});

export const CodeIssueSchema = z.object({
  id: z.string().min(1).max(20),
  line: LineSchema,
  endLine: LineSchema.nullish(),
  severity: SeveritySchema,
  category: CategorySchema,
  title: z.string().min(1).max(120),
  explanation: z.string().min(1), // what is wrong
  impact: z.string().min(1), // why it matters
  evidence: z.string().min(1), // the exact code, starting at `line`
  confidence: ConfidenceSchema,
  effort: EffortSchema,
  fix: FixSchema.nullish(),
  references: z.array(ReferenceSchema).default([]),
});

export const PositiveSchema = z.object({ line: LineSchema, comment: z.string() });

export const AreaScoreSchema = z.object({
  score: z.number().int().min(1).max(10),
  reason: z.string().min(1),
});

export const ScoreBreakdownSchema = z.object({
  correctness: AreaScoreSchema,
  security: AreaScoreSchema,
  performance: AreaScoreSchema,
  readability: AreaScoreSchema,
});

export const FunctionComplexitySchema = z.object({
  name: z.string().min(1),
  startLine: LineSchema,
  endLine: LineSchema,
  bestCase: BigOSchema.nullish(),
  averageCase: BigOSchema.nullish(),
  worstCase: BigOSchema,
  space: BigOSchema,
  explanation: z.string().min(1),
});

export const ComplexitySchema = z.object({
  time: BigOSchema, // headline: worst case of the code as a whole
  space: BigOSchema,
  explanation: z.string().min(1), // how the figures were worked out
  functions: z.array(FunctionComplexitySchema),
});

export const AlgorithmAlternativeSchema = z.object({
  name: z.string().min(1),
  time: BigOSchema,
  space: BigOSchema,
  tradeoff: z.string().min(1),
});

export const DetectedAlgorithmSchema = z.object({
  name: z.string().min(1).max(80),
  category: z.string().min(1).max(40),
  confidence: ConfidenceSchema,
  startLine: LineSchema,
  endLine: LineSchema,
  evidence: z.string().min(1), // what in the code shows this algorithm
  summary: z.string().min(1),
  time: BigOSchema,
  space: BigOSchema,
  assessment: z.string().min(1), // is it a good choice here?
  alternatives: z.array(AlgorithmAlternativeSchema).default([]),
});

/** Facts measured from the code itself. null means "not measured". */
export const MetricsSchema = z.object({
  totalLines: z.number().int().nonnegative(),
  codeLines: z.number().int().nonnegative(),
  commentLines: z.number().int().nonnegative(),
  blankLines: z.number().int().nonnegative(),
  longestLine: z.number().int().nonnegative(),
  functionCount: z.number().int().nonnegative().nullish(),
  longestFunctionLines: z.number().int().nonnegative().nullish(),
  maxNestingDepth: z.number().int().nonnegative().nullish(),
});

export const ReviewResultSchema = z
  .object({
    purpose: z.string(),
    summary: z.string(),
    verdict: VerdictSchema,
    score: z.number().int().min(1).max(10).nullish(),
    scoreBreakdown: ScoreBreakdownSchema.nullish(),
    priorityFixes: z.array(z.string()).max(3),
    issues: z.array(CodeIssueSchema),
    positives: z.array(PositiveSchema),
    complexity: ComplexitySchema.nullish(),
    algorithms: z.array(DetectedAlgorithmSchema).default([]),
    metrics: MetricsSchema,
    limitations: z.array(z.string()).default([]),
  })
  .superRefine((review, ctx) => {
    const ids = review.issues.map((i) => i.id);
    if (new Set(ids).size !== ids.length) {
      ctx.addIssue({ code: "custom", message: "issue ids must be unique", path: ["issues"] });
    }
    for (const id of review.priorityFixes) {
      if (!ids.includes(id)) {
        ctx.addIssue({
          code: "custom",
          message: `priorityFixes refers to unknown issue ${id}`,
          path: ["priorityFixes"],
        });
      }
    }
    if (review.verdict !== "not-assessed" && (review.score == null || !review.scoreBreakdown)) {
      ctx.addIssue({
        code: "custom",
        message: "score and scoreBreakdown are required for an assessed review",
        path: ["score"],
      });
    }
  });

export type Severity = z.infer<typeof SeveritySchema>;
export type Category = z.infer<typeof CategorySchema>;
export type Confidence = z.infer<typeof ConfidenceSchema>;
export type Effort = z.infer<typeof EffortSchema>;
export type Verdict = z.infer<typeof VerdictSchema>;
export type Fix = z.infer<typeof FixSchema>;
export type CodeIssue = z.infer<typeof CodeIssueSchema>;
export type ScoreBreakdown = z.infer<typeof ScoreBreakdownSchema>;
export type FunctionComplexity = z.infer<typeof FunctionComplexitySchema>;
export type Complexity = z.infer<typeof ComplexitySchema>;
export type DetectedAlgorithm = z.infer<typeof DetectedAlgorithmSchema>;
export type Metrics = z.infer<typeof MetricsSchema>;
export type ReviewResult = z.infer<typeof ReviewResultSchema>;

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

/** The steps a review goes through, in order. Shown as progress while it runs. */
export const REVIEW_STAGES = ["prepare", "understand", "analyse", "complexity", "verify"] as const;
export type ReviewStage = (typeof REVIEW_STAGES)[number];

// A discriminated union: TypeScript narrows the type based on `status`,
// so you can't read `result` unless the review actually succeeded.
export type ReviewState =
  | { status: "idle" }
  | { status: "loading"; stage?: ReviewStage | null }
  | { status: "success"; result: ReviewResult }
  | { status: "error"; message: string };
