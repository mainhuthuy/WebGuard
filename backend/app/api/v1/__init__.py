"""API v1 router bundle."""

from fastapi import APIRouter
from app.api.v1.scan import router as scan_router

api_router = APIRouter()
api_router.include_router(scan_router)

__all__ = ["api_router"]
