# WebGuard - Development Workflow

## Quy trình dev hàng ngày

### 1. Bắt đầu ngày làm việc

```powershell
# Pull code mới nhất
git checkout develop
git pull origin develop

# Kích hoạt backend virtual environment
cd backend
.\.venv\Scripts\Activate.ps1

# Chạy dev servers
cd ..
make dev
# Hoặc chạy riêng:
# Terminal 1: make dev-be
# Terminal 2: make dev-fe
```

### 2. Bắt đầu làm feature mới

```powershell
# Tạo feature branch từ develop
git checkout develop
git pull origin develop
git checkout -b feature/ten-tinh-nang

# Ví dụ:
git checkout -b feature/headers-module
git checkout -b feature/scan-page-ui
git checkout -b fix/ssl-timeout-error
```

### 3. Code & Commit

```powershell
# Xem thay đổi
git status
git diff

# Stage files
git add <file>        # Stage file cụ thể
git add .             # Stage tất cả

# Commit theo Conventional Commits format
git commit -m "feat: add security headers analysis module"
git commit -m "fix: handle timeout error in SSL checker"
git commit -m "docs: update API reference for scan endpoint"
git commit -m "test: add unit tests for cookies module"
git commit -m "chore: update dependencies"
git commit -m "ci: add backend linting to GitHub Actions"

# ⚠️ Pre-commit hooks sẽ tự động chạy!
# Nếu hooks fail → sửa lỗi → stage lại → commit lại
```

### 4. Chạy Tests trước khi Push

```powershell
# Chạy tất cả tests
make test

# Chỉ chạy backend tests
make test-be

# Chỉ chạy frontend tests
make test-fe

# Chạy linting
make lint
```

### 5. Push & Tạo Pull Request

```powershell
# Push branch lên remote
git push origin feature/ten-tinh-nang

# Tạo Pull Request trên GitHub:
# - Base branch: develop
# - Compare branch: feature/ten-tinh-nang
# - Điền PR template đầy đủ
# - Assign reviewers (nếu có)
```

### 6. Merge & Cleanup

```powershell
# Sau khi PR được approve & merge trên GitHub
git checkout develop
git pull origin develop

# Xóa branch local đã merge
git branch -d feature/ten-tinh-nang
```

---

## Lệnh thường dùng

### Backend

```powershell
# Chạy dev server
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Chạy tests
cd backend && python -m pytest

# Chạy tests với coverage
cd backend && python -m pytest --cov=app --cov-report=html

# Lint
cd backend && python -m ruff check app/ tests/

# Auto-fix lint errors
cd backend && python -m ruff check --fix app/ tests/

# Format code
cd backend && python -m black app/ tests/

# Type checking
cd backend && python -m mypy app/

# Security audit dependencies
cd backend && pip-audit
```

### Frontend

```powershell
# Chạy dev server
cd frontend && npm run dev

# Chạy tests
cd frontend && npm test

# Lint
cd frontend && npm run lint

# Format
cd frontend && npm run format

# Build production
cd frontend && npm run build
```

### Docker

```powershell
# Start (production)
cd docker && docker compose up -d

# Start (development với hot-reload)
cd docker && docker compose -f docker-compose.dev.yml up -d

# Xem logs
docker compose logs -f

# Rebuild
docker compose build --no-cache

# Dừng & xóa
docker compose down -v
```

---

## Cấu trúc Commit Message

Format: `<type>(<scope>): <description>`

| Type | Mô tả |
|------|--------|
| `feat` | Tính năng mới |
| `fix` | Sửa bug |
| `docs` | Thay đổi documentation |
| `style` | Formatting, missing semicolons, etc. |
| `refactor` | Refactoring code |
| `test` | Thêm hoặc sửa tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |
| `perf` | Performance improvements |
| `build` | Build system changes |

Scope (tùy chọn): `backend`, `frontend`, `docker`, `docs`, `ci`

### Ví dụ:
```
feat(backend): add CORS misconfiguration detection module
fix(frontend): resolve SSE connection drop on scan progress
docs: update SETUP_GUIDE with Docker instructions
test(backend): add integration tests for scan API
ci: add trivy image scanning to Docker build pipeline
chore: bump fastapi from 0.115.0 to 0.115.3
```
