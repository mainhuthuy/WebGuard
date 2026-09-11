from unittest.mock import AsyncMock, patch
import httpx
import pytest
from app.modules.cookies import CookiesModule

@pytest.mark.asyncio
async def test_cookies_missing_flags(mock_insecure_cookie_response):
    """Cookie thiếu cờ HttpOnly, Secure, SameSite phải sinh ra 3 findings."""
    module = CookiesModule()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_insecure_cookie_response
        findings = await module.scan("https://example.com")

        assert len(findings) == 3
        missing_flags = [f["flag_missing"] for f in findings]
        assert "HttpOnly" in missing_flags
        assert "Secure" in missing_flags
        assert "SameSite" in missing_flags

@pytest.mark.asyncio
async def test_cookies_secure(mock_secure_cookie_response):
    """Cookie có đủ cả 3 flags thì không có finding nào."""
    module = CookiesModule()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_secure_cookie_response
        findings = await module.scan("https://example.com")

        assert len(findings) == 0

@pytest.mark.asyncio
async def test_cookies_no_cookies_set():
    """Website không set bất kỳ cookie nào thì trả về rỗng."""
    module = CookiesModule()
    empty_cookie_response = httpx.Response(
        status_code=200,
        headers={"Content-Type": "text/html"},
        request=httpx.Request("GET", "https://example.com")
    )
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = empty_cookie_response
        findings = await module.scan("https://example.com")

        assert len(findings) == 0
