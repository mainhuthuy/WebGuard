"""API routes for scan history management operations."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.errors import ScanNotFoundException
from app.db.session import get_db
from app.schemas.history import (
    HistoryDeleteResponse,
    ScanHistoryResponse,
    ScanHistoryStats,
)
from app.services.history import history_service

logger = logging.getLogger("app.api.v1.history")

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "",
    response_model=ScanHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách lịch sử các phiên quét",
    description="Truy vấn danh sách lịch sử quét có phân trang, hỗ trợ tìm kiếm URL, lọc theo trạng thái/grade và sắp xếp.",
)
async def list_scan_history(
    page: int = Query(default=1, ge=1, description="Số thứ tự trang (bắt đầu từ 1)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Số bản ghi trên mỗi trang"),
    search_url: str | None = Query(default=None, description="Tìm kiếm theo URL mục tiêu"),
    status: str | None = Query(default=None, description="Lọc theo trạng thái: pending, running, completed, failed, cancelled"),
    grade: str | None = Query(default=None, description="Lọc theo xếp hạng: A+, A, B, C, D, F"),
    sort_by: str = Query(default="created_at", description="Trường cần sắp xếp: created_at hoặc score"),
    sort_order: str = Query(default="desc", description="Thứ tự sắp xếp: desc (giảm dần) hoặc asc (tăng dần)"),
    from_date: datetime | None = Query(default=None, description="Lọc từ ngày (UTC)"),
    to_date: datetime | None = Query(default=None, description="Lọc đến ngày (UTC)"),
    db: Session = Depends(get_db),
) -> ScanHistoryResponse:
    """Truy vấn danh sách lịch sử quét qua HistoryService."""
    return history_service.get_history(
        db=db,
        page=page,
        page_size=page_size,
        search_url=search_url,
        status=status,
        grade=grade,
        sort_by=sort_by,
        sort_order=sort_order,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/stats",
    response_model=ScanHistoryStats,
    status_code=status.HTTP_200_OK,
    summary="Thống kê tổng quan lịch sử quét",
    description="Trả về tổng số phiên quét, tỷ lệ thành công/thất bại, điểm trung bình và phân bố grade.",
)
async def get_history_stats(
    db: Session = Depends(get_db),
) -> ScanHistoryStats:
    """Lấy số liệu thống kê lịch sử qua HistoryService."""
    return history_service.get_stats(db=db)


@router.delete(
    "/{scan_id}",
    response_model=HistoryDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Xóa một phiên quét trong lịch sử",
    description="Xóa vĩnh viễn một bản ghi phiên quét và toàn bộ các phát hiện (findings) con liên quan.",
)
async def delete_scan_history_item(
    scan_id: str,
    db: Session = Depends(get_db),
) -> HistoryDeleteResponse:
    """Xóa một bản ghi lịch sử theo scan_id."""
    deleted = history_service.delete_history_item(db=db, scan_id=scan_id)
    if not deleted:
        raise ScanNotFoundException(scan_id=scan_id)

    return HistoryDeleteResponse(
        deleted=True,
        message=f"Đã xóa thành công phiên quét {scan_id} khỏi lịch sử",
        deleted_count=1,
    )


@router.delete(
    "",
    response_model=HistoryDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Dọn dẹp lịch sử quét hàng loạt",
    description="Dọn dẹp toàn bộ lịch sử quét hoặc chỉ xóa các bản ghi cũ hơn số ngày chỉ định.",
)
async def clear_scan_history(
    older_than_days: int | None = Query(
        default=None,
        ge=1,
        description="Chỉ xóa các phiên quét cũ hơn số ngày này (nếu không truyền sẽ xóa toàn bộ)",
    ),
    db: Session = Depends(get_db),
) -> HistoryDeleteResponse:
    """Dọn dẹp lịch sử quét hàng loạt qua HistoryService."""
    count = history_service.clear_history(db=db, older_than_days=older_than_days)
    return HistoryDeleteResponse(
        deleted=True,
        message=f"Đã dọn dẹp thành công {count} bản ghi lịch sử quét",
        deleted_count=count,
    )
