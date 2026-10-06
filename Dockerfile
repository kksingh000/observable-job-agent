# Builds the static Jobvis console, then a Python image that serves both the
# console/API and the Gradio wizard from one process on one port (see
# src/job_scout/render_entry.py for why that split exists).

# ---- stage 1: build the static Jobvis console (web/out) ----
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

# ---- stage 2: python runtime ----
FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies first, so they cache independently of app code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY README.md ./
RUN uv sync --frozen --no-dev

COPY --from=web /web/out ./web/out

ENV PYTHONUNBUFFERED=1 \
    JOBVIS_WEB_DIR=/app/web/out

# Render sets $PORT at runtime; 10000 is just the documented local default.
EXPOSE 10000
CMD ["sh", "-c", "uv run uvicorn job_scout.render_entry:app --host 0.0.0.0 --port ${PORT:-10000}"]
