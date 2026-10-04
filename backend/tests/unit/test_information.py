"""Unit tests cho InformationModule (mock httpx)."""

from unittest.mock import patch

import httpx
import pytest

from app.modules.information import InformationModule

BASE = "https://example.com"


def _resp(status: int, **headers: str) -> httpx.Response:
    return httpx.Response(status, headers=headers, request=httpx.Request("GET", BASE))


def _fake_get(routes: dict[str, httpx.Response]):
    """Hàm giả cho AsyncClient.get: trả response theo đường dẫn, mặc định 404."""

    async def fake_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        path = url[len(BASE):] or "/"
        return routes.get(path, httpx.Response(404, request=httpx.Request("GET", url)))

    return fake_get


async def _scan(routes: dict[str, httpx.Response]) -> list[dict]:
    with patch("httpx.AsyncClient.get", _fake_get(routes)):
        return await InformationModule().scan(BASE)


async def test_clean_site_has_no_findings() -> None:
    assert await _scan({}) == []


async def test_exposed_env_file_is_critical() -> None:
    findings = await _scan({"/.env": _resp(200)})
    assert [(f["name"], f["severity"]) for f in findings] == [("/.env", "critical")]


async def test_wp_admin_returning_200_is_detected() -> None:
    findings = await _scan({"/wp-admin": _resp(200)})
    assert [f["name"] for f in findings] == ["/wp-admin"]


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
async def test_wp_admin_redirecting_to_wordpress_login_is_detected(status: int) -> None:
    """WordPress thật thường chuyển /wp-admin sang wp-login.php thay vì trả 200."""
    redirect = _resp(status, location="https://example.com/wp-login.php?redirect_to=%2Fwp-admin%2F")
    findings = await _scan({"/wp-admin": redirect})
    assert [f["name"] for f in findings] == ["/wp-admin"]


async def test_wp_admin_trailing_slash_redirect_is_detected() -> None:
    findings = await _scan({"/wp-admin": _resp(301, location="https://example.com/wp-admin/")})
    assert [f["name"] for f in findings] == ["/wp-admin"]


async def test_unrelated_redirect_is_not_a_finding() -> None:
    """Site chuyển mọi đường dẫn lạ về trang chủ không phải WordPress."""
    findings = await _scan({"/wp-admin": _resp(302, location="https://example.com/")})
    assert findings == []


async def test_redirect_on_other_paths_is_not_treated_as_exposure() -> None:
    """Chỉ /wp-admin có luật redirect; /.env chuyển hướng vẫn không phải lộ file."""
    findings = await _scan({"/.env": _resp(302, location="https://example.com/wp-login.php")})
    assert findings == []


async def test_non_redirect_status_with_a_location_header_is_ignored() -> None:
    findings = await _scan({"/wp-admin": _resp(404, location="https://example.com/wp-login.php")})
    assert findings == []


async def test_server_and_powered_by_headers_are_reported() -> None:
    findings = await _scan({"/": _resp(200, **{"server": "nginx/1.18.0", "x-powered-by": "PHP/7.4"})})
    assert sorted(f["name"] for f in findings) == ["Server header", "X-Powered-By header"]


async def test_network_errors_on_one_path_do_not_hide_other_findings() -> None:
    calls: list[str] = []

    async def flaky_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(url)
        if url.endswith("/.env"):
            raise httpx.ConnectTimeout("slow")
        if url.endswith("/robots.txt"):
            return _resp(200)
        return httpx.Response(404, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", flaky_get):
        findings = await InformationModule().scan(BASE)
    assert [f["name"] for f in findings] == ["/robots.txt"]
    assert len(calls) >= 4  # vẫn tiếp tục kiểm tra các đường dẫn còn lại
