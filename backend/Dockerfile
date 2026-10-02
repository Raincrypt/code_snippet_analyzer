FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_FORMAT=json

WORKDIR /srv

# Install dependencies first so this layer is cached until pyproject.toml changes.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[postgres]"

COPY alembic.ini ./
COPY migrations ./migrations

# Run as an unprivileged user.
RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 8000

# Applies pending migrations, then starts the server. With several instances, run
# `alembic upgrade head` once as a separate release step instead of on every start.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
