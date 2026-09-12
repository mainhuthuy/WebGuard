"""Application configuration settings using Pydantic Settings."""

from functools import lru_cache
import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for WebGuard backend service."""

    # Cấu hình nạp: tự tìm file .env và chỉ đọc các biến có tiền tố WEBGUARD_
    model_config = SettingsConfigDict(
        env_prefix="WEBGUARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Thông tin ứng dụng cơ bản
    APP_NAME: str = "WebGuard API"
    APP_DESCRIPTION: str = "Automated Web Security Assessment & Misconfiguration Scanner"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"  # development | production | testing
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 2. Cấu hình CORS (cho phép frontend gọi API)
    CORS_ORIGINS: list[str] | str = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # 3. Database
    DB_URL: str = "sqlite:///./webguard.db"

    # 4. Scanner Engine Options
    SCAN_TIMEOUT: int = 30
    MAX_CONCURRENT_SCANS: int = 3

    # 5. Chế độ Demo (dành cho bản online demo sau này)
    DEMO_MODE: bool = False
    DEMO_RATE_LIMIT: int = 5

    # 6. Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"  # "console" hoặc "json"

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Chuẩn hóa CORS_ORIGINS: dù nhập chuỗi phẩy hay list thì đều ra list[str]."""
        if isinstance(v, str):
            stripped = v.strip()
            # Nếu truyền dạng chuỗi JSON ["http://localhost:3000"]
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except json.JSONDecodeError:
                    pass
            # Nếu truyền dạng chuỗi cách nhau bằng dấu phẩy: "http://localhost:3000, http://localhost:5173"
            return [item.strip() for item in stripped.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v]
        return ["*"]

    @property
    def is_production(self) -> bool:
        """Hàm tiện ích kiểm tra xem có đang chạy ở production không."""
        return self.ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton pattern: Đọc file cấu hình 1 lần duy nhất và cache lại trong RAM."""
    return Settings()
