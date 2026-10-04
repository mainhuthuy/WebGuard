from unittest.mock import AsyncMock, patch

import pytest

from app.modules.headers import HeadersModule


@pytest.mark.asyncio
async def test_headers_all_missing(mock_insecure_headers_response):
    """Website thiếu toàn bộ 10 security headers phải bị phát hiện đủ 10 findings."""
    module = HeadersModule()

    # Mock hàm client.get để trả về response thiếu header mà không cần kết nối mạng
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_insecure_headers_response
        findings = await module.scan("https://insecure-example.com")

        assert len(findings) == 10
        names = [f["name"] for f in findings]
        assert "content-security-policy" in names
        assert "strict-transport-security" in names
        assert "x-frame-options" in names

@pytest.mark.asyncio
async def test_headers_all_present(mock_secure_headers_response):
    """Website có đầy đủ headers thì số finding trả về phải là 0."""
    module = HeadersModule()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_secure_headers_response
        findings = await module.scan("https://secure-example.com")

        assert len(findings) == 0
