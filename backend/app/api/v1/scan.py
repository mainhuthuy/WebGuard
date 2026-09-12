"""API routes for security scanning operations."""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from fastapi import APIRouter, status

from app.schemas.scan import ScanCreateRequest, ScanCreateResponse, ScanStatus

logger = logging.getLogger("app.api.v1.scan")

router = APIRouter(prefix="/scan", tags=["Scan"])

# Bộ nhớ tạm (in-memory store) lưu trạng thái các lượt quét
scan_jobs: dict[str, dict[str, Any]] = {}


@router.post(
    "",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Khởi tạo một phiên quét bảo mật mới",
    description="Nhận URL mục tiêu, kiểm tra tính hợp lệ và trả về scan_id để theo dõi tiến trình.",
)
async def create_scan(payload: ScanCreateRequest) -> ScanCreateResponse:
    """Tạo lượt quét mới và sinh scan_id."""
    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Khai báo rõ kiểu dữ liệu của list findings rỗng
    empty_findings: list[dict[str, Any]] = []

    # Lưu tạm thông tin scan vào bộ nhớ
    scan_record: dict[str, Any] = {
        "scan_id": scan_id,
        "target_url": payload.url,
        "status": ScanStatus.PENDING,
        "created_at": now,
        "findings": empty_findings,
    }
    scan_jobs[scan_id] = scan_record

    logger.info(f"Đã tạo phiên quét mới: id={scan_id}, target={payload.url}")

    return ScanCreateResponse(
        scan_id=scan_id,
        target_url=payload.url,
        status=ScanStatus.PENDING,
        created_at=now,
    )
