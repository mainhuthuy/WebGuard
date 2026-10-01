"""Danh mục kiểm tra hiển thị ở trang About (frontend) phải khớp với các module quét thật.

Nếu thêm/đổi/xóa một kiểm tra hoặc mức độ rủi ro trong `app/modules/*`, test này nhắc cập nhật
`frontend/src/pages/aboutChecks.ts`.
"""

from pathlib import Path
import re

import pytest

from app.modules.cookies import CookiesModule
from app.modules.headers import HeadersModule
from app.modules.information import InformationModule

CATALOG = Path(__file__).resolve().parents[3] / "frontend" / "src" / "pages" / "aboutChecks.ts"

# Các kiểm tra mà severity nằm trực tiếp trong mã của module (không phải bảng dữ liệu)
SSL_TLS_CHECKS = {
    "ssl_connection_failed": "critical",
    "cert_expired": "critical",
    "outdated_tls_version": "high",
    "cert_expiring_soon": "medium",
}
CORS_CHECKS = {
    "cors_origin_reflection": "critical",
    "cors_credentials_exposed": "critical",
    "cors_wildcard": "high",
}
INFORMATION_HEADER_CHECKS = {"Server header": "medium", "X-Powered-By header": "medium"}


def _documented() -> dict[str, str]:
    """Đọc cặp (name -> severity) từ file TypeScript của trang About."""
    text = CATALOG.read_text(encoding="utf-8")
    pairs = re.findall(r"name:\s*'([^']+)',\s*severity:\s*'(\w+)'", text)
    return {re.sub(r"\s*\(HSTS\)$", "", name): severity for name, severity in pairs}


@pytest.fixture(scope="module")
def documented() -> dict[str, str]:
    if not CATALOG.exists():
        pytest.skip("không có thư mục frontend (backend chạy riêng)")
    return _documented()


def _expected() -> dict[str, str]:
    expected: dict[str, str] = {}
    expected.update({h["name"]: h["severity"] for h in HeadersModule.SECURITY_HEADERS})
    expected.update({f["name"]: f["severity"] for f in CookiesModule.COOKIE_FLAGS})
    expected.update({p["path"]: p["severity"] for p in InformationModule.SENSITIVE_PATHS})
    expected.update(INFORMATION_HEADER_CHECKS)
    expected.update(SSL_TLS_CHECKS)
    expected.update(CORS_CHECKS)
    return expected


def test_every_check_is_documented_with_the_right_severity(documented: dict[str, str]) -> None:
    expected = _expected()
    missing = sorted(set(expected) - set(documented))
    assert not missing, f"Thiếu trong trang About: {missing}"
    wrong = {n: (documented[n], s) for n, s in expected.items() if documented[n] != s}
    assert not wrong, f"Sai mức độ rủi ro (About, backend): {wrong}"


def test_about_page_documents_nothing_the_scanner_does_not_check(documented: dict[str, str]) -> None:
    extra = sorted(set(documented) - set(_expected()))
    assert not extra, f"Trang About nhắc tới kiểm tra không tồn tại: {extra}"
