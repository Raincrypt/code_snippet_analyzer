# Frontend

React 19, TypeScript, Vite, Tailwind CSS v4. Run from the repo root with `npm run dev:frontend`.

```
src/
├── api/          ReviewApi interface + mock implementation
├── components/   Shared UI (ui/ = primitives) and app chrome
├── features/     review/ (editor, results, cards) and chat/
├── hooks/        useReview, useChat (state + async + cancellation), usePersistentNumber
├── mocks/        Sample code and review fixture
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
