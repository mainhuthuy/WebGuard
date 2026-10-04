"""Cookie flags được so khớp theo TÊN THUỘC TÍNH, không phải chuỗi con trong cả dòng Set-Cookie."""

from unittest.mock import AsyncMock, patch

import httpx

from app.modules.cookies import CookiesModule


def _response(cookie: str) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        headers={"Set-Cookie": cookie},
        request=httpx.Request("GET", "https://example.com"),
    )


async def _scan(cookie: str) -> list[dict]:
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _response(cookie)
        return await CookiesModule().scan("https://example.com")


async def _missing(cookie: str) -> list[str]:
    return sorted(f["flag_missing"] for f in await _scan(cookie))


async def test_cookie_name_containing_a_flag_word_is_not_mistaken_for_the_flag() -> None:
    """Tên cookie chứa chữ 'secure' không được coi là đã có cờ Secure."""
    assert await _missing("session_secure=1; HttpOnly; SameSite=Lax") == ["Secure"]


async def test_cookie_value_containing_flag_words_is_not_mistaken_for_flags() -> None:
    assert await _missing("id=samesite_httponly; Path=/") == ["HttpOnly", "SameSite", "Secure"]


async def test_unrelated_attribute_value_containing_a_flag_word_is_ignored() -> None:
    assert await _missing("a=1; Comment=samesite; HttpOnly; Secure") == ["SameSite"]


async def test_flag_matching_ignores_case_and_attribute_values() -> None:
    assert await _missing("a=1; SECURE; httponly; samesite=LAX") == []


async def test_cookie_name_is_reported_without_its_value() -> None:
    findings = await _scan("theme=dark; Path=/")
    assert {f["name"] for f in findings} == {"theme"}


async def test_whitespace_around_attributes_is_tolerated() -> None:
    assert await _missing("a=1;Secure ;  HttpOnly;SameSite=Strict") == []
