"""ContentModule: phân tích tĩnh HTML trang chủ (mock httpx)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.modules.content import ContentModule

HTTPS = "https://example.com/"
HTTP = "http://example.com/"


async def _scan(html: str, url: str = HTTPS, content_type: str = "text/html; charset=utf-8") -> list[dict]:
    response = httpx.Response(
        200, text=html, headers={"content-type": content_type}, request=httpx.Request("GET", url)
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response
        return await ContentModule().scan(url)


def _pairs(findings: list[dict]) -> list[tuple[str, str]]:
    return sorted((f["name"], f["severity"]) for f in findings)


async def test_clean_page_has_no_findings() -> None:
    html = (
        '<html><head><script src="/app.js"></script><link rel="stylesheet" href="/a.css"></head>'
        '<body><img src="/logo.png"><form method="post" action="/login">'
        '<input type="hidden" name="csrf_token" value="x"><input type="password" name="p"></form></body></html>'
    )
    assert await _scan(html) == []


async def test_non_html_response_is_skipped() -> None:
    assert await _scan('{"a": "<script src=http://x/a.js>"}', content_type="application/json") == []


async def test_active_mixed_content_is_high() -> None:
    html = '<script src="http://cdn.example.com/a.js"></script>'
    assert ("mixed_content_active", "high") in _pairs(await _scan(html))


async def test_iframe_and_stylesheet_over_http_are_active_mixed_content() -> None:
    html = '<iframe src="http://x.com/f"></iframe>'
    assert _pairs(await _scan(html)) == [("mixed_content_active", "high")]
    html = '<link rel="stylesheet" href="http://example.com/a.css">'
    assert _pairs(await _scan(html)) == [("mixed_content_active", "high")]


async def test_passive_mixed_content_is_low() -> None:
    assert _pairs(await _scan('<img src="http://example.com/a.png">')) == [("mixed_content_passive", "low")]


async def test_mixed_content_is_not_checked_on_http_pages() -> None:
    assert await _scan('<img src="http://example.com/a.png">', url=HTTP) == []


async def test_third_party_script_without_integrity_is_flagged_once() -> None:
    html = (
        '<script src="https://cdn.other.com/a.js"></script>'
        '<link rel="stylesheet" href="https://cdn.other.com/a.css">'
    )
    findings = await _scan(html)
    assert _pairs(findings) == [("missing_sri", "medium")]
    assert "cdn.other.com" in findings[0]["description"]


async def test_third_party_script_with_integrity_is_fine() -> None:
    html = '<script src="https://cdn.other.com/a.js" integrity="sha384-abc" crossorigin></script>'
    assert await _scan(html) == []


async def test_first_party_and_subdomain_scripts_need_no_sri() -> None:
    html = (
        '<script src="https://example.com/a.js"></script>'
        '<script src="https://static.example.com/b.js"></script>'
    )
    assert await _scan(html) == []


async def test_password_form_on_http_page_is_critical() -> None:
    html = '<form action="/login" method="post"><input type="password" name="p"></form>'
    assert ("password_form_http", "critical") in _pairs(await _scan(html, url=HTTP))


async def test_form_posting_to_http_from_https_page() -> None:
    html = '<form action="http://example.com/login" method="get"><input name="q"></form>'
    findings = await _scan(html)
    assert _pairs(findings) == [("insecure_form_action", "high")]
    assert findings[0]["url"] == "http://example.com/login"


async def test_post_form_without_csrf_token_is_low() -> None:
    html = '<form method="POST" action="/save"><input name="title"></form>'
    assert _pairs(await _scan(html)) == [("form_without_csrf_token", "low")]


async def test_get_form_needs_no_csrf_token() -> None:
    assert await _scan('<form action="/search"><input name="q"></form>') == []


@pytest.mark.parametrize(
    ("src", "label"),
    [
        ("/js/jquery-1.12.4.min.js", "jQuery 1.12.4"),
        ("https://code.jquery.com/jquery-3.4.1.min.js", "jQuery 3.4.1"),
        ("/vendor/bootstrap/3.3.7/js/bootstrap.min.js", "Bootstrap 3.3.7"),
        ("/lib/angular.js@1.6.9/angular.min.js", "AngularJS 1.6.9"),
        ("/lodash-4.17.15.min.js", "Lodash 4.17.15"),
        ("/moment-2.20.0.js", "Moment.js 2.20.0"),
    ],
)
async def test_vulnerable_library_versions_are_flagged(src: str, label: str) -> None:
    findings = await _scan(f'<script src="{src}" integrity="sha384-x"></script>')
    assert [(f["name"], f["severity"]) for f in findings] == [("outdated_js_library", "medium")]
    assert label in findings[0]["description"]


@pytest.mark.parametrize(
    "src", ["/jquery-3.7.1.min.js", "/jquery-3.5.0.js", "/bootstrap-5.3.0.js", "/lodash-4.17.21.js"]
)
async def test_patched_library_versions_are_fine(src: str) -> None:
    assert await _scan(f'<script src="{src}"></script>') == []


async def test_same_library_is_reported_once_per_version() -> None:
    html = '<script src="/jquery-1.9.1.js"></script><script src="/js/jquery-1.9.1.min.js"></script>'
    assert len(await _scan(html)) == 1


async def test_generator_with_version_is_low() -> None:
    html = '<meta name="generator" content="WordPress 5.8.1">'
    assert _pairs(await _scan(html)) == [("generator_version_disclosure", "low")]


async def test_generator_without_version_is_ignored() -> None:
    assert await _scan('<meta name="generator" content="Hugo">') == []


async def test_malformed_html_does_not_crash() -> None:
    assert isinstance(await _scan("<html><script src=<<<>>> <form <input"), list)
