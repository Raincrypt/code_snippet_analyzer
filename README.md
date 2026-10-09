# Code Snippet Analyzer

An AI code reviewer. Paste code, get line-by-line findings, then ask follow-up questions.

```
code-snippet-analyzer/
├── frontend/   React 19 + TypeScript + Vite + Tailwind v4
├── backend/    Python FastAPI + SQLAlchemy + Alembic (stub reviewer; no AI model yet)
├── shared/     Example code + example review used by both sides (shared/demo)
├── .github/    CI: format, lint, typecheck, test, build
└── eslint.config.js, .prettierrc.json, .editorconfig   shared tooling
```

## Getting started

Requires Node 22+ and Python 3.11+.

```bash
npm install

cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cd ..

npm run dev                   # frontend on :5173, backend on :8000 (keep the venv active)
```

The frontend calls the API through relative `/api` URLs; Vite proxies them to the backend in development.
Copy `backend/.env.example` to `backend/.env` to change backend settings. See `backend/README.md`.

## Commands (run from the repo root)

| Command                             | What it does               |
| ----------------------------------- | -------------------------- |
| `npm run dev`                       | Start frontend and backend |
| `npm run dev:frontend` / `:backend` | Start one of them          |
| `npm test`                          | Run all tests              |
| `npm run typecheck`                 | tsc (frontend) + mypy      |
| `npm run lint` / `lint:fix`         | ESLint + ruff              |
| `npm run format` / `format:check`   | Prettier + ruff format     |
| `npm run build`                     | Frontend production build  |

## Conventions

- **Strict typing** in both apps: TypeScript (`noUncheckedIndexedAccess`) and mypy `strict`.
- **Validation at the boundaries**: Zod in the frontend, Pydantic in the backend. The JSON shapes match (camelCase).
- **One interface for the network** (`frontend/src/api/types.ts`). A mock implements it today; swap in an HTTP client without touching components.
- **Logic in hooks, layout in components.** Hooks in `frontend/src/hooks` own state and async work and cancel in-flight requests.
- **Import with `@/`** inside the frontend instead of `../../`.
- **Tests sit next to the code** they cover (`Thing.tsx`, `Thing.test.tsx`).
- **Accessible by default**: labelled controls, visible focus, live regions for async content, `motion-safe:` for animation.

## Status

The frontend runs on mock data and shows the full review format: summary, findings with fixes, time and space complexity, recognised algorithms, and measured metrics. The backend is a complete base: reviews and chat messages are saved in a database, with a stub reviewer in place of an AI model. Next: connect the frontend to the API with streaming, then add an AI model behind the `Reviewer` interface.
