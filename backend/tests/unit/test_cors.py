from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.modules.cors import CorsModule


@pytest.mark.asyncio
async def test_cors_wildcard():
    """Server trả về Access-Control-Allow-Origin: * phải bắt được lỗi cors_wildcard."""
    module = CorsModule()
    mock_response = httpx.Response(
        status_code=200,
        headers={"access-control-allow-origin": "*"},
        request=httpx.Request("GET", "https://example.com")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        findings = await module.scan("https://example.com")

        assert len(findings) == 1
        assert findings[0]["name"] == "cors_wildcard"
        assert findings[0]["severity"] == "high"

@pytest.mark.asyncio
async def test_cors_reflection_and_credentials():
    """Server phản hồi origin evil.com và cho phép credentials phải bắt được 2 lỗi Critical."""
    module = CorsModule()
    mock_response = httpx.Response(
        status_code=200,
        headers={
            "access-control-allow-origin": "https://evil.com",
            "access-control-allow-credentials": "true",
        },
        request=httpx.Request("GET", "https://example.com")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        findings = await module.scan("https://example.com")

        names = [f["name"] for f in findings]
        assert "cors_origin_reflection" in names
        assert "cors_credentials_exposed" in names
        for f in findings:
            assert f["severity"] == "critical"

@pytest.mark.asyncio
async def test_cors_secure():
    """Server cấu hình an toàn, không phản hồi evil.com thì không có lỗi."""
    module = CorsModule()
    mock_response = httpx.Response(
        status_code=200,
        headers={"access-control-allow-origin": "https://trusted-domain.com"},
        request=httpx.Request("GET", "https://example.com")
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        findings = await module.scan("https://example.com")

        assert len(findings) == 0
