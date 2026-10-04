"""Pydantic data schemas for scan requests, findings, and responses."""

import ipaddress
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"



class ScanMode(str, Enum):
    """Chế độ quét: quick (Headers + SSL/TLS) hoặc full (toàn bộ module)."""

    QUICK = "quick"
    FULL = "full"


class ScanEventType(str, Enum):
    START = "start"
    MODULE_START = "module_start"
    MODULE_COMPLETED = "module_completed"
    SCORING = "scoring"
    COMPLETE = "complete"
    ERROR = "error"


class ScanCreateRequest(BaseModel):
    """Payload gửi lên để yêu cầu tạo một lượt quét bảo mật mới."""

    url: str = Field(
        ...,
        description="Target URL cần quét (phải có http:// hoặc https://)",
        examples=["https://example.com"],
    )
    mode: ScanMode = Field(
        default=ScanMode.FULL,
        description="Chế độ quét: 'quick' (Headers + SSL/TLS) hoặc 'full' (tất cả module)",
    )

    @field_validator("url")
    @classmethod
    def validate_target_url(cls, v: str) -> str:
        url_str = v.strip()
        parsed = urlparse(url_str)

        # 1. Kiểm tra scheme phải là http hoặc https
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL phải bắt đầu bằng giao thức http:// hoặc https://")

        # 2. Phải có hostname (tên miền)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL không hợp lệ, không tìm thấy hostname")

        # 3. Chống SSRF: Chặn loopback / localhost (so sánh chuỗi chặn danh sách đen, không
        # phải bind địa chỉ server — ruff's bandit rule S104 hiểu nhầm "0.0.0.0" ở đây)
        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0"):  # noqa: S104
            raise ValueError("Không được phép quét localhost hoặc địa chỉ loopback cục bộ")

        # 4. Chặn dải IP Private nội bộ (10.x, 192.168.x, 172.16-31.x)
        try:
            ip = ipaddress.ip_address(hostname)
            is_ip = True
        except ValueError:
            # Không phải dạng IP thuần (là tên miền chữ như example.com)
            is_ip = False
        # Nếu là IP thật mà lại là Private hoặc Loopback thì CHẶN NGAY
        if is_ip and not ip.is_global:
            raise ValueError("Không được phép quét dải địa chỉ IP mạng nội bộ (Private IP)")
        return url_str


class ScanCreateResponse(BaseModel):
    """Thông tin trả về ngay khi khởi tạo thành công một phiên quét."""

    scan_id: str = Field(..., description="Mã định danh duy nhất của lượt quét (UUID)")
    target_url: str = Field(..., description="URL mục tiêu đã được chuẩn hóa")
    mode: ScanMode = Field(default=ScanMode.FULL, description="Chế độ quét đã chọn")
    status: ScanStatus = Field(default=ScanStatus.PENDING, description="Trạng thái hiện tại")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Thời gian khởi tạo phiên quét (UTC)",
    )


# --- Các model kết quả từ Sprint 1 giữ nguyên ---
class Finding(BaseModel):
    module: str
    name: str
    severity: SeverityLevel
    description: str
    remediation: str
    url: str | None = None


class ScoringResult(BaseModel):
    score: int
    grade: str
    total_findings: int


class ScanResponse(BaseModel):
    scan_id: str | None = None
    url: str
    status: ScanStatus = ScanStatus.COMPLETED
    total_findings: int
    findings: list[Finding]
    scoring: ScoringResult


class ScanDetailResponse(BaseModel):
    """Chi tiết đầy đủ thông tin và kết quả của một phiên quét."""

    scan_id: str = Field(..., description="Mã định danh duy nhất của lượt quét")
    target_url: str = Field(..., description="URL mục tiêu đã quét")
    mode: ScanMode = Field(default=ScanMode.FULL, description="Chế độ quét đã dùng")
    status: ScanStatus = Field(..., description="Trạng thái hiện tại của phiên quét")
    created_at: datetime = Field(..., description="Thời điểm khởi tạo (UTC)")
    completed_at: datetime | None = Field(
        default=None, description="Thời điểm hoàn thành (UTC)"
    )
    total_findings: int = Field(default=0, description="Tổng số lỗ hổng phát hiện được")
    findings: list[Finding] = Field(
        default_factory=list, description="Danh sách các phát hiện an ninh"
    )
    scoring: ScoringResult | None = Field(
        default=None, description="Kết quả tính điểm an ninh"
    )


class ScanStreamEvent(BaseModel):
    """Cấu trúc dữ liệu cho mỗi sự kiện bắn về client qua SSE stream."""

    event: ScanEventType = Field(..., description="Loại sự kiện")
    scan_id: str = Field(..., description="Mã định danh lượt quét")
    progress: int = Field(..., ge=0, le=100, description="Tiến độ quét (0-100%)")
    message: str = Field(..., description="Mô tả thông điệp gửi tới người dùng")
    module: str | None = Field(default=None, description="Tên module đang xử lý")
    findings: list[Finding] | None = Field(
        default=None, description="Danh sách các lỗ hổng mới phát hiện trong bước này"
    )
    data: dict[str, Any] | None = Field(
        default=None, description="Dữ liệu tổng hợp (như điểm số, kết quả hoàn chỉnh)"
    )


class ScanCancelResponse(BaseModel):
    """Thông tin trả về khi yêu cầu hủy phiên quét."""

    scan_id: str = Field(..., description="Mã định danh lượt quét")
    status: ScanStatus = Field(default=ScanStatus.CANCELLED, description="Trạng thái sau khi hủy")
    message: str = Field(
        default="Đã hủy phiên quét thành công",
        description="Thông báo kết quả thao tác hủy",
    )


