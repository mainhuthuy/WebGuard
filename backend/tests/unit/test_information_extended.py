"""InformationModule: các đường dẫn nhạy cảm mới, chữ ký nội dung, catch-all, lỗi chi tiết."""

from unittest.mock import patch

import httpx
import pytest

from app.modules.information import InformationModule

BASE = "https://example.com"


def _resp(status: int = 200, body: bytes | str = b"", **headers: str) -> httpx.Response:
    content = body.encode() if isinstance(body, str) else body
    return httpx.Response(
        status, content=content, headers=headers, request=httpx.Request("GET", BASE)
    )


async def _scan(routes: dict[str, httpx.Response], default: httpx.Response | None = None) -> list[dict]:
    async def fake_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        path = url[len(BASE):] or "/"
        if path in routes:
            return routes[path]
        return default if default is not None else httpx.Response(404, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", fake_get):
        return await InformationModule().scan(BASE)


def _names(findings: list[dict]) -> list[str]:
    return sorted(f["name"] for f in findings)


@pytest.mark.parametrize(
    ("path", "body", "severity"),
    [
        ("/.git/config", "[core]\n\trepositoryformatversion = 0", "critical"),
        ("/.aws/credentials", "[default]\naws_access_key_id = AKIA", "critical"),
        ("/id_rsa", "-----BEGIN OPENSSH PRIVATE KEY-----", "critical"),
        ("/.htpasswd", "admin:$apr1$abc$hash", "critical"),
        ("/wp-config.php.bak", "define('DB_PASSWORD', 'x');", "critical"),
        ("/backup.sql", "-- MySQL dump 10.13\nCREATE TABLE users", "critical"),
        ("/backup.zip", b"PK\x03\x04binary", "critical"),
        ("/console", "<title>Console // Werkzeug Debugger</title>", "critical"),
        ("/actuator/env", '{"activeProfiles":[],"propertySources":[]}', "high"),
        ("/docker-compose.yml", "version: '3'\nservices:\n  db:", "high"),
        ("/phpinfo.php", "<title>phpinfo()</title>", "medium"),
        ("/server-status", "<title>Apache Server Status for x</title>", "medium"),
        ("/phpmyadmin/", "<title>phpMyAdmin</title>", "medium"),
        ("/.DS_Store", b"\x00\x00\x00\x01Bud1\x00", "medium"),
        ("/wp-json/wp/v2/users", '[{"id":1,"slug":"admin"}]', "medium"),
        ("/xmlrpc.php", "XML-RPC server accepts POST requests only.", "medium"),
        ("/package.json", '{"dependencies": {}}', "low"),
        ("/openapi.json", '{"openapi": "3.0.0"}', "low"),
    ],
)
async def test_exposed_path_with_matching_content_is_reported(
    path: str, body: bytes | str, severity: str
) -> None:
    findings = await _scan({path: _resp(200, body)})
    assert [(f["name"], f["severity"]) for f in findings] == [(path, severity)]


async def test_partial_content_206_counts_as_exposed() -> None:
    findings = await _scan({"/backup.sql": _resp(206, "CREATE TABLE a (id int)")})
    assert _names(findings) == ["/backup.sql"]


async def test_path_with_wrong_content_is_not_reported() -> None:
    """Có trả 200 nhưng nội dung không phải file thật (vd: trang HTML) → không báo."""
    html = "<html><body>Welcome</body></html>"
    assert await _scan({"/.git/config": _resp(200, html), "/id_rsa": _resp(200, html)}) == []


async def test_catch_all_site_does_not_flood_with_false_positives() -> None:
    """Site trả 200 + cùng một trang cho mọi URL (SPA): chỉ file khớp chữ ký mới được tính."""
    spa = _resp(200, "<html><div id='root'></div></html>")
    assert await _scan({}, default=spa) == []


async def test_catch_all_site_still_reports_a_real_leak() -> None:
    spa = _resp(200, "<html><div id='root'></div></html>")
    findings = await _scan({"/.git/config": _resp(200, "[core]\nbare = false")}, default=spa)
    assert _names(findings) == ["/.git/config"]


async def test_catch_all_skips_checks_without_a_signature() -> None:
    """/.env không có chữ ký: trên site catch-all, 200 không đủ bằng chứng."""
    spa = _resp(200, "<html></html>")
    assert await _scan({"/.env": _resp(200, "<html></html>")}, default=spa) == []


async def test_directory_listing_on_a_common_folder() -> None:
    listing = _resp(200, "<html><title>Index of /uploads</title></html>")
    findings = await _scan({"/uploads/": listing})
    assert [(f["name"], f["severity"], f["url"]) for f in findings] == [
        ("directory_listing", "medium", f"{BASE}/uploads/")
    ]


async def test_directory_listing_on_homepage() -> None:
    findings = await _scan({"/": _resp(200, "<title>Index of /</title>")})
    assert _names(findings) == ["directory_listing"]


@pytest.mark.parametrize(
    "error",
    [
        "Traceback (most recent call last):\n  File app.py",
        "You have an error in your SQL syntax; check the manual",
        "Warning: mysql_connect() in /var/www/a.php on line 12",
        "Server Error in '/' Application.",
        "ORA-00933: SQL command not properly ended",
    ],
)
async def test_verbose_error_messages_are_reported(error: str) -> None:
    probe = httpx.Response(500, content=error.encode(), request=httpx.Request("GET", BASE))

    async def fake_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        if "/webguard-" in url:
            return probe
        return httpx.Response(404, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", fake_get):
        findings = await InformationModule().scan(BASE)
    assert _names(findings) == ["verbose_error_messages"]
    assert findings[0]["severity"] == "medium"


async def test_plain_404_page_is_not_an_error_leak() -> None:
    assert await _scan({}, default=_resp(404, "Not Found")) == []


async def test_extra_version_headers_are_reported() -> None:
    headers = {"x-aspnet-version": "4.0.30319", "x-aspnetmvc-version": "5.2", "x-generator": "Drupal 9"}
    findings = await _scan({"/": _resp(200, **headers)})
    assert _names(findings) == ["X-AspNet-Version header", "X-AspNetMvc-Version header", "X-Generator header"]
    assert {f["name"]: f["severity"] for f in findings}["X-Generator header"] == "low"


@pytest.mark.parametrize("ip", ["10.0.0.5", "192.168.1.20", "172.16.4.9", "172.31.255.1"])
async def test_internal_ip_in_html_is_reported(ip: str) -> None:
    findings = await _scan({"/": _resp(200, f"<!-- backend at {ip} -->")})
    assert _names(findings) == ["internal_ip_disclosure"]


@pytest.mark.parametrize("ip", ["8.8.8.8", "172.32.0.1", "11.0.0.1"])
async def test_public_ip_in_html_is_ignored(ip: str) -> None:
    assert await _scan({"/": _resp(200, f"server {ip}")}) == []


async def test_all_requests_ask_for_a_byte_range() -> None:
    """Xin Range để không phải tải toàn bộ file backup nặng."""
    seen: list[dict] = []

    async def fake_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs)
        return httpx.Response(404, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", fake_get):
        await InformationModule().scan(BASE)
    assert any(k.get("headers", {}).get("Range", "").startswith("bytes=0-") for k in seen)
