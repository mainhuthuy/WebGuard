"""API route for health check and service status."""

from datetime import datetime, timezone
import logging
import platform

from typing import Any

from fastapi import APIRouter, Request, status

from app.api.v1.scan import scan_jobs

logger = logging.getLogger("app.api.v1.health")

router = APIRouter(tags=["Health"])

# Ghi lại thời điểm server khởi động (module-level = chạy 1 lần khi import)
_started_at = datetime.now(timezone.utc)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Kiểm tra trạng thái dịch vụ",
    description="Trả về metadata hệ thống bao gồm uptime, phiên bản, "
    "môi trường và thống kê quét.",
)
async def health_check(request: Request) -> dict[str, Any]:
    """Health check endpoint cung cấp metadata và thống kê hệ thống."""
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)
    uptime_seconds = (now - _started_at).total_seconds()

    return {
        "status": "healthy",
        "service": "webguard-backend",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "demo_mode": settings.DEMO_MODE,
        "python_version": platform.python_version(),
        "started_at": _started_at.isoformat(),
        "uptime_seconds": round(uptime_seconds, 1),
        "total_scans": len(scan_jobs),
    }
