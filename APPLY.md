# Update: rules + test cases (Phase C-1 and C-2) and the model status dot

Unzip over the project root and choose "replace" for existing files.

1. DELETE the old prompt file (a zip cannot delete): `backend\app\prompts\review_v1.py`
   (or run `delete-old-files.bat` from the project root).
2. Backend check:  cd backend  then  .venv\Scripts\python.exe -m pytest -q
3. Docker:  docker compose down  then  docker compose up -d --build
   Without Docker: restart start-all.bat.

Includes the httpx fix (backend\pyproject.toml now lists httpx as a normal dependency).

## What is in it
- C-1: rule-based checks + algorithm catalogue + review_v2 prompt + stricter scoring
- C-2: 48 extra eval cases (tags complex-algorithm / bad-practice), 19 more rules, 9 more detectors
- Model status dot (green / yellow / red) in the footer
Quality run (optional, ~1 min per case on CPU):
  .venv\Scripts\python.exe -m evals.run_evals --tag bad-practice --json bad.json
