"""Unit tests cho SSLTLSModule (không mở kết nối mạng thật)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.modules import ssl_tls
from app.modules.ssl_tls import SSLTLSModule


def _cert_expiring_in(days: int) -> dict[str, Any]:
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    return {"notAfter": expire.strftime("%b %d %H:%M:%S %Y GMT")}


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, cert: dict[str, Any], version: str) -> None:
    monkeypatch.setattr(ssl_tls, "_fetch_certificate", lambda host, port: (cert, version))


async def test_healthy_certificate_has_no_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, _cert_expiring_in(200), "TLSv1.3")
    assert await SSLTLSModule().scan("https://example.com") == []


async def test_expired_certificate_is_critical(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, _cert_expiring_in(-5), "TLSv1.3")
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["cert_expired"]
    assert findings[0]["severity"] == "critical"


async def test_expiring_soon_is_medium(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, _cert_expiring_in(10), "TLSv1.2")
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["cert_expiring_soon"]


async def test_outdated_tls_version_is_high(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, _cert_expiring_in(200), "TLSv1")
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["outdated_tls_version"]
    assert findings[0]["severity"] == "high"


async def test_connection_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(host: str, port: int) -> Any:
        raise OSError("connection refused")

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", boom)
    findings = await SSLTLSModule().scan("https://example.com")
    assert findings[0]["name"] == "ssl_connection_failed"
    assert "connection refused" in findings[0]["description"]


async def test_uses_port_from_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, int]] = []

    def fetch(host: str, port: int) -> tuple[dict[str, Any], str]:
        seen.append((host, port))
        return _cert_expiring_in(200), "TLSv1.3"

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", fetch)
    await SSLTLSModule().scan("https://example.com:8443/path")
    assert seen == [("example.com", 8443)]
