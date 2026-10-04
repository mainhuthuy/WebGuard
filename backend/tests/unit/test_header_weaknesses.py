"""HeadersModule: header CÓ mặt nhưng giá trị yếu cũng phải bị phát hiện."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.modules.headers import HeadersModule

SECURE = {
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "same-origin",
}


async def _weak(**overrides: str) -> list[str]:
    """Quét một site đủ header, ghi đè một vài header, trả về tên các finding."""
    headers = {**SECURE}
    for key, value in overrides.items():
        headers[key.replace("_", "-")] = value
    response = httpx.Response(200, headers=headers, request=httpx.Request("GET", "https://e.com"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response
        findings = await HeadersModule().scan("https://e.com")
    return sorted(f["name"] for f in findings)


async def test_secure_values_produce_no_findings() -> None:
    assert await _weak() == []


@pytest.mark.parametrize(
    ("csp", "expected"),
    [
        ("default-src 'self' 'unsafe-inline'", ["csp_unsafe_inline"]),
        ("script-src 'self' 'unsafe-eval'", ["csp_unsafe_eval"]),
        ("script-src *", ["csp_wildcard_source"]),
        ("script-src 'self' https:", ["csp_wildcard_source"]),
        ("default-src 'self'; script-src 'self' data:", ["csp_wildcard_source"]),
    ],
)
async def test_weak_csp_is_reported(csp: str, expected: list[str]) -> None:
    assert await _weak(Content_Security_Policy=csp) == expected


async def test_unsafe_inline_is_ignored_when_a_nonce_is_present() -> None:
    csp = "script-src 'self' 'unsafe-inline' 'nonce-abc123'"
    assert await _weak(Content_Security_Policy=csp) == []


async def test_script_src_overrides_default_src() -> None:
    """default-src yếu nhưng script-src chặt chẽ → script đã an toàn."""
    csp = "default-src 'unsafe-inline'; script-src 'self'"
    assert await _weak(Content_Security_Policy=csp) == []


async def test_csp_without_script_directives_is_not_judged() -> None:
    assert await _weak(Content_Security_Policy="frame-ancestors 'none'") == []


async def test_short_hsts_max_age() -> None:
    value = "max-age=3600; includeSubDomains"
    assert await _weak(Strict_Transport_Security=value) == ["hsts_short_max_age"]


async def test_hsts_without_include_subdomains() -> None:
    assert await _weak(Strict_Transport_Security="max-age=31536000") == [
        "hsts_missing_include_subdomains"
    ]


async def test_hsts_without_max_age_counts_as_short() -> None:
    names = await _weak(Strict_Transport_Security="includeSubDomains")
    assert names == ["hsts_short_max_age"]


async def test_obsolete_x_frame_options_value() -> None:
    value = "ALLOW-FROM https://a.com"
    assert await _weak(X_Frame_Options=value) == ["x_frame_options_invalid"]


async def test_sameorigin_x_frame_options_is_fine() -> None:
    assert await _weak(X_Frame_Options="sameorigin") == []


async def test_wrong_x_content_type_options_value() -> None:
    assert await _weak(X_Content_Type_Options="sniff") == ["x_content_type_options_invalid"]


@pytest.mark.parametrize("value", ["unsafe-url", "no-referrer-when-downgrade"])
async def test_unsafe_referrer_policy(value: str) -> None:
    assert await _weak(Referrer_Policy=value) == ["referrer_policy_unsafe"]


async def test_referrer_policy_fallback_list_uses_last_value() -> None:
    """Trình duyệt dùng giá trị cuối cùng mà nó hiểu."""
    assert await _weak(Referrer_Policy="unsafe-url, strict-origin") == []
