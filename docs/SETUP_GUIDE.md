# WebGuard - Setup Guide

## Prerequisites

Trước khi bắt đầu, hãy kiểm tra và cài đặt các công cụ sau. **Nếu lệnh check trả về version → bạn đã có, skip bước cài đặt.**

### 1. Git
```powershell
git --version
# ✅ "git version 2.x.x" → SKIP
# ❌ Lỗi → Cài từ https://git-scm.com/downloads
```

### 2. Python 3.12+
```powershell
python --version
# ✅ "Python 3.12.x" trở lên → SKIP
# ❌ Lỗi → Cài từ https://www.python.org/downloads/
#    ⚠️ Tick ✅ "Add Python to PATH" khi cài

pip --version
# ✅ "pip 2x.x" → SKIP
```

### 3. Node.js (v18+)
```powershell
node --version
# ✅ "v18.x.x" trở lên → SKIP
# ❌ Lỗi → Cài từ https://nodejs.org/ (chọn LTS)
```

### 4. pnpm
```powershell
pnpm --version
# ✅ "9.x.x" → SKIP
# ❌ Lỗi → Cài bằng: npm install -g pnpm
```

### 5. Docker & Docker Compose
```powershell
docker --version
# ✅ "Docker version 2x.x" → SKIP
# ❌ Lỗi → Cài Docker Desktop: https://www.docker.com/products/docker-desktop/

docker compose version
# ✅ "Docker Compose version v2.x.x" → SKIP
```

### 6. Make (Tùy chọn)
```powershell
make --version
# ✅ Hiện version → SKIP
# ❌ Lỗi → Cài qua Chocolatey (Run as Admin): choco install make -y
#    Hoặc dùng Git Bash / WSL thay thế
```

---

## Bước 1: Clone / Tải dự án

```powershell
# Nếu clone từ GitHub
git clone <repo-url>
cd WebGuard

# Nếu đã có folder local
cd d:\HuyMai\SelfLearning\Project\WebGuard
```

---

## Bước 2: Setup Backend

```powershell
# Di chuyển vào thư mục backend
cd backend

# Tạo virtual environment
python -m venv .venv

# Kích hoạt virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
# .venv\Scripts\activate.bat
# Linux/Mac:
# source .venv/bin/activate

# Cài đặt dependencies (bao gồm cả dev tools)
pip install -e ".[dev]"

# Copy file environment variables
copy .env.example .env

# Verify: chạy thử FastAPI
python -m uvicorn app.main:app --reload --port 8000
# ✅ Mở http://localhost:8000/docs → thấy Swagger UI
```

---

## Bước 3: Setup Frontend

```powershell
# Di chuyển vào thư mục frontend (từ root)
cd frontend

# Cài đặt dependencies
pnpm install

# Copy file environment variables
copy .env.example .env

# Verify: chạy thử React dev server
pnpm dev
# ✅ Mở http://localhost:5173 → thấy React app
```

---

## Bước 4: Setup Pre-commit Hooks

```powershell
# Từ thư mục root WebGuard
cd ..

# Cài đặt pre-commit hooks
pip install pre-commit
pre-commit install

# Verify: chạy thử hooks
pre-commit run --all-files
```

---

## Bước 5: Chạy với Docker (Tùy chọn)

```powershell
# Từ thư mục root WebGuard
cd docker

# Build và chạy tất cả services
docker compose up -d

# Kiểm tra
docker compose ps
# ✅ Tất cả services đều "running"

# Dừng
docker compose down
```

---

## Quick Reference

| Lệnh | Mô tả |
|-------|--------|
| `make dev` | Chạy cả BE + FE development servers |
| `make dev-be` | Chỉ chạy Backend |
| `make dev-fe` | Chỉ chạy Frontend |
| `make test` | Chạy tất cả tests |
| `make lint` | Kiểm tra code quality |
| `make format` | Auto-format code |
| `make docker-up` | Chạy Docker Compose |
| `make docker-down` | Dừng Docker |

---

## Troubleshooting

### "Execution Policy" error khi chạy `.venv\Scripts\Activate.ps1`
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port 8000 đã bị chiếm
```powershell
# Tìm process đang dùng port 8000
netstat -ano | findstr :8000
# Kill process đó
taskkill /PID <PID> /F
```

### pnpm lỗi liên quan Corepack
```powershell
corepack disable pnpm
npm install -g pnpm --force
```
