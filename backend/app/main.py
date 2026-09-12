"""Main application entrypoint for WebGuard API service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import (
    RequestLoggingMiddleware,
    Settings,
    get_settings,
    register_exception_handlers,
    setup_logging,
)

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Quản lý vòng đời ứng dụng: Khởi chạy logging và thông báo khi bật/tắt server."""
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info(
        f"Khởi động {settings.APP_NAME} v{settings.APP_VERSION} "
        f"[env={settings.ENV}, debug={settings.DEBUG}]"
    )
    yield
    logger.info(f"Đang tắt ứng dụng {settings.APP_NAME}")


def create_application(settings: Settings | None = None) -> FastAPI:
    """Factory function để tạo và cấu hình ứng dụng FastAPI."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # 1. Gắn Middleware đo thời gian và Request ID
    app.add_middleware(RequestLoggingMiddleware)

    # 2. Cấu hình CORS an toàn theo biến môi trường
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # 3. Kích hoạt bộ xử lý lỗi toàn cục (Global Error Handlers)
    register_exception_handlers(app)

    # 4. Các endpoint cơ bản ban đầu
    @app.get("/", tags=["General"])
    async def root() -> dict[str, str]:
        """Endpoint gốc kiểm tra API còn sống."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs": "/docs" if not settings.is_production else "disabled",
        }

    @app.get("/api/v1/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        """Health check endpoint cung cấp metadata hệ thống."""
        return {
            "status": "healthy",
            "service": "webguard-backend",
            "version": settings.APP_VERSION,
            "environment": settings.ENV,
            "demo_mode": settings.DEMO_MODE,
        }

    return app


# Instance mặc định để máy chủ Uvicorn gọi chạy
app = create_application()
