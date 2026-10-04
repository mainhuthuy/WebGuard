"""CookiesModule: cookie đủ cờ nhưng cấu hình vẫn rủi ro."""

from unittest.mock import AsyncMock, patch

import httpx

from app.modules.cookies import CookiesModule

FLAGS = "; Secure; HttpOnly; SameSite=Lax"


async def _issues(cookie: str) -> list[str]:
    response = httpx.Response(
        200, headers={"Set-Cookie": cookie}, request=httpx.Request("GET", "https://e.com")
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response
        findings = await CookiesModule().scan("https://e.com")
    return sorted(f["flag_missing"] for f in findings)


async def test_healthy_cookie_has_no_issues() -> None:
    assert await _issues("sid=abc" + FLAGS) == []


async def test_samesite_none_is_reported() -> None:
    assert await _issues("a=1; Secure; HttpOnly; SameSite=None") == ["SameSite=None"]


async def test_secure_prefix_requires_secure() -> None:
    assert await _issues("__Secure-a=1; HttpOnly; SameSite=Lax") == [
        "Secure",
        "cookie_prefix_violation",
    ]


async def test_host_prefix_requires_path_root_and_no_domain() -> None:
    assert await _issues("__Host-a=1; Path=/app" + FLAGS) == ["cookie_prefix_violation"]
    assert await _issues("__Host-a=1; Path=/; Domain=e.com" + FLAGS) == ["cookie_prefix_violation"]
    assert await _issues("__Host-a=1; Path=/" + FLAGS) == []


async def test_session_cookie_with_domain_is_broad() -> None:
    assert await _issues("sessionid=1; Domain=e.com" + FLAGS) == ["cookie_broad_domain"]


async def test_non_session_cookie_with_domain_is_ignored() -> None:
    assert await _issues("theme=dark; Domain=e.com" + FLAGS) == []


async def test_long_lived_session_cookie_by_max_age() -> None:
    assert await _issues("token=1; Max-Age=31536000" + FLAGS) == ["cookie_long_lived"]


async def test_short_lived_session_cookie_is_fine() -> None:
    assert await _issues("token=1; Max-Age=3600" + FLAGS) == []


async def test_long_lived_session_cookie_by_expires() -> None:
    expires = "Wed, 01 Jan 2099 00:00:00 GMT"
    assert await _issues(f"auth=1; Expires={expires}" + FLAGS) == ["cookie_long_lived"]


async def test_invalid_expiry_is_ignored() -> None:
    assert await _issues("auth=1; Expires=not-a-date; Max-Age=abc" + FLAGS) == []
