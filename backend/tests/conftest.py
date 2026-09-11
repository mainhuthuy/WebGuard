import httpx
import pytest

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
    """Giả lập Response từ một website cấu hình ĐẦY ĐỦ 9 header bảo mật."""
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
