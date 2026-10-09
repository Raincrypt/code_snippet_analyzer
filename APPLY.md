# Phase A1 changes: how to apply

This zip contains only the files that are new or changed since your last full zip. Paths are relative
to the repository root.

1. Unzip it **at the repository root**, overwriting files when asked.
2. Delete these three files, which the new review panel replaces:
   - `frontend/src/features/review/AnnotationCard.tsx`
   - `frontend/src/features/review/AnnotationCard.test.tsx`
   - `frontend/src/features/review/ResultsPanel.tsx`
3. Delete your local database, because the saved review format changed: `rm backend/app.db`
4. No new packages are needed (no `npm install` or `pip install`).
5. Check everything (with the Python virtual environment active):
   `npm run format:check && npm run lint && npm run typecheck && npm test && npm run build`
6. You can delete this `APPLY.md` afterwards.

Also included, because they were not in your last zip:
- the history removal (frontend History button; backend list and delete endpoints)
- the editor height fix (`flex-1` on the editor section in `CodeEditor.tsx`)
