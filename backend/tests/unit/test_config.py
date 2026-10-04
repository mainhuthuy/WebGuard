"""Unit tests for configuration settings."""

import pytest

from app.core.config import Settings


def test_default_settings() -> None:
    """Kiểm tra các giá trị mặc định khi không truyền biến môi trường."""
    settings = Settings(_env_file=None)
    assert settings.APP_NAME == "WebGuard API"
    assert settings.PORT == 8000
    assert settings.DEBUG is True
    assert not settings.is_production


def test_cors_origins_parsing() -> None:
    """Kiểm tra hàm assemble_cors_origins xử lý được nhiều kiểu định dạng CORS."""
    # 1. Truyền dạng list trực tiếp
    s1 = Settings(CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"], _env_file=None)
    assert s1.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]

    # 2. Truyền dạng chuỗi phân tách bằng dấu phẩy
    s2 = Settings(CORS_ORIGINS="http://localhost:3000, https://app.webguard.io", _env_file=None)
    assert s2.CORS_ORIGINS == ["http://localhost:3000", "https://app.webguard.io"]

    # 3. Truyền dạng chuỗi JSON list
    s3 = Settings(CORS_ORIGINS='["http://example.com", "http://test.com"]', _env_file=None)
    assert s3.CORS_ORIGINS == ["http://example.com", "http://test.com"]


def test_environment_variable_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra biến môi trường hệ thống tiền tố WEBGUARD_ có ghi đè đúng không."""
    monkeypatch.setenv("WEBGUARD_ENV", "production")
    monkeypatch.setenv("WEBGUARD_PORT", "9000")

    settings = Settings(_env_file=None)
    assert settings.ENV == "production"
    assert settings.PORT == 9000
    assert settings.is_production is True
