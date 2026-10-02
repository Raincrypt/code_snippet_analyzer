import { z } from "zod";

// Zod schemas are the single source of truth: they validate data at runtime
// AND give us TypeScript types. In week 3 this file moves to packages/shared
// so the API and the UI can never disagree about a review's shape.

export const SeveritySchema = z.enum(["error", "warning", "info", "suggestion"]);
export const CategorySchema = z.enum(["bug", "security", "performance", "style", "best-practice"]);

export const CodeIssueSchema = z.object({
  line: z.number().int().positive(),
  endLine: z.number().int().positive().optional(),
  severity: SeveritySchema,
  category: CategorySchema,
  title: z.string().min(1).max(120),
  description: z.string().min(1),
  suggestion: z.string().optional(),
});

export const ReviewResultSchema = z.object({
  summary: z.string(),
  score: z.number().int().min(1).max(10),
  issues: z.array(CodeIssueSchema),
  positives: z.array(z.object({ line: z.number().int().positive(), comment: z.string() })),
});

export type Severity = z.infer<typeof SeveritySchema>;
export type Category = z.infer<typeof CategorySchema>;
export type CodeIssue = z.infer<typeof CodeIssueSchema>;
export type ReviewResult = z.infer<typeof ReviewResultSchema>;

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

// A discriminated union: TypeScript narrows the type based on `status`,
// so you can't read `result` unless the review actually succeeded.
export type ReviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: ReviewResult }
  | { status: "error"; message: string };
