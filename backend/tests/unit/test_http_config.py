"""HttpConfigModule: ép HTTPS, TRACE, method nguy hiểm, security.txt (mock httpx)."""

from unittest.mock import patch

import httpx

from app.modules.http_config import HttpConfigModule

URL = "https://example.com/app"
GOOD_SECURITY_TXT = httpx.Response(200, text="Contact: mailto:sec@example.com\nExpires: 2099-01-01T00:00:00Z")


def _r(status: int = 200, text: str = "", **headers: str) -> httpx.Response:
    return httpx.Response(status, text=text, headers=headers, request=httpx.Request("GET", URL))


async def _scan(
    *,
    http: httpx.Response | Exception | None = None,
    trace: httpx.Response | Exception | None = None,
    options: httpx.Response | Exception | None = None,
    security_txt: httpx.Response | Exception | None = None,
    redirect_param: str | None = None,
    redirect_location: str = "https://webguard-redirect-check.invalid/",
    url: str = URL,
) -> list[dict]:
    http = http if http is not None else _r(301, location="https://example.com/")
    trace = trace if trace is not None else _r(405)
    options = options if options is not None else _r(200, allow="GET, HEAD, POST")
    security_txt = security_txt if security_txt is not None else GOOD_SECURITY_TXT
    def pick(value: httpx.Response | Exception) -> httpx.Response:
        if isinstance(value, Exception):
            raise value
        return value

    async def fake_get(self, target, **kwargs):  # type: ignore[no-untyped-def]
        if target.endswith("/.well-known/security.txt"):
            return pick(security_txt)
        if redirect_param and f"{redirect_param}=" in target and "webguard-redirect-check.invalid" in target:
            return _r(302, location=redirect_location)
        return pick(http)

    async def fake_request(self, method, target, **kwargs):  # type: ignore[no-untyped-def]
        return pick(trace if method == "TRACE" else options)

    with (
        patch("httpx.AsyncClient.get", fake_get),
        patch("httpx.AsyncClient.request", fake_request),
    ):
        findings = await HttpConfigModule().scan(url)
    return findings


def _names(findings: list[dict]) -> list[str]:
    return [f["name"] for f in findings]


async def test_well_configured_site_has_no_findings() -> None:
    assert await _scan() == []


async def test_http_served_without_redirect_is_high() -> None:
    findings = await _scan(http=_r(200, "<html>hi</html>"))
    assert [(f["name"], f["severity"]) for f in findings] == [("https_not_enforced", "high")]
    assert findings[0]["url"] == "http://example.com/"


async def test_redirect_to_another_http_url_is_not_enforcement() -> None:
    assert _names(await _scan(http=_r(302, location="http://example.com/login"))) == ["https_not_enforced"]


async def test_relative_redirect_stays_on_http() -> None:
    assert _names(await _scan(http=_r(301, location="/home"))) == ["https_not_enforced"]


async def test_closed_port_80_is_fine() -> None:
    assert await _scan(http=httpx.ConnectError("refused")) == []


async def test_http_error_status_is_not_reported() -> None:
    assert await _scan(http=_r(403)) == []


async def test_http_target_is_probed_on_its_own_port() -> None:
    findings = await _scan(http=_r(200), url="http://example.com:8080/x")
    assert findings[0]["url"] == "http://example.com:8080/"


async def test_trace_enabled_is_reported() -> None:
    findings = await _scan(trace=_r(200, "TRACE / HTTP/1.1\r\nHost: example.com"))
    assert [(f["name"], f["severity"]) for f in findings] == [("http_trace_enabled", "medium")]


async def test_trace_200_without_echo_is_ignored() -> None:
    assert await _scan(trace=_r(200, "<html>home</html>")) == []


async def test_risky_methods_advertised_by_options() -> None:
    findings = await _scan(options=_r(200, allow="GET, PUT, delete, POST"))
    assert _names(findings) == ["risky_http_methods"]
    assert "PUT, DELETE" in findings[0]["description"]


async def test_missing_security_txt_is_low() -> None:
    findings = await _scan(security_txt=_r(404))
    assert [(f["name"], f["severity"]) for f in findings] == [("security_txt_missing", "low")]
    assert findings[0]["url"] == "https://example.com/.well-known/security.txt"


async def test_catch_all_html_is_not_a_security_txt() -> None:
    """Site trả 200 + trang HTML cho mọi URL: không có Contact thì vẫn là thiếu."""
    assert _names(await _scan(security_txt=_r(200, "<html>app</html>"))) == ["security_txt_missing"]


async def test_network_errors_never_crash_the_module() -> None:
    boom = httpx.ConnectTimeout("slow")
    assert await _scan(http=boom, trace=boom, options=boom, security_txt=boom) == []


async def test_open_redirect_via_common_param_is_reported() -> None:
    findings = await _scan(redirect_param="next")
    assert [(f["name"], f["severity"]) for f in findings] == [("open_redirect", "medium")]
    assert "next" in findings[0]["description"]


async def test_open_redirect_checks_an_unusual_param_name_too() -> None:
    findings = await _scan(redirect_param="returnto")
    assert _names(findings) == ["open_redirect"]


async def test_redirect_to_a_bot_check_page_that_echoes_the_url_is_not_an_open_redirect() -> None:
    """Regression: google.com/sorry/index?continue=<URL ta gửi> chứa marker nhưng đích là google.com."""
    echoed = "https://www.google.com/sorry/index?continue=https://example.com/%3Fnext%3Dhttps%253A%252F%252Fwebguard-redirect-check.invalid%252F"
    findings = await _scan(redirect_param="next", redirect_location=echoed)
    assert "open_redirect" not in _names(findings)


async def test_protocol_relative_redirect_to_the_marker_host_is_reported() -> None:
    findings = await _scan(redirect_param="next", redirect_location="//webguard-redirect-check.invalid/x")
    assert _names(findings) == ["open_redirect"]
