"""API routes for security scanning operations."""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.core.errors import ScanNotFoundException
from app.core.security import assert_public_target
from app.db.session import get_db
from app.schemas.ai import AIExplainRequest, AIExplainResponse
from app.schemas.scan import (
    Finding,
    ScanCancelResponse,
    ScanCreateRequest,
    ScanCreateResponse,
    ScanDetailResponse,
    ScanEventType,
    ScanMode,
    ScanStatus,
    ScoringResult,
)
from app.services import ai_explainer
from app.services.scan import scan_service

logger = logging.getLogger("app.api.v1.scan")

router = APIRouter(prefix="/scan", tags=["Scan"])

# Bộ nhớ tạm (in-memory store) lưu trạng thái các lượt quét để tương thích ngược và cache nhanh
scan_jobs: dict[str, dict[str, Any]] = {}


@router.post(
    "",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Khởi tạo một phiên quét bảo mật mới",
    description="Nhận URL mục tiêu, kiểm tra tính hợp lệ và trả về scan_id để theo dõi tiến trình.",
)
async def create_scan(
    payload: ScanCreateRequest,
    db: Session = Depends(get_db),
) -> ScanCreateResponse:
    """Tạo lượt quét mới qua ScanService và lưu vào Database."""
    await assert_public_target(payload.url)
    scan = scan_service.create_scan(db=db, target_url=payload.url, mode=payload.mode.value)

    # Đồng bộ cache scan_jobs để tương thích ngược
    scan_jobs[scan.id] = {
        "scan_id": scan.id,
        "target_url": scan.target_url,
        "mode": scan.mode,
        "status": ScanStatus(scan.status),
        "created_at": scan.created_at,
        "findings": [],
    }

    logger.info(f"Đã tạo phiên quét mới: id={scan.id}, target={payload.url}")

    return ScanCreateResponse(
        scan_id=scan.id,
        target_url=scan.target_url,
        mode=ScanMode(scan.mode),
        status=ScanStatus(scan.status),
        created_at=scan.created_at,
    )


@router.get(
    "/{scan_id}/stream",
    summary="Theo dõi tiến trình quét theo thời gian thực (SSE)",
    description="Mở luồng Server-Sent Events (SSE) để nhận tiến độ quét từng bước.",
    response_class=EventSourceResponse,
)
async def stream_scan_progress(
    scan_id: str,
    db: Session = Depends(get_db),
) -> EventSourceResponse:
    """Stream tiến trình quét từng bước về client qua Server-Sent Events và lưu kết quả vào DB."""
    scan = scan_service.get_scan(db, scan_id)
    if not scan and scan_id not in scan_jobs:
        raise ScanNotFoundException(scan_id=scan_id)

    job = scan_jobs.get(scan_id)

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        try:
            if job:
                job["status"] = ScanStatus.RUNNING

            async for step_event in scan_service.stream_scan(scan_id=scan_id, db=db):
                # Đồng bộ in-memory job cho tương thích ngược
                if job:
                    if step_event["event"] == ScanEventType.COMPLETE.value:
                        job["status"] = ScanStatus.COMPLETED
                        job["findings"] = step_event.get("findings") or []
                        event_data = step_event.get("data")
                        if isinstance(event_data, dict) and "scoring" in event_data:
                            job["scoring"] = event_data["scoring"]
                        job["completed_at"] = datetime.now(UTC)
                    elif step_event["event"] == ScanEventType.ERROR.value:
                        job["status"] = ScanStatus.FAILED
                        job["completed_at"] = datetime.now(UTC)

                yield ServerSentEvent(
                    event=step_event["event"],
                    data=json.dumps(step_event, default=str, ensure_ascii=False),
                )
        except Exception as exc:
            logger.exception(f"Lỗi sự cố khi quét scan_id={scan_id}: {exc}")
            if job:
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
async def get_scan_result(
    scan_id: str,
    db: Session = Depends(get_db),
) -> ScanDetailResponse:
    """Trả về chi tiết đầy đủ của một phiên quét theo scan_id (lấy từ Database hoặc cache)."""
    scan = scan_service.get_scan(db, scan_id)

    if scan:
        findings_list = [
            Finding(
                module=f.module,
                name=f.name,
                severity=f.severity,
                description=f.description,
                remediation=f.remediation,
                url=f.target_url,
            )
            for f in scan.findings
        ]
        scoring_result: ScoringResult | None = None
        if scan.score is not None and scan.grade is not None:
            scoring_result = ScoringResult(
                score=scan.score,
                grade=scan.grade,
                total_findings=len(findings_list),
            )

        return ScanDetailResponse(
            scan_id=scan.id,
            target_url=scan.target_url,
            mode=ScanMode(scan.mode),
            status=ScanStatus(scan.status),
            created_at=scan.created_at,
            completed_at=scan.completed_at,
            total_findings=len(findings_list),
            findings=findings_list,
            scoring=scoring_result,
        )

    # Fallback kiểm tra trong in-memory scan_jobs nếu có
    if scan_id not in scan_jobs:
        raise ScanNotFoundException(scan_id=scan_id)

    job = scan_jobs[scan_id]
    findings: list[dict[str, Any]] = job.get("findings") or []
    scoring_data = job.get("scoring")

    scoring_res: ScoringResult | None = None
    if isinstance(scoring_data, dict) and "score" in scoring_data:
        scoring_res = ScoringResult(
            score=scoring_data["score"],
            grade=scoring_data["grade"],
            total_findings=scoring_data.get("total_findings", len(findings)),
        )

    return ScanDetailResponse(
        scan_id=scan_id,
        target_url=job["target_url"],
        mode=ScanMode(job.get("mode", "full")),
        status=job["status"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        total_findings=len(findings),
        findings=findings,
        scoring=scoring_res,
    )


@router.post(
    "/{scan_id}/cancel",
    response_model=ScanCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy một phiên quét đang diễn ra",
    description="Hủy tiến trình quét bảo mật nếu đang ở trạng thái pending hoặc running.",
)
async def cancel_scan(
    scan_id: str,
    db: Session = Depends(get_db),
) -> ScanCancelResponse:
    """Hủy một lượt quét đang chờ hoặc đang chạy."""
    scan = scan_service.get_scan(db, scan_id)
    if not scan and scan_id not in scan_jobs:
        raise ScanNotFoundException(scan_id=scan_id)

    success = scan_service.cancel_scan(db, scan_id)
    if not success:
        # Nếu scan đã hoàn tất hoặc thất bại trước đó
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể hủy phiên quét {scan_id} vì đã kết thúc hoặc không thể hủy.",
        )

    # Đồng bộ in-memory cache
    if scan_id in scan_jobs:
        scan_jobs[scan_id]["status"] = ScanStatus.CANCELLED

    return ScanCancelResponse(
        scan_id=scan_id,
        status=ScanStatus.CANCELLED,
        message=f"Đã hủy thành công phiên quét {scan_id}",
    )


@router.post(
    "/{scan_id}/explain",
    response_model=AIExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="Giải thích kết quả quét và đề xuất khắc phục bằng AI (BYOK)",
    description=(
        "Gửi các phát hiện ĐÃ CÓ của phiên quét tới nhà cung cấp AI do người dùng chọn, dùng "
        "API key của chính người dùng (BYOK). Không gửi thêm bất kỳ request mới nào tới target; "
        "API key chỉ dùng cho đúng 1 lần gọi này và không được lưu lại ở phía server."
    ),
)
async def explain_scan(
    scan_id: str,
    payload: AIExplainRequest,
    db: Session = Depends(get_db),
) -> AIExplainResponse:
    """Nhờ AI (key của người dùng) diễn giải findings đã quét và đề xuất khắc phục chi tiết."""
    scan = scan_service.get_scan(db, scan_id)
    if not scan:
        raise ScanNotFoundException(scan_id=scan_id)
    if scan.status != ScanStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiên quét {scan_id} chưa hoàn tất, chưa có dữ liệu để AI giải thích.",
        )

    try:
        explanation, used_model = await ai_explainer.explain_scan(
            provider=payload.provider.value,
            api_key=payload.api_key,
            model=payload.model,
            scan=scan,
        )
    except ai_explainer.AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return AIExplainResponse(provider=payload.provider, model=used_model, explanation=explanation)
