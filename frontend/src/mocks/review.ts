import { ReviewResultSchema, type ReviewResult } from "@/types/review";
import type { ReplyStyle } from "@/types/settings";

export const SAMPLE_CODE = `async function getUser(req, res) {
  const id = req.query.id;
  const rows = await db.query("SELECT * FROM users WHERE id = " + id);
  var user = rows[0];
  if (user.role == "admin") {
    console.log("admin login", user.password);
  }
  const posts = [];
  for (let i = 0; i < user.postIds.length; i++) {
    posts.push(await db.query("SELECT * FROM posts WHERE id = " + user.postIds[i]));
  }
  res.json({ user, posts });
}`;

// Parsing the mock through the schema means a typo here fails loudly,
// exactly like a malformed API response will later.
export const MOCK_REVIEW: ReviewResult = ReviewResultSchema.parse({
  summary:
    "The handler works for the happy path, but it builds SQL from user input and assumes the user always exists. Fix the injection risk first; the rest is cleanup.",
  score: 4,
  issues: [
    {
      line: 3,
      severity: "error",
      category: "security",
      title: "SQL injection through string concatenation",
      description:
        "The `id` query parameter goes straight into the SQL string, so a request like `?id=1 OR 1=1` returns every user.",
      suggestion: 'const rows = await db.query("SELECT * FROM users WHERE id = $1", [id]);',
    },
    {
      line: 5,
      severity: "error",
      category: "bug",
      title: "Crash when the user does not exist",
      description:
        "`rows[0]` is undefined for an unknown id, so `user.role` throws a TypeError and the request fails with a 500.",
      suggestion: 'if (!user) return res.status(404).json({ error: "User not found" });',
    },
    {
      line: 6,
      severity: "warning",
      category: "security",
      title: "Password written to the logs",
      description:
        "Logging `user.password` leaks credentials to anyone who can read your logs. Log the user id instead.",
      suggestion: 'console.log("admin login", user.id);',
    },
    {
      line: 9,
      endLine: 11,
      severity: "warning",
      category: "performance",
      title: "One query per post (N+1)",
      description:
        "The loop awaits a separate query for every post id, so latency grows with the number of posts.",
      suggestion:
        'const posts = await db.query("SELECT * FROM posts WHERE id = ANY($1)", [user.postIds]);',
    },
    {
      line: 5,
      severity: "info",
      category: "best-practice",
      title: "Use strict equality",
      description: "`==` allows type coercion. Prefer `===` so comparisons behave predictably.",
      suggestion: 'if (user.role === "admin") {',
    },
    {
      line: 4,
      severity: "suggestion",
      category: "style",
      title: "Prefer const over var",
      description:
        "`var` is function-scoped and hoisted. `const` states that the binding never changes.",
      suggestion: "const user = rows[0];",
    },
  ],
  positives: [{ line: 1, comment: "Async/await keeps the control flow easy to follow." }],
});

export const MOCK_REPLIES: Record<ReplyStyle, string> = {
  brief: "Use a parameterized query so the database never treats input as code.",
  balanced:
    "Good question. The safest fix is a parameterized query: pass the value separately from the SQL text so the database never treats it as code. I can show the same change for the posts query if that helps.",
  detailed: [
    "Good question. Here is the reasoning, step by step.",
    "1. The problem: the query is built by joining strings, so whatever the caller sends in `id` becomes part of the SQL itself. A value like `1 OR 1=1` changes the meaning of the query.",
    '2. The fix: send the SQL and the value separately. The database parses the SQL first, then treats the value strictly as data: `db.query("SELECT * FROM users WHERE id = $1", [id])`.',
    "3. Apply it everywhere: the posts query in the loop has the same flaw, and replacing the loop with one `= ANY($1)` query also removes the N+1 problem.",
    "I can walk through the rewritten handler if you would like.",
  ].join("\n\n"),
};
