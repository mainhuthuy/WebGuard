"""Pydantic schemas cho tính năng 'Giải thích bằng AI' (BYOK — Bring Your Own Key)."""

from enum import Enum

from pydantic import BaseModel, Field


class AIProvider(str, Enum):
    """Các nhà cung cấp AI được hỗ trợ. Người dùng tự mang API key của họ (BYOK)."""

    GOOGLE = "google"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AIExplainRequest(BaseModel):
    """Payload gửi lên để nhờ AI giải thích + đề xuất khắc phục cho một phiên quét.

    `api_key` là key của CHÍNH người dùng (lấy từ tài khoản của họ), chỉ dùng cho đúng
    1 lần gọi API này rồi bỏ đi — server không lưu lại key dưới bất kỳ hình thức nào.
    """

    provider: AIProvider = Field(..., description="Nhà cung cấp AI (BYOK)")
    api_key: str = Field(..., min_length=8, description="API key của người dùng, chỉ dùng 1 lần, không lưu lại")
    model: str | None = Field(
        default=None, description="Tên model tùy chọn; bỏ trống sẽ dùng model mặc định của provider"
    )


class AIExplainResponse(BaseModel):
    """Kết quả giải thích + đề xuất khắc phục do AI sinh ra."""

    provider: AIProvider
    model: str = Field(..., description="Model thực tế đã dùng để sinh nội dung")
    explanation: str = Field(..., description="Nội dung giải thích và đề xuất khắc phục (Markdown)")
