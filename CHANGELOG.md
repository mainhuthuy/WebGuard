# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Backend Dockerfile rewritten as a multi-stage build**: a `builder` stage installs the app
  into an isolated virtualenv, a slim `runtime` stage copies only that venv plus the files the
  app actually needs (`app/`, `templates/`, `alembic.ini`) and runs as a non-root user. The image
  no longer installs `curl` — the `HEALTHCHECK` now uses Python's stdlib `urllib` instead.
  Added `backend/.dockerignore`.
- **Each Docker Compose file now has an explicit `name:`** (`webguard`, `webguard-dev`,
  `webguard-demo`). Without it, all three shared one project name (the `docker/` directory),
  so their images/networks/volumes collided — confirmed by actually reproducing it: running
  the dev stack then the prod stack without `--build` silently reused the dev-target image
  despite `target: production` being set, because Compose skips building when an image with
  that name already exists.
- `docker-compose.yml`'s `BACKEND_PORT`, `FRONTEND_PORT` and `WEBGUARD_CORS_ORIGINS` are now
  overridable via `docker/.env` (copy from `docker/.env.example`) — previously that file
  wasn't wired to anything and copying it had no effect.
- **CI/CD and DevSecOps pipelines (GitHub Actions)** — written but not yet run on GitHub
  (only the frontend lint/tsc/build and `npm audit` commands were run locally; see `docs/learning/4.4`–`4.7`):
  - `backend-ci.yml`: Ruff lint + Pytest with coverage report artifact on every PR/push touching
    `backend/**`.
  - `frontend-ci.yml`: ESLint, `tsc -b` type check and Vite build as three parallel jobs on
    `frontend/**` changes. The Vitest suite is deliberately not in CI yet (one flaky test was seen).
  - `cd-publish-images.yml`: builds the backend and frontend (`production` target) images and pushes
    them to GitHub Container Registry on pushes to `main` and `vX.Y.Z` tags — never on pull requests.
    Tags: `main`, `sha-<short>`, semver, and `latest` only for release tags.
  - `security.yml`: `pip-audit` (runtime deps), `npm audit --omit=dev`, and Trivy image scans on PRs
    and weekly. Only fixable HIGH/CRITICAL findings fail the build. The publish workflow also runs
    Trivy *before* pushing, so a vulnerable image never reaches the registry.
- **One-click dev setup**: `scripts/setup-dev.ps1` (Windows) and `scripts/setup-dev.sh` (Linux/macOS/
  Git Bash) check prerequisites, create `backend/.venv`, install backend + frontend dependencies and
  copy the `.env` files without overwriting existing ones. `-CheckOnly` / `--check` only verifies
  prerequisites; `-Docker` / `--docker` starts the hot-reload Docker stack instead.
- `CONTRIBUTING.md`: clone-to-merged-PR guide for newcomers, with the exact commands CI runs.
- Learning notes `docs/learning/4.4`–`4.10`.
- **Frontend production image now runs nginx fully unprivileged** (port 8080, non-root `nginx`
  user) and serves the security headers WebGuard's own `HeadersModule` checks for (CSP,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`,
  `Cross-Origin-Opener-Policy`), `server_tokens off`, gzip, and correct caching (`no-cache` for
  `index.html`, `immutable` for hashed `/assets/*`). New `frontend/security-headers.conf`.
- **"Explain with AI" (BYOK — Bring Your Own Key)**: a new Settings page lets each user paste
  their own API key for Google Gemini, Groq, OpenRouter, OpenAI or Anthropic (several offer a
  free tier), stored only in that browser's `localStorage`. On the results page, one click sends
  the scan's already-collected findings to the chosen provider and gets back a plain-language
  risk summary plus a detailed, prioritised remediation plan — formatted as Markdown. The AI never
  sends any new request to the scanned target; it only reads findings the scanner already
  produced. The key is relayed through the backend for exactly one request and is never logged or
  stored server-side. New endpoint: `POST /scan/{id}/explain` (`backend/app/services/ai_explainer.py`,
  `backend/app/schemas/ai.py`).
- **Frontend (Sprint 3)**: design system, layout and UI primitives, Scan / Progress / Results /
  History / About pages, `useSSE` / `useScan` / `useReport` / `useHistory` hooks, Axios API services
  (`scanApi`, `reportApi`) with DTO mappers, client-side JSON/HTML export, ESLint config and a
  Vitest + React Testing Library suite (112 tests)
- Scan `mode` (`quick` = Headers + SSL/TLS, `full` = all modules) end to end: API, database column
  (Alembic migration `9c3e1f7a2b64`), history and report output
- DNS-based SSRF protection: hostnames must resolve to public addresses only
- History page backed by the API: server-side search, grade filter, sorting, pagination, stats and
  delete with confirmation; open a past scan from the history
- Failed scans now show the reason and a "Try Again" action

- **Scanner coverage 25 → 100 checks across 7 modules** (all passive, no injection or exploitation):
  - `headers`: Cross-Origin-Resource-Policy, plus weak *values* — CSP `unsafe-inline` / `unsafe-eval` /
    wildcard sources, short HSTS `max-age`, missing `includeSubDomains`, invalid `X-Frame-Options` /
    `X-Content-Type-Options`, unsafe `Referrer-Policy`
  - `cookies`: `SameSite=None`, broken `__Host-` / `__Secure-` prefixes, session cookies with a broad
    `Domain` or a lifetime over 30 days
  - `ssl_tls`: certificate expired / hostname mismatch / self-signed / untrusted chain reported
    individually, weak cipher suites (RC4, 3DES, NULL/anonymous), missing TLS 1.3
  - `information`: 33 more sensitive paths (git/svn/aws/ssh secrets, SQL and zip backups, debug
    consoles, phpinfo, admin tools, API docs…), directory listing, verbose error messages, internal IP
    disclosure, ASP.NET / generator version headers. Files are matched by content signature and a
    random-URL probe detects "200 for everything" sites, so SPAs no longer cause false positives
  - `cors`: `null` origin and prefix/suffix origin-validation bypass
  - new `content` module: mixed content, missing SRI, password forms over HTTP, insecure form actions,
    forms without CSRF token, vulnerable JS library versions, meta generator version
  - new `http_config` module: HTTP not redirected to HTTPS, TRACE enabled, risky methods in `OPTIONS`,
    missing `security.txt`, open redirect via common query parameters (probed with a single harmless,
    non-resolving `.invalid` test URL — nothing is ever actually fetched from it)
  - `content` module gains one active, non-destructive check: username enumeration on login forms,
    via exactly two failed login attempts (a made-up username and "admin", both with the same wrong
    password) compared for differing status codes, error text or response length. Not a brute force —
    the password cannot possibly be correct, so the account can never actually be logged into

### Changed
- README Quick Start now mentions the setup scripts and links to `CONTRIBUTING.md`
- `cert_expired` is now actually reachable: expired certificates used to be reported as a generic
  `ssl_connection_failed` because verification failed before the expiry check ran
- Full scans run 7 modules (Quick is unchanged: Headers + SSL/TLS)
- About page now documents every check (25 across 5 modules) with its risk level, what is looked
  for and why it matters, plus a guide to the four risk levels; a backend test keeps this catalogue
  in sync with the scanner modules
- IP-literal SSRF check uses `is_global` (also blocks CGNAT, link-local and reserved ranges)
- Target requests use a 10s timeout; the TLS handshake runs in a worker thread instead of blocking
  the event loop and honours the port in the URL
- nginx no longer buffers the SSE scan stream
- Results and About pages are lazy-loaded (main bundle 662 kB -> 331 kB)
- `docs/API_REFERENCE.md` corrected to match the implemented endpoints and payloads

### Fixed
- `GET /report/{id}/export?format=html` would have thrown `TemplateNotFound` when run from the
  Docker image — the Dockerfile never copied `templates/` into it. Also fixed: `docker-compose.yml`
  / `docker-compose.dev.yml` pointed `WEBGUARD_DB_URL` at `/app/webguard.db` while the persistent
  volume was mounted at `/app/data` — the two never overlapped, so the database was silently lost
  on every container recreation. Both now point at `/app/data/webguard.db`.
- `docker-compose.yml`'s frontend service never specified a build `target`, so Docker built the
  Dockerfile's *last* stage (`dev`, the Vite dev server) instead of the intended nginx production
  build — confirmed by actually running `docker compose up` rather than just reading the file.
  Now pins `target: production`.
- Scanner accuracy: cookie flags are matched by attribute name (a cookie named `session_secure` no
  longer counts as having `Secure`); CORS credentials are critical only when an arbitrary origin is
  reflected (a fixed origin with credentials is a valid config); servers that still accept
  TLS 1.0/1.1 are now detected by probing each legacy version (including legacy-only servers that
  previously showed up as a plain connection failure); `/wp-admin` redirects to the WordPress login
  are detected
- Severity distribution bar on the results page filled only 50% of its width (the summary `total`
  was counted twice)
- Learning notes (`docs/learning`) reviewed against the code: corrected the SSRF validator example,
  the 9-header count, scoring/grade claims, Jinja2 autoescape, SSE reconnect caveats, error-format
  and logging descriptions; all Sprint 3 theory consolidated in `docs/learning/3.0_Sprint3_Frontend_Theory.md`
- Existing SQLite databases created before the `mode` column are upgraded automatically on startup
- Backend tests no longer write to the development `webguard.db` (isolated temporary database)
- `SSE` stream no longer auto-reconnects (reconnecting would restart a running scan)
- "New Scan" in the sidebar returned to a blank form while a scan was running instead of its progress
- `tsc` build errors from unused imports/variables

### Initial
- Initial project structure and development environment setup
- Backend scaffolding with FastAPI
- Frontend scaffolding with React + Vite + TypeScript
- Development documentation (SETUP_GUIDE, DEV_WORKFLOW, GIT_CONVENTIONS)
- Docker and Docker Compose configuration
- Pre-commit hooks for code quality
