# Contributing to WebGuard

Thanks for helping out! This guide gets you from a fresh clone to a merged pull request. If anything here is wrong or unclear, that's a bug in this file — please fix it too.

## 1. Get it running

### One command (recommended)

```powershell
# Windows
.\scripts\setup-dev.ps1
```
```bash
# Linux / macOS / Git Bash
./scripts/setup-dev.sh
```

This checks your tools (Python 3.12+, Node 18+), creates `backend/.venv`, installs backend and frontend dependencies, and copies `.env.example` → `.env` (it never overwrites an existing `.env`, and is safe to re-run). Add `-CheckOnly` / `--check` to only verify prerequisites.

Then run the app in two terminals:

```bash
# Backend  (http://localhost:8000/docs)
cd backend && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload

# Frontend (http://localhost:5173)
cd frontend && npm run dev
```

### Or with Docker (hot-reload, nothing to install locally)

```bash
./scripts/setup-dev.sh --docker        # Windows: .\scripts\setup-dev.ps1 -Docker
# equivalent: docker compose -f docker/docker-compose.dev.yml up -d --build
```

Editing files under `backend/app` or `frontend/src` reloads automatically. For the production-style stack (nginx, built bundle): `cd docker && docker compose up -d`.

More detail: [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

## 2. Project layout

| Path | What lives there |
|---|---|
| `backend/app/modules/` | Scanner modules (headers, cookies, TLS, CORS, content, …) — one class per module, all extending `BaseModule` |
| `backend/app/api/`, `services/`, `schemas/`, `models/` | FastAPI routes, business logic, Pydantic schemas, SQLAlchemy models |
| `backend/tests/` | `unit/` and `integration/` tests |
| `frontend/src/` | React + TypeScript + Vite UI |
| `docker/` | Compose files (prod, dev, demo) |
| `docs/` | Architecture, API reference, conventions; `docs/learning/` holds a write-up per roadmap task |

Start with [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the big picture.

## 3. Workflow

1. **Branch** from `develop` using a prefix: `feature/…`, `fix/…`, `docs/…`, `ci/…`, `refactor/…`.
2. **Make your change** — keep it focused; one PR, one purpose.
3. **Run the same checks CI runs** (below) locally.
4. **Commit** using [Conventional Commits](docs/GIT_CONVENTIONS.md), e.g. `feat(backend): add robots.txt check`. Subject in English, lowercase, imperative, ≤ 72 chars.
5. **Open a PR** against `develop` (see the checklist in [docs/GIT_CONVENTIONS.md](docs/GIT_CONVENTIONS.md)).

Optional but recommended: `pip install pre-commit && pre-commit install` to run formatting/lint hooks on every commit.

## 4. Checks your PR must pass

CI runs these on every PR — run them first and you'll rarely see a red build.

| Area | Command (from the folder) | CI workflow |
|---|---|---|
| Backend lint | `ruff check app/ tests/` | `backend-ci.yml` |
| Backend tests | `pytest` | `backend-ci.yml` |
| Frontend lint | `npm run lint` | `frontend-ci.yml` |
| Frontend types | `npx tsc -b` | `frontend-ci.yml` |
| Frontend build | `npx vite build` | `frontend-ci.yml` |
| Frontend tests | `npm test` | — (run locally) |
| Dependency / image scan | `pip-audit .` (backend), `npm audit --omit=dev --audit-level=high` (frontend) | `security.yml` |

`make lint`, `make test` and `make format` wrap most of this.

## 5. Common tasks

### Add a scanner check or module

- A **new check** goes in the relevant file under `backend/app/modules/`; return a `Finding` with a severity and remediation advice.
- A **new module** subclasses `BaseModule` (`name`, `description`, async `scan(url)`) and is registered in `scanner.py`.
- Add unit tests under `backend/tests/unit/` — cover both the "vulnerable" and the "safe" case. Avoid false positives: a check that cries wolf is worse than no check.

### Scope & safety rules for scanners

WebGuard must stay safe to point at sites people don't own. A check should only **read** what the target already serves publicly. No exploitation, no injection payloads, no credential brute-forcing, and no new request types without discussing it first (open an issue). See the *Scope & Safety* section in the [README](README.md).

### Change the database schema

Add an Alembic migration (`cd backend && alembic revision --autogenerate -m "…"`) and review it by hand before committing.

## 6. Reporting bugs and vulnerabilities

- **Bugs / ideas:** open a GitHub issue with steps to reproduce, expected vs. actual behavior, and your OS / versions.
- **Security vulnerabilities:** do **not** open a public issue — follow [SECURITY.md](SECURITY.md).

## 7. A note on AI-assisted contributions

Fine to use, but you are responsible for what you submit: understand it, run it, and keep the PR small enough for a human to review.
