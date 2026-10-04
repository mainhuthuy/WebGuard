"""CorsModule: origin null và kiểm tra whitelist origin yếu."""

from unittest.mock import patch

import httpx

from app.modules.cors import CorsModule

URL = "https://example.com"


async def _scan(trusted) -> list[str]:  # type: ignore[no-untyped-def]
    """`trusted(origin) -> bool`: server phản hồi origin nào thì coi là tin cậy."""

    async def fake_get(self, url, headers=None, **kwargs):  # type: ignore[no-untyped-def]
        origin = (headers or {}).get("Origin")
        response_headers = {}
        if origin and trusted(origin):
            response_headers["access-control-allow-origin"] = origin
        return httpx.Response(200, headers=response_headers, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", fake_get):
        findings = await CorsModule().scan(URL)
    return [f["name"] for f in findings]


async def test_strict_whitelist_has_no_findings() -> None:
    assert await _scan(lambda o: o == "https://app.example.com") == []


async def test_null_origin_is_reported() -> None:
    assert await _scan(lambda o: o == "null") == ["cors_null_origin"]


async def test_suffix_attack_origin_is_reported() -> None:
    """Server dùng startswith: https://example.com.evil.com được chấp nhận."""
    assert await _scan(lambda o: o.startswith("https://example.com")) == [
        "cors_weak_origin_validation"
    ]


async def test_prefix_attack_origin_is_reported() -> None:
    """Server dùng endswith: https://evilexample.com được chấp nhận."""
    assert await _scan(lambda o: o.endswith("example.com")) == ["cors_weak_origin_validation"]


async def test_reflecting_everything_is_not_reported_twice() -> None:
    names = await _scan(lambda o: True)
    assert "cors_origin_reflection" in names
    assert "cors_weak_origin_validation" not in names
    assert "cors_null_origin" in names
