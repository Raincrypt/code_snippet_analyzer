# Frontend

React 19, TypeScript, Vite, Tailwind CSS v4. Run from the repo root with `npm run dev:frontend`.

```
src/
├── api/          ReviewApi interface + mock implementation
├── components/   Shared UI (ui/ = primitives) and app chrome
├── features/     review/ (editor, results bar, panel/) and chat/
├── hooks/        useReview, useChat (state + async + cancellation), usePersistentNumber
├── mocks/        Example code and review (read from /shared/demo)
├── types/        Zod schemas and inferred types
├── utils/        Pure helpers (severity styles, languages)
└── index.css     Design tokens (colors, fonts, animation)
```

Use the "Next mock review" selector in the status bar to preview the issues, no-issues and error states.

## Layout

- The chat panel is resizable (drag the divider, or focus it and use ←/→, Shift for bigger steps, Home/End for the limits).
- The review panel below the editor starts minimized. Click its bar to open it; when open, its top edge is resizable too (↑/↓).
- Panel sizes are remembered in localStorage. Resizing is desktop-only (≥1024px); on smaller screens the panels stack.

## Settings

Open **Settings** in the header. All settings are saved in the browser (`code-snippet-analyzer:settings`) and validated on load.

| Setting          | Options                   | Default  |
| ---------------- | ------------------------- | -------- |
| Theme            | Light, Dark, System       | System   |
| Editor font size | Small, Medium, Large      | Medium   |
| Reply style      | Brief, Balanced, Detailed | Balanced |

System follows the OS and switches live. Theme changes fade over about 300ms (instant if the OS asks for reduced motion). The theme is applied by a small script in `index.html` before the first paint, so there is no flash on reload.

## The review panel

Collapsed by default; click the bar to open it. Four tabs:

| Tab        | Shows                                                                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Overview   | Verdict, score, summary, what the code does, complexity at a glance, "fix these first", score breakdown, positives, limitations                        |
| Findings   | Filter by severity or category, sort, expand/collapse. Each finding: what's wrong, why it matters, the code, a fix, references                         |
| Complexity | Time and space in Big-O (with where it sits among common growth rates), per-function best/average/worst cases, recognised algorithms with alternatives |
| Metrics    | Figures measured from the code itself, not estimated                                                                                                   |

While a review runs it shows step-by-step progress. If the code is edited afterwards the panel says the review is out of date and the editor's line markers are hidden.

The review format is defined in `src/types/review.ts` (Zod) and mirrored by `backend/app/schemas.py` (Pydantic). Both sides validate `/shared/demo/review.json`, so they cannot drift apart.
