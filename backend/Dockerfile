FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_FORMAT=json \
    # SQLite on the /data volume by default. Set DATABASE_URL to a PostgreSQL URL to use that instead.
    DATABASE_URL=sqlite+aiosqlite:////data/app.db

WORKDIR /srv

# Install dependencies first so this layer is cached until pyproject.toml or the app changes.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[postgres]"

COPY alembic.ini ./
COPY migrations ./migrations

# Run as an unprivileged user that owns the data folder.
RUN useradd --system --no-create-home appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser
VOLUME /data

EXPOSE 8000

# Lets Docker (and `depends_on: service_healthy`) know when the API answers.
HEALTHCHECK --interval=10s --timeout=4s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

# Applies pending migrations, then starts the server. With several instances, run
# `alembic upgrade head` once as a separate release step instead of on every start.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
