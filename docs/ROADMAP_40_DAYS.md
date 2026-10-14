# WebGuard — Kế Hoạch 40 Ngày Triển Khai (Agile Sprints)

> **Mục tiêu:** Xây dựng hoàn chỉnh 100% công cụ Web Security Assessment Scanner đạt chuẩn Enterprise/DevOps cho CV và phỏng vấn.
> **Thời gian:** 40 ngày (6 Sprints) — 4-5 giờ/ngày.

---

## 📊 Tổng quan Timeline 40 ngày

```
Ngày 1-3   │ Sprint 0 │ ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ Project Bootstrap & Infrastructure
Ngày 4-11  │ Sprint 1 │ ░░░████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ Core Scanner Engine (5 Modules)
Ngày 12-19 │ Sprint 2 │ ░░░░░░░░░░░████████░░░░░░░░░░░░░░░░░░░░░░ │ FastAPI Service, SSE & SQLite
Ngày 20-28 │ Sprint 3 │ ░░░░░░░░░░░░░░░░░░░█████████░░░░░░░░░░░░░ │ React Dashboard UI & Integration
Ngày 29-35 │ Sprint 4 │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░███████░░░░░░ │ DevOps, Docker & CI/CD Pipeline
Ngày 36-40 │ Sprint 5 │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█████ │ Landing Page, Live Demo & Portfolio
```

---

## 🏃 SPRINT 0: Project Bootstrap & Infrastructure (Ngày 1 - 3)

**Mục tiêu:** Thiết lập cấu trúc Monorepo, môi trường Python + Node, cấu hình Git Flow, Linters và Docker configs.

| # | Task | Chi tiết | Ước tính |
|---|------|----------|----------|
| 0.1 | Khởi tạo repo & Git Flow | Khởi tạo git, nhánh `main` (production) & `develop` (dev chính) | 0.5h |
| 0.2 | Cấu trúc Monorepo | Tạo thư mục `backend`, `frontend`, `landing`, `docker`, `docs`, `scripts` | 1h |
| 0.3 | Backend Setup | `pyproject.toml`, FastAPI, Uvicorn, HTTPX, Pydantic, Python Virtualenv | 2h |
| 0.4 | Frontend Setup | React 19 + Vite + TypeScript, CSS tokens Cyber Dark Vibe | 2h |
| 0.5 | Linter & Formatter | Cấu hình Ruff + Black (Python), ESLint + Prettier (JS/TS) | 1.5h |
| 0.6 | Pre-commit Hooks | `.pre-commit-config.yaml` tự động kiểm tra code trước khi commit | 1h |
| 0.7 | Standard Configs | `.editorconfig`, `.gitignore`, `.gitattributes` | 0.5h |
| 0.8 | Makefile Commands | Các lệnh tắt `make dev`, `make test`, `make lint`, `make docker-up` | 1h |
| 0.9 | Tài liệu cốt lõi | `SETUP_GUIDE.md`, `DEV_WORKFLOW.md`, `GIT_CONVENTIONS.md` | 2h |
| 0.10 | Issue & PR Templates | Chuẩn hóa quy trình đóng góp và báo lỗi GitHub | 0.5h |

**DoD (Definition of Done):** Môi trường dev chạy được trên localhost, Git Flow sẵn sàng trên GitHub.

---

## 🏃 SPRINT 1: Core Scanner Engine (Ngày 4 - 11)

**Mục tiêu:** Xây dựng lõi quét bảo mật Python với 5 module chuyên biệt, độc lập và có unit test đầy đủ.

| # | Task | Chi tiết | Ước tính |
|---|------|----------|----------|
| 1.1 | Thiết kế `BaseModule` | Lớp trừu tượng (Abstract Base Class) định nghĩa chuẩn cho mọi module quét | 2h |
| 1.2 | `HeadersModule` | Quét CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy | 3h |
| 1.3 | `CookiesModule` | Kiểm tra cờ an toàn của Cookie: `HttpOnly`, `Secure`, `SameSite` | 2h |
| 1.4 | `SSLTLSModule` | Kiểm tra chứng chỉ SSL/TLS, hạn dùng, thuật toán và phiên bản giao thức cũ | 3h |
| 1.5 | `InformationModule` | Rà soát lộ file nhạy cảm: `/.env`, `/.git`, `robots.txt`, Server Header banner | 3h |
| 1.6 | `CORSModule` | Kiểm tra cấu hình sai CORS (`Origin: *` hoặc phản hồi origin tùy tiện) | 2h |
| 1.7 | `ScoringEngine` | Thuật toán tính điểm an toàn (A+, A, B, C, F) và phân loại mức độ nghiêm trọng | 2h |
| 1.8 | `Scanner` Orchestrator | Bộ điều phối chạy song song các module quét (Async I/O) | 2h |
| 1.9 | Pydantic Schemas | `ScanRequest`, `ScanResponse`, `Finding`, `Remediation` data models | 1.5h |
| 1.10 | Unit Tests | Viết bộ test `pytest` mock HTTP responses cho cả 5 module | 3h |
| 1.11 | Test Fixtures | Cấu hình `conftest.py` với các kịch bản test mẫu | 1h |

**DoD:** Chạy `pytest` 100% pass, Scanner quét thử nghiệm URL trả về đúng cấu trúc kết quả và gợi ý fix.

---

## 🏃 SPRINT 2: FastAPI Service & Database (Ngày 12 - 19)

**Mục tiêu:** Xây dựng RESTful API hoàn chỉnh, bắn tiến trình quét theo thời gian thực (SSE) và lưu lịch sử vào SQLite.

| # | Task | Chi tiết | Ước tính |
|---|------|----------|----------|
| 2.1 | Cấu hình FastAPI | Setup CORS, Global Error Handling, Structured Logging | 2h |
| 2.2 | API: Khởi tạo Scan | `POST /api/v1/scan` nhận URL, validate và sinh `scan_id` | 2h |
| 2.3 | API: SSE Real-time | `GET /api/v1/scan/{id}/stream` bắn tiến trình quét từng bước về client | 3h |
| 2.4 | API: Lấy kết quả | `GET /api/v1/scan/{id}` lấy chi tiết toàn bộ findings | 1.5h |
| 2.5 | API: Xuất báo cáo | `GET /api/v1/report/{id}/export?format=json\|html` xuất báo cáo | 2h |
| 2.6 | API: Health Check | `GET /api/v1/health` kiểm tra trạng thái dịch vụ | 0.5h |
| 2.7 | SQLite & SQLAlchemy | Bảng `scans` và `findings` lưu trữ lịch sử quét cục bộ | 2h |
| 2.8 | Alembic Migrations | Quản lý phiên bản cấu trúc database | 1h |
| 2.9 | `ScanService` | Quản lý vòng đời scan: khởi tạo, chạy background, hủy hoặc hoàn tất | 2h |
| 2.10 | `ReportService` | Tạo file báo cáo HTML từ template Jinja2 chuyên nghiệp | 2.5h |
| 2.11 | `HistoryService` | Truy vấn và phân trang danh sách các lần quét trước | 1.5h |
| 2.12 | Integration Tests | Test các endpoint API bằng `TestClient` của FastAPI | 2h |
| 2.13 | API Docs | Cập nhật `ARCHITECTURE.md` và `API_REFERENCE.md` | 1.5h |

**DoD:** Có thể test toàn bộ API qua Swagger UI (`/docs`), nhận SSE mượt mà, lịch sử lưu vào file `webguard.db`.

---

## 🏃 SPRINT 3: React Dashboard UI & Integration (Ngày 20 - 28)

**Mục tiêu:** Xây dựng giao diện Web Dashboard hoàn chỉnh, kết nối Backend, hiển thị trực quan biểu đồ và lỗ hổng.

*(Lưu ý: Thiết kế phong cách Cyber Dark Vibe, styling CSS do bạn tự tùy biến theo ý thích).*

| # | Task | Chi tiết | Ước tính |
|---|------|----------|----------|
| 3.1 | Core Design Skeleton | Khung CSS variables, Dark Palette, Typography (Inter/JetBrains Mono) | 1h |
| 3.2 | Layout Components | `Header` (Logo + status), `Sidebar` (Menu), `Footer` | 2h |
| 3.3 | UI Primitives | `Button`, `Card`, `Badge` (Severity colors), `ProgressBar`, `Modal` | 2.5h |
| 3.4 | Scan Page | Ô nhập URL, nút kích hoạt scan, chọn chế độ Quick / Full audit | 3h |
| 3.5 | Real-time Progress | Component nhận SSE hiển thị tiến trình quét từng bước | 3h |
| 3.6 | Results Page | Thẻ điểm `ScoreCard` (A+ -> F) + biểu đồ `SeverityChart` (Recharts) | 4h |
| 3.7 | Finding Detail | Modal/Panel xem chi tiết lỗ hổng + snippet code mẫu hướng dẫn sửa | 2h |
| 3.8 | History Page | Bảng xem lại các lần quét cũ, lọc theo ngày hoặc điểm số | 2h |
| 3.9 | Export Actions | Nút tải file báo cáo JSON hoặc HTML report trực tiếp | 1.5h |
| 3.10 | Custom Hooks | `useScan` (quản lý state), `useSSE` (kết nối stream), `useReport` | 2h |
| 3.11 | API Services | Khởi tạo Axios client (`scanApi.ts`, `reportApi.ts`) | 1.5h |
| 3.12 | About & Disclaimer | Trang giới thiệu tính năng, hướng dẫn sử dụng và chính sách miễn trừ | 1h |
| 3.13 | Frontend Tests | Test các component chính bằng Vitest và React Testing Library | 2h |

**DoD:** Trải nghiệm người dùng trọn vẹn: Nhập URL → Xem quét thời gian thực → Đọc kết quả & remediation → Xuất báo cáo.

---

## 🏃 SPRINT 4: DevOps, Docker & CI/CD Pipeline (Ngày 29 - 35)

**Mục tiêu:** Đóng gói Docker hoàn chỉnh, xây dựng pipeline DevSecOps tự động kiểm tra bảo mật cho chính dự án.

| # | Task | Chi tiết | Ước tính | Trạng thái |
|---|------|----------|----------|-----------|
| 4.1 | Backend Dockerfile | Multi-stage build (tối ưu dung lượng image) | 2h | ✅ |
| 4.2 | Frontend Dockerfile | Multi-stage build + Nginx alpine phục vụ static bundle | 2h | ✅ |
| 4.3 | Docker Compose | Cấu hình file chạy Production và Dev (hot-reload) | 2h | ✅ |
| 4.4 | CI: Backend Pipeline | GitHub Actions: Tự động chạy Lint (Ruff) + Test (Pytest) khi tạo PR | 2.5h | 🟡 đã viết, chưa chạy trên GitHub |
| 4.5 | CI: Frontend Pipeline | GitHub Actions: Lint (ESLint) + Type Check (TSC) + Build check | 2h | 🟡 đã viết, chưa chạy trên GitHub |
| 4.6 | CD: Container Registry | Tự động build và push Docker image lên GitHub Container Registry | 2h | 🟡 đã viết, chưa chạy trên GitHub |
| 4.7 | DevSecOps in Pipeline | Quét lỗ hổng dependencies bằng `pip-audit` + quét Docker image bằng `Trivy` | 2h | 🟡 đã viết, chưa chạy trên GitHub |
| 4.8 | Setup Scripts | Viết script chạy nhanh 1 click: `setup-dev.ps1` (Windows) & `setup-dev.sh` | 1.5h | ✅ (chưa chạy luồng cài đầy đủ) |
| 4.9 | End-to-End Docker Test | Kiểm tra lệnh `docker compose up -d` trên máy sạch | 2h | ✅ (Windows + Docker Desktop) |
| 4.10 | `CONTRIBUTING.md` | Hướng dẫn cộng tác và phát triển dành cho người mới | 1h | ✅ |

> **Ghi chú trạng thái:** 🟡 = workflow đã viết nhưng **chưa chạy trên GitHub Actions** và chưa được kiểm tra cú pháp YAML (các lệnh ESLint/`tsc`/Vite build đã chạy thử ở local; lệnh Ruff/Pytest/`pip-audit`/Trivy thì chưa chạy ở máy này); `pip-audit` và Trivy chưa chạy lần nào, lần đầu có thể đỏ do CVE sẵn có. CI frontend chưa gồm `npm test` (còn 1 test chập chờn cần tìm ra). Tài liệu từng task: `docs/learning/4.1` – `4.10`.

**DoD:** Người dùng chỉ cần gõ duy nhất 1 lệnh `docker compose up -d` là toàn bộ hệ thống hoạt động hoàn hảo. Pipeline CI/CD tự động xanh trên GitHub.

---

## 🏃 SPRINT 5: Landing Page, Online Demo & Portfolio (Ngày 36 - 40)

**Mục tiêu:** Xây dựng Landing Page giới thiệu có bản Demo trực tuyến giới hạn để HR/Interviewer click xem ngay, hoàn tất Portfolio.

| # | Task | Chi tiết | Ước tính |
|---|------|----------|----------|
| 5.1 | Khởi tạo `landing/` | Project Vite + React riêng cho Landing Page | 1h |
| 5.2 | Sections chính | `Hero`, `Features`, `HowItWorks`, `TechStack`, `Screenshots` | 3h |
| 5.3 | Live Demo Component | Nhúng ô quét thử nghiệm trực tiếp ngay trên trang web (Chỉ quét Headers + SSL) | 3h |
| 5.4 | Demo Controls | Giới hạn quét an toàn: Rate Limiting 5 lần/ngày/IP, nút "Download Full Version" | 2h |
| 5.5 | Deploy Online Demo | Deploy Landing Page lên **Vercel** + Backend Demo lên **Render** (Free tier) | 2h |
| 5.6 | Demo Mode Backend | Thêm flag `DEMO_MODE=true` tắt các module nhạy cảm để đảm bảo an toàn | 2.5h |
| 5.7 | Professional README | Thêm Badges, Architecture Diagram, GIF demo, Link Live Demo | 2.5h |
| 5.8 | Architecture Diagram | Vẽ sơ đồ hệ thống luồng dữ liệu (Mermaid format) | 1h |
| 5.9 | Quay Video Demo / GIF | Ghi lại luồng quét thực tế chèn vào README | 1.5h |
| 5.10 | Test với Lab thực tế | Quét thử trên các môi trường lab (badssl.com, httpbin.org) | 2h |
| 5.11 | Release v1.0.0 | Đóng gói GitHub Release v1.0.0 kèm CHANGELOG đầy đủ | 1.5h |
| 5.12 | Chuẩn bị nội dung CV | Soạn bullet points chuẩn cho mục Dự án trong CV xin việc | 0.5h |

**DoD:** Dự án có link Live Demo trực tiếp, GitHub repo có badge, ảnh demo, tài liệu chuyên nghiệp, sẵn sàng gửi cho nhà tuyển dụng!

---

## 📌 Bổ sung sau kế hoạch gốc (ngoài 40 ngày)

Kế hoạch trên chốt ở **5 module quét**. Sau khi hoàn thành, phạm vi quét được mở rộng đáng kể dựa trên nhu cầu thực tế, không nằm trong lịch 40 ngày ban đầu:

| Hạng mục | Trước | Sau | Tài liệu |
|---|---|---|---|
| Số module quét (`full`) | 5 | **7** (+ `ContentModule`, `HttpConfigModule`) | `1.11`, `1.12` |
| Tổng số kiểm tra | 25 | **~102** (header giá trị yếu, cookie nâng cao, phân loại lỗi chứng chỉ, 33 đường dẫn nhạy cảm mới, CORS nâng cao, phân tích HTML, hành vi HTTP) | `1.2`–`1.6`, `1.8`, `1.11`, `1.12` |
| Kiểm tra chủ động (rủi ro thấp, có giới hạn phạm vi rõ ràng) | 0 | 2 (`username_enumeration`, `open_redirect`) | `1.11`, `1.12` |
| Tích hợp AI | Không có | "Explain with AI" (BYOK — người dùng tự mang API key, AI chỉ diễn giải dữ liệu đã quét) | `3.14` |

**Nguyên tắc giữ xuyên suốt khi mở rộng:** mọi kiểm tra mới đều được cân nhắc giữa *giá trị phát hiện* và *rủi ro trở thành công cụ tấn công trên target không xác minh chủ sở hữu* — đây là lý do WebGuard **không** có các kiểm tra kiểu XSS/SQLi injection thật hay brute-force, dù về mặt kỹ thuật không khó thêm.
