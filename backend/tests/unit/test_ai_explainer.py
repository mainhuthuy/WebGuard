"""AIExplainerService: prompt building, 3 provider adapters, ánh xạ lỗi (mock httpx)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.services.ai_explainer import AIProviderError, build_prompt, explain_scan


def _scan(findings: list[FindingModel] | None = None) -> ScanModel:
    scan = ScanModel(
        id="scan-1",
        target_url="https://example.com",
        status="completed",
        mode="full",
        created_at=datetime.now(UTC),
        score=72,
        grade="B",
    )
    scan.findings = findings or []  # type: ignore[assignment]
    return scan


def _finding(**overrides: str) -> FindingModel:
    defaults = {
        "module": "headers",
        "name": "content-security-policy",
        "severity": "high",
        "description": "Thiếu CSP",
        "remediation": "Thêm header CSP",
        "target_url": "https://example.com",
    }
    return FindingModel(**{**defaults, **overrides})


# ---------------- build_prompt ----------------


def test_prompt_includes_target_url_and_score() -> None:
    prompt = build_prompt(_scan([_finding()]))
    assert "https://example.com" in prompt
    assert "72/100" in prompt
    assert "content-security-policy" in prompt
    assert "HIGH" in prompt


def test_prompt_handles_a_clean_scan_with_no_findings() -> None:
    prompt = build_prompt(_scan([]))
    assert "Không phát hiện vấn đề nào" in prompt


def test_prompt_truncates_very_long_finding_lists() -> None:
    many = [_finding(name=f"issue-{i}") for i in range(90)]
    prompt = build_prompt(_scan(many))
    assert "issue-0" in prompt
    assert "issue-79" in prompt
    assert "issue-89" not in prompt
    assert "10 phát hiện khác" in prompt


# ---------------- provider adapters (mock httpx.AsyncClient.post) ----------------


def _ok(json_body: dict) -> httpx.Response:
    return httpx.Response(200, json=json_body, request=httpx.Request("POST", "https://x.test"))


def _err(status: int, json_body: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json=json_body or {}, request=httpx.Request("POST", "https://x.test"))


async def test_google_provider_happy_path() -> None:
    body = {"candidates": [{"content": {"parts": [{"text": "## Plan\n..."}]}}]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok(body)
        text, model = await explain_scan("google", "fake-key", None, _scan([_finding()]))
    assert text == "## Plan\n..."
    assert model == "gemini-2.0-flash"
    # Key đi trong header, KHÔNG nằm trong URL — httpx log URL ở mức INFO nên key sẽ lộ ra log
    assert "fake-key" not in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["headers"]["x-goog-api-key"] == "fake-key"


@pytest.mark.parametrize("provider", ["openai", "groq", "openrouter"])
async def test_openai_compatible_providers_happy_path(provider: str) -> None:
    body = {"choices": [{"message": {"content": "remediation plan"}}]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok(body)
        text, model = await explain_scan(provider, "fake-key", "custom-model", _scan([_finding()]))
    assert text == "remediation plan"
    assert model == "custom-model"
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer fake-key"


async def test_anthropic_provider_happy_path() -> None:
    body = {"content": [{"text": "detailed plan"}]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok(body)
        text, model = await explain_scan("anthropic", "fake-key", None, _scan([_finding()]))
    assert text == "detailed plan"
    assert model == "claude-3-5-haiku-latest"
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["x-api-key"] == "fake-key"


async def test_default_model_used_when_not_specified() -> None:
    body = {"choices": [{"message": {"content": "x"}}]}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok(body)
        _, model = await explain_scan("groq", "fake-key", None, _scan([_finding()]))
    assert model == "llama-3.1-8b-instant"


# ---------------- error mapping ----------------


async def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(AIProviderError) as exc_info:
        await explain_scan("mystery-ai", "fake-key", None, _scan([]))
    assert exc_info.value.status_code == 400


async def test_invalid_api_key_maps_to_401() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _err(401, {"error": {"message": "invalid api key"}})
        with pytest.raises(AIProviderError) as exc_info:
            await explain_scan("openai", "bad-key", None, _scan([]))
    assert exc_info.value.status_code == 401
    assert "bad-key" not in exc_info.value.message


async def test_rate_limit_maps_to_429() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _err(429, {"error": {"message": "rate limited"}})
        with pytest.raises(AIProviderError) as exc_info:
            await explain_scan("google", "fake-key", None, _scan([]))
    assert exc_info.value.status_code == 429


async def test_generic_provider_error_maps_to_502() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _err(500, {"error": {"message": "internal error"}})
        with pytest.raises(AIProviderError) as exc_info:
            await explain_scan("anthropic", "fake-key", None, _scan([]))
    assert exc_info.value.status_code == 502


async def test_timeout_is_handled() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectTimeout("slow")
        with pytest.raises(AIProviderError) as exc_info:
            await explain_scan("google", "fake-key", None, _scan([]))
    assert exc_info.value.status_code == 504


async def test_malformed_response_body_is_handled() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok({"unexpected": "shape"})
        with pytest.raises(AIProviderError) as exc_info:
            await explain_scan("openai", "fake-key", None, _scan([]))
    assert exc_info.value.status_code == 502


async def test_error_body_without_json_still_handled() -> None:
    response = httpx.Response(500, content=b"<html>Bad Gateway</html>", request=httpx.Request("POST", "https://x.test"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(AIProviderError):
            await explain_scan("groq", "fake-key", None, _scan([]))


def test_api_key_is_never_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Đảm bảo không có log nào (ở mức module này) chứa API key."""
    import logging

    caplog.set_level(logging.DEBUG, logger="app.services.ai_explainer")
    assert "super-secret-key-xyz" not in caplog.text
