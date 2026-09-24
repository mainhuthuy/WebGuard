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
| `X-Correlation-ID` | String | Không | Mã định danh truy vết luồng xử lý do client truyền hoặc do server sinh tự động |

### Cấu trúc phản hồi lỗi chuẩn (RFC 7807 Standard Error Format)
Tất cả các lỗi nghiệp vụ từ server (4xx, 5xx) đều có cấu trúc JSON đồng nhất:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Không tìm thấy phiên quét có ID: 123e4567-e89b-12d3-a456-426614174000",
    "status_code": 404
  }
}
```

---

## 2. Health Check API (`/health`)

Cung cấp thông tin trạng thái hoạt động của hệ thống phục vụ giám sát container và Kubernetes probes.

### 2.1. Kiểm tra sức khỏe tổng quan
- **Endpoint:** `GET /api/v1/health`
- **Mục đích:** Kiểm tra phiên bản và trạng thái tổng quan của service.
- **Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "app_name": "WebGuard API"
}
```

### 2.2. Liveness Probe
- **Endpoint:** `GET /api/v1/health/live`
- **Mục đích:** Kiểm tra container tiến trình Python có đang còn sống hay không.
- **Response:** `200 OK`
```json
{
  "status": "alive"
}
```

### 2.3. Readiness Probe
- **Endpoint:** `GET /api/v1/health/ready`
- **Mục đích:** Kiểm tra khả năng kết nối tới Database trước khi nhận lưu lượng mạng.
- **Response:**
  - `200 OK`: Khi kết nối DB hoạt động bình thường.
  - `503 Service Unavailable`: Khi không thể kết nối tới DB.
```json
{
  "status": "ready",
  "database": "connected"
}
```

---

## 3. Scan Management API (`/scan`)

Quản lý vòng đời khởi tạo, giám sát và hủy bỏ các phiên quét an ninh.

### 3.1. Khởi tạo phiên quét mới
- **Endpoint:** `POST /api/v1/scan`
- **Mô tả:** Tiếp nhận URL mục tiêu, kiểm tra bảo vệ SSRF, khởi tạo bản ghi trong Database. Có thể chọn quét ngầm (background mode) hoặc chỉ khởi tạo chờ client kết nối SSE.
- **Request Body:**
```json
{
  "target_url": "https://example.com",
  "run_in_background": false
}
```
- **Response:** `201 Created`
```json
{
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
  "target_url": "https://example.com",
  "status": "pending",
  "created_at": "2026-09-24T11:00:00Z",
  "stream_url": "/api/v1/scan/b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9/stream"
}
```
- **Error Cases:**
  - `400 Bad Request`: URL không hợp lệ hoặc vi phạm SSRF (trỏ tới dải IP private/localhost).
  - `422 Unprocessable Content`: Thiếu trường dữ liệu bắt buộc.

### 3.2. Lấy thông tin & kết quả phiên quét
- **Endpoint:** `GET /api/v1/scan/{scan_id}`
- **Response:** `200 OK`
```json
{
  "id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
  "target_url": "https://example.com",
  "status": "completed",
  "score": 95.0,
  "grade": "A+",
  "created_at": "2026-09-24T11:00:00Z",
  "completed_at": "2026-09-24T11:00:05Z",
  "findings": [
    {
      "id": 1,
      "module": "headers",
      "name": "Missing Content-Security-Policy",
      "severity": "medium",
      "description": "Header Content-Security-Policy chưa được thiết lập.",
      "remediation": "Cấu hình header Content-Security-Policy để ngăn ngừa XSS.",
      "target_url": "https://example.com"
    }
  ]
}
```

### 3.3. Luồng sự kiện thời gian thực (SSE Stream)
- **Endpoint:** `GET /api/v1/scan/{scan_id}/stream`
- **Header phản hồi:** `Content-Type: text/event-stream`, `Cache-Control: no-cache`
- **Mô tả:** Truyền trực tiếp các sự kiện tiến trình quét từng module theo định dạng SSE.
- **Các bước sự kiện tiêu biểu:**
```text
data: {"event": "init", "scan_id": "b3e...", "progress": 0, "message": "Bắt đầu quét..."}

data: {"event": "step", "scan_id": "b3e...", "progress": 20, "module": "headers", "message": "Đang phân tích HTTP Headers..."}

data: {"event": "step", "scan_id": "b3e...", "progress": 40, "module": "cookies", "message": "Đang kiểm tra cờ bảo mật Cookie..."}

data: {"event": "complete", "scan_id": "b3e...", "progress": 100, "message": "Quét hoàn tất!", "findings": [...], "data": {"scoring": {"score": 95.0, "grade": "A+"}}}
```

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
  - `400 Bad Request`: Khi phiên quét đã ở trạng thái kết thúc (`completed`, `failed`, `cancelled`).

### 3.5. Xóa phiên quét
- **Endpoint:** `DELETE /api/v1/scan/{scan_id}`
- **Mô tả:** Xóa vĩnh viễn phiên quét và toàn bộ các findings liên quan (Cascade delete).
- **Response:** `200 OK`
```json
{
  "message": "Đã xóa phiên quét và các findings liên quan thành công.",
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9"
}
```

---

## 4. Report Management API (`/report`)

Xuất và định dạng báo cáo kiểm toán bảo mật.

### 4.1. Lấy dữ liệu báo cáo chi tiết
- **Endpoint:** `GET /api/v1/report/{scan_id}`
- **Mô tả:** Trả về dữ liệu tổng hợp phục vụ hiển thị báo cáo: điểm số, thời gian thực thi, thống kê lỗi theo mức độ nghiêm trọng (critical, high, medium, low, info).
- **Response:** `200 OK`
```json
{
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
  "target_url": "https://example.com",
  "status": "completed",
  "score": 85.0,
  "grade": "B",
  "created_at": "2026-09-24T11:00:00Z",
  "completed_at": "2026-09-24T11:00:08Z",
  "duration_seconds": 8.0,
  "severity_counts": {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 0,
    "info": 1
  },
  "total_findings": 4,
  "findings": [...]
}
```

### 4.2. Xuất báo cáo (HTML / JSON Export)
- **Endpoint:** `GET /api/v1/report/{scan_id}/export?format={html|json}`
- **Query Parameters:**
  - `format`: `html` (mặc định) hoặc `json`.
- **Response:**
  - Với `format=html`: Trả về `text/html; charset=utf-8`, kèm header `Content-Disposition: attachment; filename="webguard_report_<id>.html"`. Báo cáo HTML được sinh bởi Jinja2 template với giao diện tối ưu chuyên nghiệp.
  - Với `format=json`: Trả về `application/json`, kèm header `Content-Disposition: attachment; filename="webguard_report_<id>.json"`.

---

## 5. History & Analytics API (`/history`)

Tra cứu lịch sử quét với bộ lọc động và thống kê số liệu tổng quan.

### 5.1. Danh sách lịch sử quét có phân trang & lọc
- **Endpoint:** `GET /api/v1/history`
- **Query Parameters:**
  - `target_url` (string, tùy chọn): Tìm kiếm tương đối theo URL mục tiêu.
  - `status` (string, tùy chọn): Lọc theo trạng thái (`completed`, `failed`, `running`, `cancelled`).
  - `grade` (string, tùy chọn): Lọc theo xếp hạng (`A+`, `A`, `B`, `C`, `F`).
  - `start_date` (ISO datetime, tùy chọn): Giới hạn thời gian bắt đầu.
  - `end_date` (ISO datetime, tùy chọn): Giới hạn thời gian kết thúc.
  - `page` (integer, mặc định `1`, min `1`): Trang hiện tại.
  - `page_size` (integer, mặc định `10`, min `1`, max `100`): Số bản ghi trên mỗi trang.
- **Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9",
      "target_url": "https://example.com",
      "status": "completed",
      "score": 95.0,
      "grade": "A+",
      "created_at": "2026-09-24T11:00:00Z",
      "completed_at": "2026-09-24T11:00:05Z",
      "total_findings": 1
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

### 5.2. Thống kê số liệu tổng hợp (Dashboard Analytics)
- **Endpoint:** `GET /api/v1/history/stats`
- **Mô tả:** Thống kê tổng số phiên quét, điểm số trung bình, phân bổ theo xếp hạng (Grade Distribution) và trạng thái.
- **Response:** `200 OK`
```json
{
  "total_scans": 45,
  "average_score": 82.4,
  "grade_distribution": {
    "A+": 12,
    "A": 15,
    "B": 10,
    "C": 5,
    "F": 3
  },
  "status_distribution": {
    "completed": 40,
    "failed": 3,
    "cancelled": 2
  }
}
```

### 5.3. Xem chi tiết lịch sử một phiên quét
- **Endpoint:** `GET /api/v1/history/{scan_id}`
- **Response:** `200 OK` (Trả về chi tiết phiên quét kèm toàn bộ danh sách findings).

### 5.4. Xóa một bản ghi lịch sử
- **Endpoint:** `DELETE /api/v1/history/{scan_id}`
- **Response:** `200 OK`
```json
{
  "message": "Đã xóa lịch sử phiên quét thành công.",
  "scan_id": "b3e0c0ea-5b48-436a-bdf5-d5bfa780d6b9"
}
```
