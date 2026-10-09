# Backend

FastAPI + SQLAlchemy (async) + Alembic. Python 3.11+.

No AI model is connected yet. The API runs end to end with a **stub reviewer**: it returns a canned
example review for the built-in sample code (`/shared/demo`) and a plain "not assessed" result, with
real line counts, for anything else;
a real model plugs in through one interface (see "Adding an AI model").

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # optional
```

Then from the repo root (with the venv active): `npm run dev` starts frontend and backend.
The `dev:backend` script applies migrations and starts the server on http://localhost:8000.
Interactive API docs: http://localhost:8000/api/docs

## Layout

```
app/
├── main.py            create_app(): middleware, error handlers, routes, startup/shutdown
├── config.py          Settings from environment variables
├── schemas.py         Request/response models (camelCase JSON, same shapes as the frontend)
├── models.py          Database tables: reviews, messages
├── repository.py      All database queries
├── db.py              Engine and per-request session
├── errors.py          One error shape for every failure
├── middleware.py      Request IDs and request logging
├── logging_config.py  Console or JSON logs
├── api/               health.py, reviews.py (thin route handlers)
└── services/
    └── reviewer.py    The Reviewer interface + the stub. This is where an AI model plugs in.
migrations/            Alembic migrations
tests/
```

## Endpoints

| Method | Path                         | Purpose                           |
| ------ | ---------------------------- | --------------------------------- |
| GET    | `/api/health`                | Liveness (process is up)          |
| GET    | `/api/ready`                 | Readiness (database answers)      |
| POST   | `/api/reviews`               | Review a snippet and save it      |
| GET    | `/api/reviews/{id}`          | One review with its chat messages |
| POST   | `/api/reviews/{id}/messages` | Ask a follow-up question          |

Errors always look like `{"error": {"code", "message", "requestId", "details"?}}`.

## Configuration

Environment variables (or `backend/.env`):

| Variable                                | Default                        | Notes                                                                |
| --------------------------------------- | ------------------------------ | -------------------------------------------------------------------- |
| `ENVIRONMENT`                           | `development`                  | `production` turns off `/api/docs`                                   |
| `DATABASE_URL`                          | `sqlite+aiosqlite:///./app.db` | PostgreSQL: `postgresql://user:pass@host/db` (install `.[postgres]`) |
| `LOG_LEVEL` / `LOG_FORMAT`              | `INFO` / `console`             | Use `json` in production                                             |
| `CORS_ORIGINS`                          | empty                          | Comma-separated; only if the browser calls the API directly          |
| `REVIEWER`                              | `stub`                         | Which Reviewer implementation to use                                 |
| `MAX_CODE_CHARS` / `MAX_QUESTION_CHARS` | 100000 / 4000                  | Input limits                                                         |

## Database

```bash
python -m alembic upgrade head                              # apply migrations
python -m alembic revision --autogenerate -m "describe it"  # after changing app/models.py
python -m alembic check                                     # fails if models and migrations differ
```

## Checks (also run in CI)

```bash
ruff check . && ruff format --check . && mypy app && pytest -q
```

## Adding an AI model

1. Create a class with `name`, `async review(code, language) -> ReviewOutcome` and
   `async answer(request) -> AnswerOutcome` (see `StubReviewer` in `app/services/reviewer.py`).
2. Add its name to `Settings.reviewer` in `app/config.py` and return it from `build_reviewer`.
3. Raise `ReviewerError` on failure; the API turns it into a 502.

`ReviewOutcome` already carries `model`, `prompt_version` and token counts, and the `reviews` table
already has columns for them. The model's output must satisfy `ReviewResult` in `app/schemas.py`.

## Not built yet

- Accounts and per-user data. **Without them, anyone who can reach the API can read and delete
  every review, so do not expose this publicly yet.**
- Streaming responses, rate limits and usage budgets.
- Request body size limits at the proxy, and security headers.

## Review format (v2)

`app/schemas.py` defines what a reviewer must return: purpose, summary, verdict, score and per-area
breakdown, priority fixes, findings (explanation, impact, quoted evidence, fix, references,
confidence, effort), **time/space complexity in Big-O** (overall and per function, with best,
average and worst cases), **detected algorithms** (name, evidence, complexity, alternatives), measured
metrics and limitations. Big-O strings are validated (`O(...)`), finding ids must be unique, and
priority fixes must refer to real findings. Reviews saved with an older format cannot be read:
delete `backend/app.db` after pulling this change.
