"""Check 3 của CorsModule chỉ nguy hiểm khi Origin lạ thực sự được phản xạ lại."""

from unittest.mock import AsyncMock, patch

import httpx

from app.modules.cors import CorsModule


async def _scan(headers: dict[str, str]) -> list[dict]:
    response = httpx.Response(200, headers=headers, request=httpx.Request("GET", "https://example.com"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response
        return await CorsModule().scan("https://example.com")


async def test_fixed_origin_with_credentials_is_a_valid_config_not_a_finding() -> None:
    """Allow-Origin cố định + Allow-Credentials: true là cấu hình đúng, không phải lỗi."""
    findings = await _scan(
        {
            "access-control-allow-origin": "https://myapp.com",
            "access-control-allow-credentials": "true",
        }
    )
    assert findings == []


async def test_reflection_with_credentials_reports_both_critical_findings() -> None:
    findings = await _scan(
        {
            "access-control-allow-origin": "https://evil.com",
            "access-control-allow-credentials": "true",
        }
    )
    assert sorted(f["name"] for f in findings) == ["cors_credentials_exposed", "cors_origin_reflection"]
    assert all(f["severity"] == "critical" for f in findings)


async def test_reflection_without_credentials_is_only_the_reflection_finding() -> None:
    findings = await _scan({"access-control-allow-origin": "https://evil.com"})
    assert [f["name"] for f in findings] == ["cors_origin_reflection"]


async def test_wildcard_with_credentials_is_only_the_wildcard_finding() -> None:
    """`*` kèm credentials bị trình duyệt từ chối nên không tính là rò cookie."""
    findings = await _scan(
        {"access-control-allow-origin": "*", "access-control-allow-credentials": "true"}
    )
    assert [f["name"] for f in findings] == ["cors_wildcard"]
