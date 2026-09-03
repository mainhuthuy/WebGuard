# WebGuard - Git Conventions

## Branching Strategy: Git Flow

```
main ──────────────────────────────────────────────────────►
  │                                                    ▲
  └─► develop ──────────────────────────────────────►──┘
        │         ▲         │         ▲
        └─► feature/xyz ──┘ └─► feature/abc ──┘
```

### Branch Types

| Branch | Mục đích | Tạo từ | Merge vào |
|--------|----------|--------|-----------|
| `main` | Production-ready code | — | — |
| `develop` | Integration branch, code mới nhất | `main` | `main` (qua release) |
| `feature/*` | Phát triển tính năng mới | `develop` | `develop` |
| `release/*` | Chuẩn bị release (fix bugs, update docs) | `develop` | `main` + `develop` |
| `hotfix/*` | Fix bug khẩn cấp trên production | `main` | `main` + `develop` |

### Branch Naming Convention

```
feature/short-description    # Tính năng mới
fix/short-description        # Sửa bug
hotfix/short-description     # Fix khẩn cấp
release/v1.0.0               # Chuẩn bị release
docs/short-description       # Documentation
refactor/short-description   # Refactoring
ci/short-description         # CI/CD changes
```

**Ví dụ:**
```
feature/headers-module
feature/scan-progress-ui
fix/ssl-timeout-handling
release/v1.0.0
hotfix/cors-bypass-fix
```

---

## Commit Convention: Conventional Commits

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Emoji | Mô tả | Ví dụ |
|------|-------|--------|-------|
| `feat` | ✨ | Tính năng mới | `feat(backend): add SSL certificate checker` |
| `fix` | 🐛 | Sửa bug | `fix(frontend): resolve chart rendering on mobile` |
| `docs` | 📝 | Documentation | `docs: update API reference` |
| `style` | 💄 | Code style (không thay đổi logic) | `style(backend): format with black` |
| `refactor` | ♻️ | Refactoring | `refactor(backend): extract base scanner class` |
| `test` | ✅ | Tests | `test(backend): add unit tests for headers module` |
| `chore` | 🔧 | Maintenance | `chore: update dependencies` |
| `ci` | 👷 | CI/CD | `ci: add backend linting workflow` |
| `perf` | ⚡ | Performance | `perf(backend): optimize concurrent scanning` |
| `build` | 📦 | Build system | `build: add multi-stage Dockerfile` |

### Scopes (Tùy chọn)

| Scope | Mô tả |
|-------|--------|
| `backend` | Backend Python/FastAPI |
| `frontend` | Frontend React Dashboard |
| `landing` | Landing Page |
| `docker` | Docker configuration |
| `docs` | Documentation |
| `ci` | CI/CD pipelines |
| `deps` | Dependencies |

### Rules

1. **Subject line:** Viết bằng tiếng Anh, bắt đầu bằng chữ thường, không kết thúc bằng dấu chấm
2. **Max length:** Subject ≤ 72 ký tự
3. **Imperative mood:** Dùng "add", "fix", "update" thay vì "added", "fixed", "updated"
4. **Breaking changes:** Thêm `!` sau type hoặc `BREAKING CHANGE:` trong footer

### Ví dụ đầy đủ

```
feat(backend): add security headers analysis module

Implement HeadersModule that checks for:
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy

Each missing header generates a Finding with severity level
and remediation guidance.

Closes #12
```

---

## Pull Request Checklist

Khi tạo PR, đảm bảo:

- [ ] Branch name đúng convention (`feature/`, `fix/`, ...)
- [ ] Commit messages đúng Conventional Commits format
- [ ] Code đã được lint (`make lint`)
- [ ] Tests đã pass (`make test`)
- [ ] Không commit file nhạy cảm (`.env`, secrets, API keys)
- [ ] Documentation đã được cập nhật (nếu cần)
- [ ] PR description mô tả rõ thay đổi + link issue liên quan

---

## Quy trình Release

1. Tạo branch `release/vX.Y.Z` từ `develop`
2. Update version trong `pyproject.toml` và `package.json`
3. Update `CHANGELOG.md`
4. Fix remaining bugs (nếu có)
5. Merge vào `main` → tạo Git Tag `vX.Y.Z`
6. Merge ngược lại `develop`
7. Tạo GitHub Release với release notes
