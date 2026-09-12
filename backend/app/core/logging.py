"""Structured logging setup for WebGuard."""

from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    """Định dạng log ra chuỗi JSON chuẩn cho môi trường Production / Cloud."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Nếu có các thông tin request đính kèm thì đẩy vào JSON
        for attr in ("request_id", "status_code", "duration_ms", "client_ip", "method", "path"):
            val = getattr(record, attr, None)
            if val is not None:
                log_payload[attr] = val

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Định dạng log có màu sắc trực quan khi chạy ở máy local (Development)."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan (Xanh lơ)
        logging.INFO: "\033[32m",      # Green (Xanh lá)
        logging.WARNING: "\033[33m",   # Yellow (Vàng)
        logging.ERROR: "\033[31m",     # Red (Đỏ)
        logging.CRITICAL: "\033[41m",  # Red Background (Nền đỏ)
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_str = f"{color}{record.levelname:<8}{self.RESET}"

        req_id = getattr(record, "request_id", None)
        prefix = f"[{req_id}] " if req_id else ""

        msg = record.getMessage()
        formatted = f"[{time_str}] {level_str} {record.name}: {prefix}{msg}"

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """Hàm cấu hình hệ thống logging cho toàn bộ ứng dụng."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Xóa các handler mặc định cũ để tránh bị in log 2 lần
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)

    if log_format.lower() == "json":
        stream_handler.setFormatter(JSONFormatter())
    else:
        stream_handler.setFormatter(ColoredConsoleFormatter())

    root_logger.addHandler(stream_handler)

    # Đồng bộ cấu hình log cho Uvicorn và FastAPI
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "app"):
        sub_logger = logging.getLogger(logger_name)
        sub_logger.setLevel(level)
        sub_logger.propagate = True
