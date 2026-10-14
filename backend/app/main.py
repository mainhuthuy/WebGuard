"""Main application entrypoint for WebGuard API service."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core import (
    RequestLoggingMiddleware,
    Settings,
    get_settings,
    register_exception_handlers,
    setup_logging,
)

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Quản lý vòng đời ứng dụng: Khởi chạy logging, DB tables và thông báo khi bật/tắt server."""
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

    # Khởi tạo tables trong database nếu chưa có
    from app.db.session import init_db

    init_db()

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
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # 3. Kích hoạt bộ xử lý lỗi toàn cục (Global Error Handlers)
    register_exception_handlers(app)

    # 4. Lưu settings vào app state để các router con truy cập được
    app.state.settings = settings

    # 5. Gắn các API Routers v1 vào ứng dụng
    app.include_router(api_router, prefix="/api/v1")

    # 5. Endpoint gốc kiểm tra API
    @app.get("/", tags=["General"])
    async def root() -> dict[str, str]:
        """Endpoint gốc kiểm tra API còn sống."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs": "/docs" if not settings.is_production else "disabled",
        }

    return app


app = create_application()
