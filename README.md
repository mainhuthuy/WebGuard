<div align="center">

# 🛡️ WebGuard

### Automated Web Security Assessment & Misconfiguration Scanner

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)

*A standalone web security scanner that audits HTTP configuration end to end — headers, cookies, TLS, CORS, page content, and server behaviour — against **~100 checks across 7 modules**, with real-time progress, a weighted A+–F scorecard, and an optional AI-written remediation plan using your own API key.*

[🔗 Live Demo](https://webguard.vercel.app) · [📖 Documentation](docs/) · [🐛 Report Bug](.github/ISSUE_TEMPLATE/bug_report.md) · [✨ Request Feature](.github/ISSUE_TEMPLATE/feature_request.md)

</div>

---

> ⚠️ **Work in Progress** — This project is currently under active development.

## 🚀 Features

- **7 scanning modules, ~100 checks** — every check is passive or deliberately low-risk (see [Scope & Safety](#️-scope--safety) below); nothing exploits a target or requires authorization to run
  - **Security Headers** — presence *and* value quality (CSP `unsafe-inline`/wildcard sources, short HSTS `max-age`, obsolete `X-Frame-Options`, unsafe `Referrer-Policy`...)
  - **Cookies** — `Secure`/`HttpOnly`/`SameSite`, `SameSite=None`, broken `__Host-`/`__Secure-` prefixes, overly broad `Domain`, long-lived session cookies
  - **SSL/TLS** — certificate expiry/hostname-mismatch/self-signed/untrusted-chain reported individually, legacy TLS 1.0/1.1, weak cipher suites (RC4/3DES/anonymous), missing TLS 1.3
  - **Information Disclosure** — 35+ sensitive paths (`.env`, `.git`, cloud credentials, SQL/zip backups, debug consoles, admin tools...) matched by *content signature* (not just a 200 status, so SPAs don't cause false alarms), plus directory listing, verbose error pages, internal IP leaks, version-revealing headers
  - **CORS** — wildcard origin, origin reflection, `Origin: null`, and partial-match whitelist bypass
  - **Page Content** — mixed content, missing Subresource Integrity, password forms over HTTP, insecure form actions, vulnerable JS library versions, plus one low-risk active check: login-form username enumeration
  - **HTTP Configuration** — HTTPS not enforced, `TRACE` enabled, risky methods in `OPTIONS`, missing `security.txt`, open redirect via common query parameters
- **Quick or Full scans** — Quick runs Headers + SSL/TLS in seconds; Full runs all 7 modules
- **Real-time progress** — Server-Sent Events stream each module's status as the scan runs
- **Security Scorecard** — grades your site from A+ to F with severity-weighted scoring
- **Actionable Remediation** — every finding ships with a concrete fix, not just a label
- **"Explain with AI" (BYOK)** — paste your own API key (several providers offer a free tier) and get a plain-language risk summary plus a prioritised remediation plan, generated from the findings a scan already produced — no new requests are ever sent to the scanned site, and your key never leaves your browser except to call the provider you chose
- **Scan History** — paginated, filterable record of past scans with stats
- **Export Reports** — generate JSON or self-contained HTML reports for documentation

## 🛡️ Scope & Safety

WebGuard scans any `http(s)://` URL you give it, protected by SSRF checks (no localhost, private IPs or cloud metadata addresses). Almost every check only **reads** what the target already serves publicly (headers, cookies, TLS handshake, well-known paths, the home page's HTML) — nothing is exploited. Two checks are active but deliberately scoped to stay low-risk: an open-redirect probe (a harmless, non-resolving test URL — see [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606)) and a login-form check that sends exactly two failed login attempts with a fixed, unguessable password (never enough attempts to be a brute force, and the password can't possibly succeed). WebGuard deliberately does **not** include XSS/SQLi injection or credential brute-forcing — see [`docs/ROADMAP_40_DAYS.md`](docs/ROADMAP_40_DAYS.md#-bổ-sung-sau-kế-hoạch-gốc-ngoài-40-ngày) for the reasoning. Always get authorization before scanning a site you don't own.

## 📦 Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd WebGuard

# Start with Docker (recommended)
cd docker
docker compose up -d

# Open in browser
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

For detailed setup instructions, see [SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+ · FastAPI · SQLAlchemy · SQLite |
| Frontend | React · TypeScript · Vite · npm |
| DevOps | Docker · Docker Compose · GitHub Actions |
| Testing | pytest · Vitest · React Testing Library |
| Code Quality | Ruff · Black · ESLint · Prettier · Pre-commit |

## 📖 Documentation

- [Setup Guide](docs/SETUP_GUIDE.md) — Installation from scratch
- [Dev Workflow](docs/DEV_WORKFLOW.md) — Daily development process
- [Git Conventions](docs/GIT_CONVENTIONS.md) — Branching & commit standards
- [Architecture](docs/ARCHITECTURE.md) — System design & data flow
- [API Reference](docs/API_REFERENCE.md) — Backend API documentation

## ⚖️ Disclaimer

WebGuard is designed for **authorized security assessment only**. Users are responsible for ensuring they have proper authorization before scanning any target website. The authors are not liable for any misuse of this tool.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
