"""Custom application exceptions and global error handlers for FastAPI."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings

logger = logging.getLogger("app.core.errors")


# ---------------------------------------------------------------------------
# 1. Custom Domain Exceptions
# ---------------------------------------------------------------------------
class WebGuardException(Exception):
    """Exception gốc cho mọi lỗi nghiệp vụ trong hệ thống WebGuard."""

    def __init__(
        self,
        message: str,
        code: str = "WEBGUARD_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class ScanNotFoundException(WebGuardException):
    """Bắn ra khi không tìm thấy scan_id trong hệ thống."""

    def __init__(self, scan_id: str) -> None:
        super().__init__(
            message=f"Lượt quét với ID '{scan_id}' không tồn tại",
            code="SCAN_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"scan_id": scan_id},
        )


class InvalidTargetException(WebGuardException):
    """Bắn ra khi target URL không hợp lệ hoặc vi phạm chính sách."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            code="INVALID_TARGET_URL",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ScanExecutionException(WebGuardException):
    """Bắn ra khi tiến trình quét ngầm gặp sự cố không thể hoàn thành."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            code="SCAN_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class RateLimitExceededException(WebGuardException):
    """Bắn ra khi demo vượt quá số lượt quét cho phép."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            message=f"Đã chạm giới hạn {limit} lượt quét demo trong ngày.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"limit": limit},
        )


# ---------------------------------------------------------------------------
# 2. Standard Error Response Builder
# ---------------------------------------------------------------------------
def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Đóng gói response lỗi thành JSON format chuẩn Enterprise."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
    )


# ---------------------------------------------------------------------------
# 3. Global Exception Handlers
# ---------------------------------------------------------------------------
async def webguard_exception_handler(
    request: Request, exc: WebGuardException
) -> JSONResponse:
    """Bắt các domain exception do chính mình định nghĩa."""
    logger.warning(
        f"Domain error [{exc.code}] on {request.method} {request.url.path}: {exc.message}"
    )
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Bắt lỗi dữ liệu đầu vào không hợp lệ từ Pydantic (HTTP 422)."""
    formatted_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        formatted_errors.append(
            {
                "field": loc,
                "message": err.get("msg"),
                "type": err.get("type"),
            }
        )

    logger.warning(
        f"Validation failed on {request.method} {request.url.path}: {formatted_errors}"
    )
    # Dùng số 422 trực tiếp: Starlette đã đổi tên hằng số (ENTITY -> CONTENT) và truy cập
    # hằng số cũ sẽ phát DeprecationWarning, kể cả khi dùng làm default của getattr().
    return create_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại.",
        details=formatted_errors,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Bắt các lỗi HTTP thông thường (404 Not Found, 403 Forbidden...)."""
    logger.warning(
        f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
    )
    return create_error_response(
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=exc.detail,
        details=None,
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Bắt toàn bộ lỗi bất ngờ (500) chưa được dự liệu trước để tránh sập app."""
    settings = get_settings()
    logger.exception(
        f"Unhandled exception during {request.method} {request.url.path}: {exc}"
    )
    # Nếu ở môi trường dev thì hiển thị chi tiết để debug, production thì giấu đi
    error_details = str(exc) if settings.DEBUG else None

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="Đã xảy ra lỗi máy chủ nội bộ không mong muốn.",
        details=error_details,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký toàn bộ các bộ xử lý lỗi này vào ứng dụng FastAPI."""
    app.add_exception_handler(WebGuardException, webguard_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
