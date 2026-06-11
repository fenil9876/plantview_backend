# syntax=docker/dockerfile:1

# ----------------------------------------------------------------------------
# PlantView backend (FastAPI + uvicorn). Slim Python base, single worker —
# small image, low memory. The DB is external (configured via env).
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first for better layer caching.
# psycopg2-binary ships a prebuilt libpq, so no apt build tools are needed.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code (migrations included so `alembic upgrade head` can be run).
COPY . .

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Honour $PORT when present (Render injects it); default to 8000 locally.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request,sys; p=os.getenv('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://localhost:{p}/health').status==200 else 1)" || exit 1

# Single worker is plenty for ~10 users and keeps memory minimal.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
