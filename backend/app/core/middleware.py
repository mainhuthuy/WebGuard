"""Custom ASGI middlewares for request tracking, execution timing, and access logging."""

import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.core.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware quản lý Request ID, đo độ trễ phản hồi và ghi access log."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        # 1. Lấy mã X-Request-ID từ client gửi lên (nếu có), hoặc tự sinh mã UUID mới
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # 2. Bắt đầu bấm giờ
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        # 3. Chuyển tiếp request cho API endpoint xử lý
        response: Response = await call_next(request)

        # 4. Tính toán thời gian xử lý (đơn vị mili-giây)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 5. Đính kèm các header hữu ích vào phản hồi gửi về cho client
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms}ms"

        # 6. Ghi log truy cập có cấu trúc
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        )

        return response
