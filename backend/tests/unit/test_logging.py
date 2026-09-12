"""Unit tests for structured logging."""

import json
import logging
from app.core.logging import ColoredConsoleFormatter, JSONFormatter, setup_logging


def test_json_formatter() -> None:
    """Kiểm tra JSONFormatter xuất ra đúng chuẩn JSON và đủ các trường."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=42,
        msg="Test logging message",
        args=(),
        exc_info=None,
    )
    # Giả lập các thuộc tính request được gắn vào record
    record.request_id = "req-12345"  # type: ignore[attr-defined]
    record.duration_ms = 12.34       # type: ignore[attr-defined]
    record.status_code = 200         # type: ignore[attr-defined]

    formatted_str = formatter.format(record)
    parsed = json.loads(formatted_str)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test logging message"
    assert parsed["logger"] == "test_logger"
    assert parsed["request_id"] == "req-12345"
    assert parsed["duration_ms"] == 12.34
    assert parsed["status_code"] == 200
    assert "timestamp" in parsed


def test_console_formatter() -> None:
    """Kiểm tra ColoredConsoleFormatter định dạng log đẹp khi chạy local."""
    formatter = ColoredConsoleFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test_path.py",
        lineno=10,
        msg="Lỗi thử nghiệm",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "ERROR" in formatted
    assert "Lỗi thử nghiệm" in formatted


def test_setup_logging() -> None:
    """Kiểm tra hàm setup_logging cấu hình đúng cho root logger."""
    setup_logging(log_level="DEBUG", log_format="json")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0].formatter, JSONFormatter)
