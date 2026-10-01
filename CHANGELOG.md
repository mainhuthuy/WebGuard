# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Frontend (Sprint 3)**: design system, layout and UI primitives, Scan / Progress / Results /
  History / About pages, `useSSE` / `useScan` / `useReport` / `useHistory` hooks, Axios API services
  (`scanApi`, `reportApi`) with DTO mappers, client-side JSON/HTML export, ESLint config and a
  Vitest + React Testing Library suite (109 tests)
- Scan `mode` (`quick` = Headers + SSL/TLS, `full` = all modules) end to end: API, database column
  (Alembic migration `9c3e1f7a2b64`), history and report output
- DNS-based SSRF protection: hostnames must resolve to public addresses only
- History page backed by the API: server-side search, grade filter, sorting, pagination, stats and
  delete with confirmation; open a past scan from the history
- Failed scans now show the reason and a "Try Again" action

### Changed
- IP-literal SSRF check uses `is_global` (also blocks CGNAT, link-local and reserved ranges)
- Target requests use a 10s timeout; the TLS handshake runs in a worker thread instead of blocking
  the event loop and honours the port in the URL
- nginx no longer buffers the SSE scan stream
- Results and About pages are lazy-loaded (main bundle 662 kB -> 331 kB)
- `docs/API_REFERENCE.md` corrected to match the implemented endpoints and payloads

### Fixed
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
