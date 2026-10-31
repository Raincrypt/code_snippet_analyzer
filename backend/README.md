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

| Method | Path                         | Purpose                                                                             |
| ------ | ---------------------------- | ----------------------------------------------------------------------------------- |
| GET    | `/api/health`                | Liveness (process is up)                                                            |
| GET    | `/api/ready`                 | Readiness (database answers)                                                        |
| GET    | `/api/reviewer/status`       | Whether the model server is up and has the model                                    |
| POST   | `/api/reviews/stream`        | Review a snippet; streams `stage`, then `result` (or `error`) as server-sent events |
| POST   | `/api/reviews`               | Same review, returned as one JSON response                                          |
| GET    | `/api/reviews/{id}`          | One review with its chat messages                                                   |
| POST   | `/api/reviews/{id}/messages` | Ask a follow-up question                                                            |

Errors always look like `{"error": {"code", "message", "requestId", "details"?}}`.

## Configuration

Environment variables (or `backend/.env`):

| Variable                                | Default                        | Notes                                                                                       |
| --------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------- |
| `ENVIRONMENT`                           | `development`                  | `production` turns off `/api/docs`                                                          |
| `DATABASE_URL`                          | `sqlite+aiosqlite:///./app.db` | PostgreSQL: `postgresql://user:pass@host/db` (install `.[postgres]`)                        |
| `LOG_LEVEL` / `LOG_FORMAT`              | `INFO` / `console`             | Use `json` in production                                                                    |
| `CORS_ORIGINS`                          | empty                          | Comma-separated; only if the browser calls the API directly                                 |
| `REVIEWER`                              | `stub`                         | `stub` (placeholder) or `llm` (see "The AI model"; more `LLM_*` settings in `.env.example`) |
| `MAX_CODE_CHARS` / `MAX_QUESTION_CHARS` | 100000 / 4000                  | Input limits                                                                                |

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

## The AI model (Qwen2.5-Coder through Ollama)

Reviews use the placeholder until you switch to the model:

```bash
# 1. Install Ollama (https://ollama.com), then fetch the model (about 5 GB for the 7B size)
ollama pull qwen2.5-coder:7b
# 2. Start it with a bigger context window, or long snippets are silently cut off
OLLAMA_CONTEXT_LENGTH=16384 ollama serve
# 3. Point the backend at it (in backend/.env) and restart
REVIEWER=llm
```

Larger sizes (`qwen2.5-coder:14b`, `:32b`) review better if your hardware can run them: set
`LLM_MODEL`. Any server with an OpenAI-compatible chat API works (`LLM_BASE_URL`), including
vLLM, LM Studio and hosted services (`LLM_API_KEY`). `GET /api/reviewer/status` says whether the
server is up and the model is installed.

How a review works (`app/services/llm_reviewer.py`):

1. `app/prompts/review_v2.py` builds the prompt: the code with line numbers, the rules, and an
   example. The code is marked as data, so instructions inside it are ignored.
2. One streamed model call, whose output must match `LlmReview` (`llm_schema.py`). Progress steps
   follow the fields as the model writes them.
3. If the reply is not valid, the model gets one chance to correct it.
4. For Python, `static_python.py` reads the code with the standard `ast` module and reports what
   it can prove: SQL built from strings, `eval`/`exec`, `shell=True`, mutable default arguments,
   unclosed files, bare `except`, exponential recursion and nested loops over one collection.
   Bad-practice rules cover hard-coded secrets, MD5/SHA-1 for passwords, `pickle.loads`,
   `yaml.load`, `verify=False`, requests without a timeout, `os.system` with built text,
   `tempfile.mktemp`, Flask `debug=True`, `tar.extractall`, swallowed `except Exception: pass`,
   changing a list while looping over it, `list.pop(0)` in a loop, `x in list` on a growing list,
   nesting five or more levels deep, `global` writes, shadowed built-ins and `== None`. It
   recognises binary search, merge sort, quick sort, BFS, DFS, Dijkstra, topological sort,
   sieve of Eratosthenes, Kadane, matrix multiplication, Floyd-Warshall, LRU cache, union-find,
   bubble sort, Euclid's algorithm and memoised recursion (backtracking such as N-Queens is
   deliberately not called DFS), and measures function count, longest function and nesting depth. The
   standard figures and wording for those algorithms come from `algorithm_catalog.py`.
5. `postprocess.py` combines both and checks the model's part with plain code: each finding's
   quoted code must be (close to) the real code, otherwise the finding is dropped; a rule finding
   replaces the model's version of the same problem; invented function names, "missing docstring"
   remarks on documented functions and "dynamic programming" claims without caching are removed;
   Big-O strings are cleaned. Ids, priority order, score and verdict come from fixed rules: the
   score is a weighted average capped by the weakest area and by the worst finding (an error
   caps it at 5, a security error at 4). Every correction is listed under `limitations`.

Rule-based checks cover Python only; other languages rely on the model alone.

Speed depends almost entirely on hardware: on a CPU, a 7B model takes about a minute per review.
A smaller model (`qwen2.5-coder:3b`) is roughly twice as fast and less accurate; run the evals
with both and compare.

Only one model call runs at a time (`LLM_MAX_CONCURRENCY`); other requests wait. Snippets over
`LLM_MAX_CODE_CHARS` are rejected.

### Measuring quality

```bash
python -m evals.run_evals            # runs evals/cases.json against the configured model
python -m evals.run_evals -k sql fib # only some cases
python -m evals.run_evals --tag bad-practice          # one group of cases
python -m evals.run_evals --tag complex-algorithm --json after-c2.json
```

Cases carry tags: `basic`, `complex-algorithm` (Dijkstra, quick sort, union-find, DP, N-Queens,
sieve, KMP, LRU cache, Floyd-Warshall, ...) and `bad-practice` (security holes, performance traps,
Python/JavaScript/Go/Java mistakes). The summary also shows totals per tag. On a CPU each case
takes about a minute, so use `--tag` or `-k` for quick checks.

It reports how many known bugs, complexities and algorithms the model got right (a finding on the
right line only counts if it also names the real problem), how many replies were valid, and the time
per review. Cases marked `"rules"` in `cases.json` are also run in the test suite without a model. Run it after every change to the model or the prompt.
`python evals/fake_model_server.py` starts a stand-in server for trying the app without a model.

### Adding a different kind of reviewer

Write a class with `name`, `model_name`, `check()`, `review()` and `answer()` (see `StubReviewer`),
add its name to `Settings.reviewer`, and return it from `build_reviewer`. Raise `ReviewerError` (with
a `public_message`) on failure; the API turns it into a 502.

## Not built yet

- Accounts and per-user data. **Without them, anyone who can reach the API can read and delete
  every review, so do not expose this publicly yet.**
- Rate limits and usage budgets.
- Request body size limits at the proxy, and security headers.

## Review format (v2)

`app/schemas.py` defines what a reviewer must return: purpose, summary, verdict, score and per-area
breakdown, priority fixes, findings (explanation, impact, quoted evidence, fix, references,
confidence, effort), **time/space complexity in Big-O** (overall and per function, with best,
average and worst cases), **detected algorithms** (name, evidence, complexity, alternatives), measured
metrics and limitations. Big-O strings are validated (`O(...)`), finding ids must be unique, and
priority fixes must refer to real findings. Reviews saved with an older format cannot be read:
delete `backend/app.db` after pulling this change.
