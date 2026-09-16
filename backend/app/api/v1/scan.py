"""API routes for security scanning operations."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import json
import logging
from typing import Any
import uuid

from fastapi import APIRouter, status
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.core.errors import ScanNotFoundException
from app.modules.scanner import Scanner
from app.schemas.scan import (
    ScanCreateRequest,
    ScanCreateResponse,
    ScanDetailResponse,
    ScanEventType,
    ScanStatus,
    ScoringResult,
)

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


@router.get(
    "/{scan_id}/stream",
    summary="Theo dõi tiến trình quét theo thời gian thực (SSE)",
    description="Mở luồng Server-Sent Events (SSE) để nhận tiến độ quét từng bước.",
    response_class=EventSourceResponse,
)
async def stream_scan_progress(scan_id: str) -> EventSourceResponse:
    """Stream tiến trình quét từng bước về client qua Server-Sent Events."""
    if scan_id not in scan_jobs:
        raise ScanNotFoundException(scan_id=scan_id)

    job = scan_jobs[scan_id]

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        # Trường hợp 1: Lượt quét đã hoàn thành trước đó (khi client kết nối lại)
        if job["status"] == ScanStatus.COMPLETED:
            completed_findings: list[dict[str, Any]] = job.get("findings") or []
            scoring_data: dict[str, Any] = job.get("scoring") or {}
            replayed_event: dict[str, Any] = {
                "event": ScanEventType.COMPLETE.value,
                "scan_id": scan_id,
                "progress": 100,
                "message": "Phiên quét đã hoàn tất từ trước.",
                "module": None,
                "findings": completed_findings,
                "data": {
                    "url": job["target_url"],
                    "total_findings": len(completed_findings),
                    "scoring": scoring_data,
                },
            }
            yield ServerSentEvent(
                event=ScanEventType.COMPLETE.value,
                data=json.dumps(replayed_event, default=str, ensure_ascii=False),
            )
            return

        # Trường hợp 2: Bắt đầu tiến trình quét và phát sự kiện
        job["status"] = ScanStatus.RUNNING
        scanner = Scanner()
        target_url = job["target_url"]

        try:
            async for step_event in scanner.scan_stream(url=target_url, scan_id=scan_id):
                # Lưu kết quả khi quét xong
                if step_event["event"] == ScanEventType.COMPLETE.value:
                    job["status"] = ScanStatus.COMPLETED
                    job["findings"] = step_event["findings"]
                    event_data = step_event.get("data")
                    if isinstance(event_data, dict) and "scoring" in event_data:
                        job["scoring"] = event_data["scoring"]
                    else:
                        empty_scoring: dict[str, Any] = {}
                        job["scoring"] = empty_scoring
                    job["completed_at"] = datetime.now(timezone.utc)

                yield ServerSentEvent(
                    event=step_event["event"],
                    data=json.dumps(step_event, default=str, ensure_ascii=False),
                )
        except Exception as exc:
            logger.exception(f"Lỗi sự cố khi quét scan_id={scan_id}: {exc}")
            job["status"] = ScanStatus.FAILED
            empty_findings: list[dict[str, Any]] = []
            error_event: dict[str, Any] = {
                "event": ScanEventType.ERROR.value,
                "scan_id": scan_id,
                "progress": 100,
                "message": f"Quá trình quét gặp sự cố ngoài dự kiến: {exc}",
                "module": None,
                "findings": empty_findings,
                "data": None,
            }
            yield ServerSentEvent(
                event=ScanEventType.ERROR.value,
                data=json.dumps(error_event, default=str, ensure_ascii=False),
            )

    return EventSourceResponse(event_generator())


@router.get(
    "/{scan_id}",
    response_model=ScanDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết kết quả một lượt quét",
    description="Truy vấn toàn bộ thông tin và findings của một phiên quét đã tạo.",
)
async def get_scan_result(scan_id: str) -> ScanDetailResponse:
    """Trả về chi tiết đầy đủ của một phiên quét theo scan_id."""
    if scan_id not in scan_jobs:
        raise ScanNotFoundException(scan_id=scan_id)

    job = scan_jobs[scan_id]
    findings: list[dict[str, Any]] = job.get("findings") or []
    scoring_data = job.get("scoring")

    # Đóng gói kết quả chấm điểm (chỉ khi quét hoàn tất)
    scoring_result: ScoringResult | None = None
    if isinstance(scoring_data, dict) and "score" in scoring_data:
        scoring_result = ScoringResult(
            score=scoring_data["score"],
            grade=scoring_data["grade"],
            total_findings=scoring_data.get("total_findings", len(findings)),
        )

    return ScanDetailResponse(
        scan_id=scan_id,
        target_url=job["target_url"],
        status=job["status"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        total_findings=len(findings),
        findings=findings,
        scoring=scoring_result,
    )
