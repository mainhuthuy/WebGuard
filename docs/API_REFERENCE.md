# WebGuard API Reference Manual

Tài liệu đặc tả chi tiết giao diện lập trình ứng dụng (RESTful API Specification) cho dịch vụ **WebGuard API v1**.

- **Phiên bản API:** `v1`
- **Base URL:** `http://localhost:8000/api/v1`
- **Interactive Documentation:**
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`
- **Chuẩn định dạng:** JSON (`application/json`), SSE (`text/event-stream`), HTML (`text/html`)

---

## 1. Tiêu chuẩn chung (General Conventions)

### Headers chuẩn
| Header Name | Kiểu | Bắt buộc | Mô tả |
|-------------|------|----------|-------|
| `Content-Type` | String | Có (POST) | `application/json` |
| `X-Request-ID` | String | Không | Mã định danh truy vết do client truyền; nếu không có, server tự sinh UUID. Luôn được trả lại trong header phản hồi cùng `X-Process-Time` |

### Cấu trúc phản hồi lỗi chuẩn
Tất cả các lỗi từ server (4xx, 5xx) đều có cấu trúc JSON đồng nhất (chuẩn riêng của project, không phải RFC 7807). Mã HTTP nằm ở status của response:
```json
{
  "success": false,
  "error": {
    "code": "SCAN_NOT_FOUND",
    "message": "Lượt quét với ID '123e4567-e89b-12d3-a456-426614174000' không tồn tại",
    "details": { "scan_id": "123e4567-e89b-12d3-a456-426614174000" }
  }
}
```
Các mã `code` hiện có: `SCAN_NOT_FOUND` (404), `INVALID_TARGET_URL` (400), `VALIDATION_ERROR` (422, `details` là danh sách `{field, message, type}`), `SCAN_EXECUTION_ERROR` (500), `RATE_LIMIT_EXCEEDED` (429), `HTTP_<status>` (lỗi HTTP chuẩn), `INTERNAL_SERVER_ERROR` (500).

> Ví dụ: `POST /scan/{id}/cancel` khi scan đã kết thúc trả `400` với `error.code = "HTTP_400"` và `error.message` mô tả lý do (lỗi `HTTPException` cũng đi qua bộ xử lý chung).

---

## 2. Health Check API (`/health`)

Cung cấp thông tin trạng thái hoạt động của hệ thống phục vụ giám sát.

### 2.1. Kiểm tra sức khỏe tổng quan
- **Endpoint:** `GET /api/v1/health`
- **Mục đích:** Kiểm tra trạng thái, phiên bản, uptime và thống kê tổng quan của service.
- **Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "webguard-backend",
  "version": "0.1.0",
  "environment": "development",
  "demo_mode": false,
  "python_version": "3.12.10",
  "started_at": "2026-09-24T12:00:15.460574+00:00",
  "uptime_seconds": 97.4,
  "total_scans": 0
}
```

> **Lưu ý:** Các endpoint Liveness Probe (`/health/live`) và Readiness Probe (`/health/ready`) sẽ được bổ sung trong Sprint 4 (Docker & CI/CD).

---

## 3. Scan Management API (`/scan`)

Quản lý vòng đời khởi tạo, giám sát và hủy bỏ các phiên quét an ninh.

### 3.1. Khởi tạo phiên quét mới
- **Endpoint:** `POST /api/v1/scan`
- **Mô tả:** Tiếp nhận URL mục tiêu, kiểm tra chống SSRF (cú pháp, IP literal và **phân giải DNS** — mọi địa chỉ phân giải phải là IP public), khởi tạo bản ghi `pending` trong Database. Việc quét chỉ bắt đầu khi client mở luồng SSE (mục 3.3).
- **Request Body:**
```json
{
  "url": "https://example.com",
  "mode": "full"
}
```
  - `url` (bắt buộc): URL `http://` hoặc `https://` công khai.
  - `mode` (tùy chọn, mặc định `full`): `quick` chỉ chạy **Headers + SSL/TLS**; `full` chạy cả 5 module.
- **Response:** `201 Created`
```json
{
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
  "target_url": "https://example.com",
  "mode": "full",
  "status": "pending",
  "created_at": "2026-09-24T11:00:00"
}
```
> `created_at` và các mốc thời gian khác là **UTC không kèm offset** (naive). Client cần coi chúng là UTC (frontend thêm hậu tố `Z`).
- **Error Cases:**
  - `400 Bad Request` (`INVALID_TARGET_URL`): tên miền phân giải về địa chỉ nội bộ / không công khai.
  - `422 Unprocessable Content`: thiếu `url`, scheme không phải http/https, `mode` không hợp lệ, hoặc `url` là IP không công khai (private, loopback, link-local, CGNAT, reserved...) hay `localhost`.

### 3.2. Lấy thông tin & kết quả phiên quét
- **Endpoint:** `GET /api/v1/scan/{scan_id}`
- **Response:** `200 OK`
```json
{
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
  "target_url": "https://example.com",
  "mode": "full",
  "status": "completed",
  "created_at": "2026-09-24T11:00:00",
  "completed_at": "2026-09-24T11:00:05",
  "total_findings": 1,
  "findings": [
    {
      "module": "headers",
      "name": "content-security-policy",
      "severity": "high",
      "description": "CSP giúp ngăn chặn tấn công XSS...",
      "remediation": "Thêm header: Content-Security-Policy: default-src 'self';",
      "url": "https://example.com"
    }
  ],
  "scoring": { "score": 90, "grade": "A", "total_findings": 1 }
}
```
- `scoring` là `null` khi phiên quét chưa hoàn tất. `severity` ∈ `critical | high | medium | low`.
- **Error Cases:** `404 Not Found` (`SCAN_NOT_FOUND`).

### 3.3. Luồng sự kiện thời gian thực (SSE Stream)
- **Endpoint:** `GET /api/v1/scan/{scan_id}/stream`
- **Header phản hồi:** `Content-Type: text/event-stream`
- **Mô tả:** Bắt đầu thực thi quét và truyền các sự kiện tiến trình theo định dạng SSE (`event:` + `data:` JSON). Mở lại luồng của một phiên đã `completed` sẽ phát lại duy nhất sự kiện `complete`. **Không** mở lại luồng của phiên đang chạy (sẽ khởi động quét lần nữa) — client không nên tự reconnect.
- **Các loại sự kiện** (`event`): `start`, `module_start`, `module_completed`, `scoring`, `complete`, `error`.
```text
event: start
data: {"event": "start", "scan_id": "b3e...", "progress": 5, "message": "Bắt đầu phiên quét...", "module": null, "findings": [], "data": {"total_modules": 5}}

event: module_start
data: {"event": "module_start", "scan_id": "b3e...", "progress": 10, "module": "headers", "message": "Đang kiểm tra: ...", "findings": [], "data": null}

event: module_completed
data: {"event": "module_completed", "scan_id": "b3e...", "progress": 25, "module": "headers", "message": "Hoàn thành headers (phát hiện 9 vấn đề)", "findings": [ ... ], "data": {"count": 9}}

event: scoring
data: {"event": "scoring", "progress": 95, "data": {"scoring": {"score": 46, "grade": "F", "total_findings": 10}}, ...}

event: complete
data: {"event": "complete", "progress": 100, "findings": [ ... tất cả findings ... ], "data": {"url": "...", "total_findings": 10, "scoring": {"score": 46, "grade": "F", "total_findings": 10}}, ...}
```
- Tên `module` không được chuẩn hóa (ví dụ module CORS báo là `"CORS"`); client nên so sánh không phân biệt hoa thường.

### 3.4. Hủy bỏ phiên quét
- **Endpoint:** `POST /api/v1/scan/{scan_id}/cancel`
- **Mô tả:** Yêu cầu hủy một phiên quét đang ở trạng thái `pending` hoặc `running`.
- **Response:** `200 OK`
```json
{
  "message": "Đã gửi yêu cầu hủy phiên quét thành công.",
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
  "status": "cancelled"
}
```
- **Error Cases:**
  - `400 Bad Request` (`HTTP_400`): Khi phiên quét đã ở trạng thái kết thúc (`completed`, `failed`, `cancelled`).
  - `404 Not Found` (`SCAN_NOT_FOUND`).

---

## 4. Report Management API (`/report`)

Xuất và định dạng báo cáo kiểm toán bảo mật.

### 4.1. Xuất báo cáo (HTML / JSON Export)
- **Endpoint:** `GET /api/v1/report/{scan_id}/export?format={html|json}`
- **Mô tả:** Xuất báo cáo kết quả quét dưới định dạng JSON hoặc HTML. Dữ liệu bao gồm điểm số, thời gian thực thi, thống kê lỗi theo mức độ nghiêm trọng và danh sách findings.
- **Query Parameters:**
  - `format`: `json` (mặc định) hoặc `html`.
- **Response:**
  - Với `format=json`: Trả về `application/json`, kèm header `Content-Disposition: attachment; filename="webguard_report_<id>.json"`.
    ```json
    {
      "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
      "target_url": "https://example.com",
      "mode": "full",
      "status": "completed",
      "created_at": "2026-09-24 11:00:00",
      "completed_at": "2026-09-24 11:00:08",
      "duration_seconds": 8.0,
      "scoring": { "score": 85, "grade": "B", "total_findings": 4 },
      "severity_counts": {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 1
      },
      "total_findings": 4,
      "findings": [...]
    }
    ```
  - Với `format=html`: Trả về `text/html; charset=utf-8`, kèm header `Content-Disposition: attachment; filename="webguard_report_<id>.html"`. Báo cáo HTML được sinh bởi Jinja2 template với giao diện tối ưu chuyên nghiệp.

---

## 5. History & Analytics API (`/history`)

Tra cứu lịch sử quét với bộ lọc động và thống kê số liệu tổng quan. Chi tiết một phiên quét lấy qua `GET /api/v1/scan/{scan_id}` (mục 3.2).

### 5.1. Danh sách lịch sử quét có phân trang & lọc
- **Endpoint:** `GET /api/v1/history`
- **Query Parameters:**
  - `search_url` (string, tùy chọn): Tìm tương đối (không phân biệt hoa thường) theo URL mục tiêu.
  - `status` (string, tùy chọn): `pending`, `running`, `completed`, `failed`, `cancelled`.
  - `grade` (string, tùy chọn): Lọc theo xếp hạng (`A+`, `A`, `B`, `C`, `F`).
  - `from_date` / `to_date` (ISO datetime, tùy chọn): Giới hạn thời điểm tạo.
  - `sort_by` (`created_at` mặc định | `score`) và `sort_order` (`desc` mặc định | `asc`).
  - `page` (integer, mặc định `1`, min `1`) và `page_size` (mặc định `10`, min `1`, max `100`).
- **Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
      "target_url": "https://example.com",
      "status": "completed",
      "mode": "full",
      "score": 95,
      "grade": "A+",
      "total_findings": 1,
      "created_at": "2026-09-24T11:00:00",
      "completed_at": "2026-09-24T11:00:05",
      "duration_seconds": 5.0
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 10,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false
}
```
- `score` và `grade` là `null` với phiên chưa hoàn tất, thất bại hoặc bị hủy.

### 5.2. Thống kê số liệu tổng hợp
- **Endpoint:** `GET /api/v1/history/stats`
- **Response:** `200 OK`
```json
{
  "total_scans": 45,
  "completed_scans": 40,
  "failed_scans": 3,
  "cancelled_scans": 2,
  "average_score": 82.4,
  "grade_distribution": { "A+": 12, "A": 15, "B": 10, "C": 5, "F": 3 }
}
```

### 5.3. Xóa một bản ghi lịch sử
- **Endpoint:** `DELETE /api/v1/history/{scan_id}`
- **Mô tả:** Xóa vĩnh viễn phiên quét và toàn bộ findings liên quan (cascade).
- **Response:** `200 OK`
```json
{
  "deleted": true,
  "message": "Đã xóa thành công phiên quét b3e0... khỏi lịch sử",
  "deleted_count": 1
}
```
- **Error Cases:** `404 Not Found` (`SCAN_NOT_FOUND`).

### 5.4. Dọn dẹp lịch sử hàng loạt
- **Endpoint:** `DELETE /api/v1/history?older_than_days=30`
- **Mô tả:** Xóa các phiên quét cũ hơn `older_than_days` ngày; bỏ tham số để xóa toàn bộ.
- **Response:** `200 OK` — cùng dạng với mục 5.3, `deleted_count` là số bản ghi đã xóa.
