import os
import tempfile

import httpx
import pytest

# Cô lập database: mọi test dùng file SQLite tạm, không đụng tới webguard.db của môi trường dev.
# Phải đặt TRƯỚC khi import bất kỳ module `app.*` nào (vd `app.db.session`), vì engine được tạo
# ngay khi module đó được import. httpx/pytest ở trên an toàn vì không kéo theo `app.*`.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="webguard_tests_")
os.environ["WEBGUARD_DB_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"


@pytest.fixture(scope="session", autouse=True)
def _init_test_database():
    """Tạo schema cho database test một lần trước toàn bộ session."""
    from app.db.session import init_db

    init_db()

@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra SSRF mặc định thấy mọi hostname là IP public (không phụ thuộc mạng).

    Chỉ giả lập bước phân giải của app.core.security, không đụng tới DNS của httpx.
    Test cần DNS khác thì tự monkeypatch lại `app.core.security._resolve`.
    """
    from app.core import security

    async def fake_resolve(hostname: str) -> list[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr(security, "_resolve", fake_resolve)


@pytest.fixture(autouse=True)
def _no_real_weak_cipher_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Không dò bộ mã hóa yếu qua mạng thật; test cần thì tự thay `_probe_weak_ciphers`."""
    from app.modules import ssl_tls

    monkeypatch.setattr(ssl_tls, "_probe_weak_ciphers", lambda host, port: [])


@pytest.fixture
def mock_insecure_headers_response():
    """Giả lập Response từ một website KHÔNG cấu hình bất kỳ header bảo mật nào."""
    return httpx.Response(
        status_code=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        request=httpx.Request("GET", "https://insecure-example.com")
    )

@pytest.fixture
def mock_secure_headers_response():
    """Giả lập Response từ một website cấu hình ĐẦY ĐỦ 10 header bảo mật."""
    headers = {
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
    return httpx.Response(
        status_code=200,
        headers=headers,
        request=httpx.Request("GET", "https://secure-example.com")
    )

@pytest.fixture
def mock_insecure_cookie_response():
    """Giả lập Response có cookie thiếu toàn bộ cờ bảo mật."""
    return httpx.Response(
        status_code=200,
        headers={"Set-Cookie": "session_token=abc123xyz"},
        request=httpx.Request("GET", "https://example.com")
    )

@pytest.fixture
def mock_secure_cookie_response():
    """Giả lập Response có cookie đầy đủ cờ HttpOnly, Secure, SameSite."""
    return httpx.Response(
        status_code=200,
        headers={"Set-Cookie": "session_token=abc123xyz; HttpOnly; Secure; SameSite=Strict"},
        request=httpx.Request("GET", "https://example.com")
    )

@pytest.fixture
def sample_findings():
    """Bộ findings mẫu để test ScoringEngine."""
    return [
        {"module": "CORS", "name": "cors_reflection", "severity": "critical", "description": "test", "remediation": "test"},
        {"module": "headers", "name": "csp", "severity": "high", "description": "test", "remediation": "test"},
        {"module": "headers", "name": "x-frame-options", "severity": "medium", "description": "test", "remediation": "test"},
        {"module": "headers", "name": "x-xss", "severity": "low", "description": "test", "remediation": "test"},
    ]
