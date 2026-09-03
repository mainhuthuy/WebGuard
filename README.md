<div align="center">

# 🛡️ WebGuard

### Automated Web Security Assessment & Misconfiguration Scanner

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)

*A standalone web security scanner that identifies misconfigurations, missing security headers, SSL issues, and information disclosure vulnerabilities — with actionable remediation guidance.*

[🔗 Live Demo](https://webguard.vercel.app) · [📖 Documentation](docs/) · [🐛 Report Bug](.github/ISSUE_TEMPLATE/bug_report.md) · [✨ Request Feature](.github/ISSUE_TEMPLATE/feature_request.md)

</div>

---

> ⚠️ **Work in Progress** — This project is currently under active development.

## 🚀 Features

- **Security Headers Analysis** — Checks for CSP, HSTS, X-Frame-Options, and more
- **Cookie Security Audit** — Validates HttpOnly, Secure, SameSite flags
- **SSL/TLS Health Check** — Certificate validation, protocol version detection
- **Information Disclosure Detection** — Scans for exposed `.env`, `.git`, server banners
- **CORS Misconfiguration** — Identifies overly permissive cross-origin policies
- **Security Scorecard** — Grades your site from A+ to F with weighted scoring
- **Actionable Remediation** — Provides fix examples for Nginx, Apache, Express.js
- **Export Reports** — Generate JSON or HTML reports for documentation

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
| Frontend | React · TypeScript · Vite · pnpm |
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
