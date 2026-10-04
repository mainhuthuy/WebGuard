"""ContentModule: dò username enumeration qua form đăng nhập (2 lượt POST, mật khẩu sai cố định)."""

from unittest.mock import patch

import httpx

from app.modules.content import ContentModule

URL = "https://example.com/account"
LOGIN_FORM = (
    '<form method="post" action="/login">'
    '<input type="hidden" name="csrf_token" value="tok123">'
    '<input type="text" name="username">'
    '<input type="password" name="password">'
    '</form>'
)


def _page(html: str) -> httpx.Response:
    return httpx.Response(
        200, text=html, headers={"content-type": "text/html"}, request=httpx.Request("GET", URL)
    )


def _resp(status: int = 200, text: str = "") -> httpx.Response:
    return httpx.Response(status, text=text, request=httpx.Request("POST", URL))


async def _scan(post_responses: list[httpx.Response | Exception], html: str = LOGIN_FORM) -> list[dict]:
    calls: list[dict] = []

    async def fake_get(self, target, **kwargs):  # type: ignore[no-untyped-def]
        return _page(html)

    async def fake_post(self, target, data=None, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(data or {})
        value = post_responses[len(calls) - 1]
        if isinstance(value, Exception):
            raise value
        return value

    with patch("httpx.AsyncClient.get", fake_get), patch("httpx.AsyncClient.post", fake_post):
        return await ContentModule().scan(URL)


def _names(findings: list[dict]) -> list[str]:
    return [f["name"] for f in findings]


async def test_identical_error_message_is_not_enumeration() -> None:
    same = _resp(200, "Invalid username or password.")
    assert await _scan([same, same]) == []


async def test_different_status_code_is_reported() -> None:
    findings = await _scan([_resp(200, "Invalid credentials"), _resp(401, "Invalid credentials")])
    assert [(f["name"], f["severity"]) for f in findings] == [("username_enumeration", "low")]
    assert findings[0]["url"] == "https://example.com/login"


async def test_differing_phrase_is_reported() -> None:
    findings = await _scan([
        _resp(200, "No account found with that username"),
        _resp(200, "Incorrect password"),
    ])
    assert _names(findings) == ["username_enumeration"]


async def test_differing_body_length_is_reported() -> None:
    short = _resp(200, "Login failed.")
    long = _resp(200, "Login failed. " + "Please check your details and try again. " * 5)
    findings = await _scan([short, long])
    assert _names(findings) == ["username_enumeration"]


async def test_hidden_fields_are_forwarded_to_both_requests() -> None:
    same = _resp(200, "Invalid username or password.")
    sent: list[dict] = []

    async def fake_get(self, target, **kwargs):  # type: ignore[no-untyped-def]
        return _page(LOGIN_FORM)

    async def fake_post(self, target, data=None, **kwargs):  # type: ignore[no-untyped-def]
        sent.append(data or {})
        return same

    with patch("httpx.AsyncClient.get", fake_get), patch("httpx.AsyncClient.post", fake_post):
        await ContentModule().scan(URL)

    assert [d["csrf_token"] for d in sent] == ["tok123", "tok123"]
    assert sent[0]["username"] != sent[1]["username"]
    assert sent[0]["password"] == sent[1]["password"]


async def test_get_method_login_form_is_skipped() -> None:
    """GET + 2 trường username/password, không có gì khác -> không có finding nào (CSRF field cũng vắng
    mặt nhưng method GET không bị tính vào kiểm tra 'form_without_csrf_token')."""
    html = '<form method="get" action="/login"><input name="username"><input type="password" name="password"></form>'
    assert await _scan([], html=html) == []


async def test_form_without_username_field_is_skipped() -> None:
    """Form chỉ có password (không có username) nên không được dò enumeration; vẫn có finding
    form_without_csrf_token (đúng, vì form POST thật sự thiếu token)."""
    html = '<form method="post" action="/login"><input type="password" name="password"></form>'
    assert _names(await _scan([], html=html)) == ["form_without_csrf_token"]


async def test_form_without_password_field_is_not_a_login_form() -> None:
    html = '<form method="post" action="/search"><input name="q"></form>'
    assert _names(await _scan([], html=html)) == ["form_without_csrf_token"]


async def test_network_error_during_probe_is_handled_gracefully() -> None:
    assert await _scan([httpx.ConnectError("refused")]) == []


async def test_only_the_first_login_form_is_probed() -> None:
    html = LOGIN_FORM + (
        '<form method="post" action="/login2">'
        '<input type="text" name="user"><input type="password" name="pass"></form>'
    )
    same = _resp(200, "Invalid username or password.")
    # Form thứ 2 không có CSRF token -> 1 finding form_without_csrf_token; không có username_enumeration
    # vì cả 2 lượt probe (chỉ nhắm form đầu tiên) trả về phản hồi giống hệt nhau.
    assert _names(await _scan([same, same], html=html)) == ["form_without_csrf_token"]
