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
# --extra groq: SCOUT_MODEL/SCOUT_TAILOR_MODEL can point at a groq: model
# (the free-tier alternative .env.example suggests), which needs
# langchain-groq installed up front — it isn't pulled in by the base
# dependency set, so without this the app fails at runtime with
# "Initializing ChatGroq requires the langchain-groq package" the first
# time a groq: model is actually used.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra groq

COPY src/ src/
COPY README.md ./
RUN uv sync --frozen --no-dev --extra groq

COPY --from=web /web/out ./web/out

ENV PYTHONUNBUFFERED=1 \
    JOBVIS_WEB_DIR=/app/web/out

# Render sets $PORT at runtime; 10000 is just the documented local default.
EXPOSE 10000
# Run the venv's uvicorn directly (not `uv run uvicorn ...`): `uv run` does
# its own implicit sync on every start with no --no-dev, which would
# re-install the whole dev dependency group (jupyter, ruff, pytest, ...)
# on every cold boot. The venv is already correct from the build step above.
CMD ["sh", "-c", "/app/.venv/bin/uvicorn job_scout.render_entry:app --host 0.0.0.0 --port ${PORT:-10000}"]
