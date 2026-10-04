"""SSLTLSModule: phân loại lỗi chứng chỉ, bộ mã hóa yếu, thiếu TLS 1.3."""

import ssl
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.modules import ssl_tls
from app.modules.ssl_tls import SSLTLSModule


@pytest.fixture(autouse=True)
def _no_real_legacy_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssl_tls, "_probe_legacy_tls", lambda host, port: [])


def _good_cert() -> dict[str, Any]:
    expire = datetime.now(UTC) + timedelta(days=200)
    return {"notAfter": expire.strftime("%b %d %H:%M:%S %Y GMT")}


def _cert_error(code: int | None, message: str) -> ssl.SSLCertVerificationError:
    error = ssl.SSLCertVerificationError(message)
    error.verify_code = code  # type: ignore[attr-defined]
    error.verify_message = message  # type: ignore[attr-defined]
    return error


@pytest.mark.parametrize(
    ("code", "message", "expected"),
    [
        (10, "certificate has expired", "cert_expired"),
        (62, "Hostname mismatch, certificate is not valid for 'example.com'.", "cert_hostname_mismatch"),
        (18, "self-signed certificate", "cert_self_signed"),
        (19, "self-signed certificate in certificate chain", "cert_self_signed"),
        (20, "unable to get local issuer certificate", "cert_untrusted_chain"),
        (21, "unable to verify the first certificate", "cert_untrusted_chain"),
    ],
)
async def test_certificate_verification_errors_are_classified(
    monkeypatch: pytest.MonkeyPatch, code: int, message: str, expected: str
) -> None:
    def fail(host: str, port: int) -> Any:
        raise _cert_error(code, message)

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", fail)
    findings = await SSLTLSModule().scan("https://example.com")
    assert [(f["name"], f["severity"]) for f in findings] == [(expected, "critical")]


async def test_unrecognised_certificate_error_stays_generic(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(host: str, port: int) -> Any:
        raise _cert_error(7, "certificate signature failure")

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", fail)
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["ssl_connection_failed"]


async def test_weak_ciphers_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssl_tls, "_fetch_certificate", lambda h, p: (_good_cert(), "TLSv1.3"))
    monkeypatch.setattr(ssl_tls, "_probe_weak_ciphers", lambda h, p: ["RC4", "3DES"])
    findings = await SSLTLSModule().scan("https://example.com")
    assert [(f["name"], f["severity"]) for f in findings] == [("weak_cipher_suite", "high")]
    assert "RC4, 3DES" in findings[0]["description"]


async def test_missing_tls13_is_low(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssl_tls, "_fetch_certificate", lambda h, p: (_good_cert(), "TLSv1.2"))
    findings = await SSLTLSModule().scan("https://example.com")
    assert [(f["name"], f["severity"]) for f in findings] == [("tls13_unsupported", "low")]


async def test_tls13_server_has_no_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssl_tls, "_fetch_certificate", lambda h, p: (_good_cert(), "TLSv1.3"))
    assert await SSLTLSModule().scan("https://example.com") == []


def test_weak_cipher_probe_finds_nothing_when_the_port_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    monkeypatch.undo()  # bỏ các bản giả autouse để chạy hàm thật
    assert ssl_tls._probe_weak_ciphers("127.0.0.1", port) == []
