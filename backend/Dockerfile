# syntax=docker/dockerfile:1
# ============================================================================
# Backend Dockerfile — multi-stage build
#
# Stage 1 "builder": installs the app + its dependencies into an isolated
#   virtualenv (/opt/venv). This is the only stage that would ever need a
#   compiler/dev headers for a dependency that ships no prebuilt wheel.
# Stage 2 "runtime": a fresh python:3.12-slim with NOTHING copied over except
#   the finished virtualenv and the source files the app actually needs to
#   run (app/, templates/, alembic.ini) — no pip cache, no build tooling, no
#   extra apt packages (not even curl — the healthcheck below uses Python's
#   own stdlib instead). Runs as a non-root user.
# ============================================================================

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Layer-caching trick: the dependency install is the slow step, so it must NOT be
# invalidated by source edits. setuptools only needs an `app/` package to exist to
# generate the editable-install metadata (`[tool.setuptools] packages = ["app"]` in
# pyproject.toml), so we install against an empty stub first and copy the real source
# AFTERWARDS. Editing app/ then only re-runs the cheap COPY layers below.
#
# The editable install just registers a path redirect back to /app/app (it copies no
# files), so the real `app/` must end up at exactly that path — in this stage and in
# the runtime stage. templates/ must stay a SIBLING of app/: Jinja2's loader in
# app/services/report.py finds it via a relative path, not as a package resource.
#
# The BuildKit cache mount keeps pip's download cache OUTSIDE the image, so even when
# pyproject.toml changes and the layer has to rerun, wheels are not downloaded again
# (and the cache adds nothing to the final image size).
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-compile -e .

# Real source, copied last so edits never trigger a dependency reinstall.
COPY app/ ./app/
COPY alembic.ini ./
COPY templates/ ./templates/


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Run as a non-root user (defence in depth: a RCE in a dependency doesn't
# automatically hand over root inside the container).
RUN groupadd --system --gid 1000 webguard \
    && useradd --system --uid 1000 --gid webguard --home-dir /app --shell /usr/sbin/nologin webguard

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic.ini ./
COPY --from=builder /app/templates ./templates

# SQLite file lives here when WEBGUARD_DB_URL points at ./data/webguard.db
# (see docker/docker-compose.yml) — owned by the app user so it can write to it.
RUN mkdir -p /app/data && chown -R webguard:webguard /app
USER webguard

EXPOSE 8000

# No curl in this image on purpose (see header) — urllib is stdlib, so this
# adds zero extra packages/MB to the final image.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys,urllib.request as u; sys.exit(0 if u.urlopen('http://localhost:8000/api/v1/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
