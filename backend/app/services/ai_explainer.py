"""AIExplainerService — Giải thích kết quả quét + đề xuất khắc phục bằng AI (BYOK).

Nguyên tắc thiết kế (quan trọng — đọc trước khi sửa):
- BYOK (Bring Your Own Key): người dùng tự mang API key của CHÍNH họ (lấy từ tài khoản
  free/trả phí của Google/Groq/OpenRouter/OpenAI/Anthropic). WebGuard không sở hữu, không
  lưu trữ, không log lại key này dưới bất kỳ hình thức nào — chỉ dùng đúng 1 lần cho đúng
  1 lệnh gọi API rồi bỏ đi ngay khi request kết thúc.
- AI KHÔNG tự gửi request mới tới target. Nó chỉ đọc dữ liệu findings đã quét sẵn (đang nằm
  trong DB) và viết lại thành giải thích dễ hiểu + kế hoạch khắc phục. Không có tương tác
  chủ động nào thêm với website mục tiêu ở bước này.
- Gọi thẳng REST API chính chủ của từng nhà cung cấp, không tự động hoá đăng nhập web/qua
  trình duyệt của bất kỳ dịch vụ chat nào.
"""

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.models.scan import ScanModel

logger = logging.getLogger("app.services.ai_explainer")

AI_TIMEOUT = 60.0
MAX_FINDINGS_IN_PROMPT = 80
MAX_OUTPUT_TOKENS = 2048


class AIProviderError(Exception):
    """Lỗi khi gọi nhà cung cấp AI — message AN TOÀN để trả thẳng cho người dùng (không chứa key)."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class _ProviderConfig:
    kind: Literal["google", "openai_compatible", "anthropic"]
    base_url: str
    default_model: str


# "openai_compatible" dùng chung 1 schema request/response (chat completions) cho
# OpenAI, Groq và OpenRouter — cả 3 đều tương thích API của OpenAI.
PROVIDERS: dict[str, _ProviderConfig] = {
    "google": _ProviderConfig(
        kind="google",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-2.0-flash",
    ),
    "groq": _ProviderConfig(
        kind="openai_compatible",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.1-8b-instant",
    ),
    "openrouter": _ProviderConfig(
        kind="openai_compatible",
        base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.1-8b-instruct:free",
    ),
    "openai": _ProviderConfig(
        kind="openai_compatible",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
    "anthropic": _ProviderConfig(
        kind="anthropic",
        base_url="https://api.anthropic.com/v1",
        default_model="claude-3-5-haiku-latest",
    ),
}

CATALOGUE_SUMMARY = """\
WebGuard là công cụ audit bảo mật web THỤ ĐỘNG (chỉ đọc response HTTP công khai, không khai \
thác lỗ hổng). Thang mức độ: critical (nguy hiểm ngay, ưu tiên vá đầu tiên) > high (lỗ hổng \
nghiêm trọng, dễ bị khai thác) > medium (thiếu lớp phòng thủ hoặc lộ thông tin) > low (vá \
khi thuận tiện). WebGuard quét 7 nhóm: headers (HTTP security headers), cookies (cờ bảo mật \
cookie), ssl_tls (chứng chỉ & giao thức TLS), information (lộ file/thông tin nhạy cảm), cors \
(cấu hình CORS), content (phân tích HTML: mixed content, SRI, form...), http_config (hành vi \
HTTP/HTTPS, redirect, method)."""


def _findings_section(scan: ScanModel) -> str:
    lines = []
    for f in scan.findings[:MAX_FINDINGS_IN_PROMPT]:
        lines.append(
            f"- [{f.severity.upper()}] ({f.module}) {f.name}: {f.description} "
            f"| Khắc phục gợi ý sẵn có: {f.remediation}"
        )
    if not lines:
        return "(Không phát hiện vấn đề nào — trang đạt mọi kiểm tra.)"
    extra = len(scan.findings) - MAX_FINDINGS_IN_PROMPT
    text = "\n".join(lines)
    if extra > 0:
        text += f"\n... và {extra} phát hiện khác (đã lược bớt để tiết kiệm độ dài)."
    return text


def build_prompt(scan: ScanModel) -> str:
    """Dựng prompt duy nhất (không có lịch sử hội thoại) từ catalogue + findings của scan."""
    score = scan.score if scan.score is not None else "N/A"
    grade = scan.grade or "N/A"
    return f"""\
{CATALOGUE_SUMMARY}

## Kết quả quét
- URL: {scan.target_url}
- Chế độ quét: {scan.mode}
- Điểm: {score}/100 — Hạng: {grade}
- Tổng số phát hiện: {len(scan.findings)}

## Danh sách phát hiện
{_findings_section(scan)}

## Yêu cầu
Dựa DUY NHẤT vào danh sách phát hiện ở trên (không suy đoán thêm lỗ hổng nào khác ngoài \
danh sách này), hãy viết bằng tiếng Anh, định dạng Markdown:
1. Một đoạn tóm tắt ngắn gọn mức độ rủi ro tổng thể của trang.
2. Kế hoạch khắc phục theo thứ tự ưu tiên (critical/high trước), mỗi mục giải thích ngắn gọn
   TẠI SAO nó quan trọng và các bước khắc phục cụ thể, chi tiết hơn phần remediation gợi ý sẵn.
3. Nếu có nhiều phát hiện cùng nguyên nhân gốc (vd thiếu cả loạt security headers), hãy gộp
   lại thành một khuyến nghị chung thay vì lặp lại từng dòng.
"""


def _error_message_from_body(body: Any) -> str | None:
    """Cố gắng lấy message lỗi từ response JSON của provider (format khác nhau tuỳ hãng)."""
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if isinstance(error, dict):
        return error.get("message")
    if isinstance(error, str):
        return error
    if isinstance(body.get("message"), str):
        return body["message"]
    return None


def _raise_for_status(response: httpx.Response, provider: str) -> None:
    if response.status_code < 400:
        return
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = _error_message_from_body(body)

    if response.status_code in (401, 403):
        raise AIProviderError(
            f"API key bị {provider} từ chối (không hợp lệ hoặc hết quyền truy cập model này).",
            status_code=401,
        )
    if response.status_code == 429:
        raise AIProviderError(
            f"{provider} báo đã vượt giới hạn tốc độ/hạn mức miễn phí. Thử lại sau hoặc đổi model.",
            status_code=429,
        )
    raise AIProviderError(
        f"{provider} trả về lỗi ({response.status_code}): {detail or 'không rõ nguyên nhân'}",
        status_code=502,
    )


async def _call_google(client: httpx.AsyncClient, base_url: str, api_key: str, model: str, prompt: str) -> str:
    # Key goes in a header, never the query string: httpx logs the full request URL at
    # INFO level, which would write the user's key into the server logs.
    url = f"{base_url}/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS},
    }
    response = await client.post(url, json=body, headers=headers)
    _raise_for_status(response, "Google")
    data = response.json()
    try:
        return str(data["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Google trả về phản hồi không đúng định dạng mong đợi.") from exc


async def _call_openai_compatible(
    client: httpx.AsyncClient, base_url: str, api_key: str, model: str, prompt: str, provider_label: str
) -> str:
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    response = await client.post(url, headers=headers, json=body)
    _raise_for_status(response, provider_label)
    data = response.json()
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f"{provider_label} trả về phản hồi không đúng định dạng mong đợi.") from exc


async def _call_anthropic(client: httpx.AsyncClient, base_url: str, api_key: str, model: str, prompt: str) -> str:
    url = f"{base_url}/messages"
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    body = {
        "model": model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = await client.post(url, headers=headers, json=body)
    _raise_for_status(response, "Anthropic")
    data = response.json()
    try:
        return str(data["content"][0]["text"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Anthropic trả về phản hồi không đúng định dạng mong đợi.") from exc


async def explain_scan(
    provider: str, api_key: str, model: str | None, scan: ScanModel
) -> tuple[str, str]:
    """Gọi provider đã chọn để giải thích + đề xuất khắc phục cho `scan`.

    Trả về (nội dung giải thích, tên model thực tế đã dùng). Không bao giờ log `api_key`.
    """
    config = PROVIDERS.get(provider)
    if config is None:
        raise AIProviderError(f"Nhà cung cấp AI '{provider}' không được hỗ trợ.", status_code=400)
    used_model = model or config.default_model
    prompt = build_prompt(scan)

    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            if config.kind == "google":
                text = await _call_google(client, config.base_url, api_key, used_model, prompt)
            elif config.kind == "anthropic":
                text = await _call_anthropic(client, config.base_url, api_key, used_model, prompt)
            else:
                text = await _call_openai_compatible(
                    client, config.base_url, api_key, used_model, prompt, provider_label=provider
                )
    except httpx.TimeoutException as exc:
        raise AIProviderError(
            f"Hết thời gian chờ phản hồi từ {provider} (quá {int(AI_TIMEOUT)}s).", status_code=504
        ) from exc
    except httpx.HTTPError as exc:
        raise AIProviderError(f"Không thể kết nối tới {provider}: lỗi mạng.", status_code=502) from exc

    logger.info(f"AIExplainerService: đã giải thích scan_id={scan.id} qua provider={provider} model={used_model}")
    return text.strip(), used_model
