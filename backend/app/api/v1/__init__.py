"""API v1 router bundle."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.history import router as history_router
from app.api.v1.report import router as report_router
from app.api.v1.scan import router as scan_router

api_router = APIRouter()
api_router.include_router(scan_router)
api_router.include_router(report_router)
api_router.include_router(history_router)
api_router.include_router(health_router)


__all__ = ["api_router"]


