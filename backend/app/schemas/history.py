"""Pydantic data schemas for scan history queries, pagination, and statistics."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.scan import ScanMode, ScanStatus


class ScanHistoryItem(BaseModel):
    """Thông tin tóm tắt của một phiên quét trong danh sách lịch sử."""

    id: str = Field(..., description="Mã định danh duy nhất của lượt quét (UUID)")
    target_url: str = Field(..., description="URL mục tiêu đã quét")
    status: ScanStatus = Field(..., description="Trạng thái hiện tại")
    mode: ScanMode = Field(default=ScanMode.FULL, description="Chế độ quét đã dùng")
    score: int | None = Field(default=None, description="Điểm an ninh tổng thể (0-100)")
    grade: str | None = Field(default=None, description="Xếp loại an ninh (A+ đến F)")
    total_findings: int = Field(default=0, description="Tổng số lỗ hổng phát hiện được")
    created_at: datetime = Field(..., description="Thời điểm khởi tạo (UTC)")
    completed_at: datetime | None = Field(default=None, description="Thời điểm hoàn tất (UTC)")
    duration_seconds: float | None = Field(default=None, description="Thời gian thực thi quét (giây)")


class ScanHistoryResponse(BaseModel):
    """Kết quả truy vấn danh sách lịch sử quét có phân trang (Pagination)."""

    items: list[ScanHistoryItem] = Field(default_factory=list, description="Danh sách các phiên quét")
    total: int = Field(..., description="Tổng số bản ghi thỏa mãn điều kiện lọc")
    page: int = Field(..., ge=1, description="Trang hiện tại (bắt đầu từ 1)")
    page_size: int = Field(..., ge=1, description="Số lượng bản ghi trên một trang")
    total_pages: int = Field(..., ge=0, description="Tổng số trang")
    has_next: bool = Field(..., description="Có trang kế tiếp hay không")
    has_prev: bool = Field(..., description="Có trang trước đó hay không")


class ScanHistoryStats(BaseModel):
    """Báo cáo số liệu thống kê tổng quan về lịch sử quét trong hệ thống."""

    total_scans: int = Field(default=0, description="Tổng số lần quét đã thực hiện")
    completed_scans: int = Field(default=0, description="Số lần quét hoàn tất thành công")
    failed_scans: int = Field(default=0, description="Số lần quét gặp lỗi thất bại")
    cancelled_scans: int = Field(default=0, description="Số lần quét bị người dùng hủy")
    average_score: float | None = Field(default=None, description="Điểm an ninh trung bình của các web đã quét")
    grade_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Số lượng website theo từng thang điểm xếp hạng (A+, A, B, C, D, F)",
    )


class HistoryDeleteResponse(BaseModel):
    """Kết quả thao tác xóa lịch sử quét."""

    deleted: bool = Field(..., description="Trạng thái xóa thành công hay không")
    message: str = Field(..., description="Thông báo chi tiết kết quả xóa")
    deleted_count: int = Field(default=1, description="Số lượng bản ghi đã được xóa")
