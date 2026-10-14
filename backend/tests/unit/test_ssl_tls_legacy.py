"""Unit tests cho việc phát hiện giao thức TLS cũ (1.0 / 1.1) của SSLTLSModule."""

import shutil
import socket
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.modules import ssl_tls
from app.modules.ssl_tls import SSLTLSModule


def _good_cert() -> dict[str, Any]:
    expire = datetime.now(UTC) + timedelta(days=200)
    return {"notAfter": expire.strftime("%b %d %H:%M:%S %Y GMT")}


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.setattr(ssl_tls, "_fetch_certificate", lambda host, port: (_good_cert(), version))


def _patch_probe(monkeypatch: pytest.MonkeyPatch, versions: list[str]) -> None:
    monkeypatch.setattr(ssl_tls, "_probe_legacy_tls", lambda host, port: list(versions))


# ---------------- scan(): quyết định dựa trên kết quả bắt tay và dò ----------------


async def test_legacy_versions_accepted_alongside_modern_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server hỗ trợ cả TLS 1.3 lẫn TLS 1.0/1.1 -> vẫn báo outdated_tls_version."""
    _patch_fetch(monkeypatch, "TLSv1.3")
    _patch_probe(monkeypatch, ["TLSv1", "TLSv1.1"])
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["outdated_tls_version"]
    assert findings[0]["severity"] == "high"
    assert "TLSv1, TLSv1.1" in findings[0]["description"]


async def test_modern_only_server_has_no_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fetch(monkeypatch, "TLSv1.3")
    _patch_probe(monkeypatch, [])
    assert await SSLTLSModule().scan("https://example.com") == []


async def test_negotiated_legacy_version_is_reported_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vừa thỏa thuận TLSv1 vừa dò thấy TLSv1 -> chỉ 1 finding, không lặp phiên bản."""
    _patch_fetch(monkeypatch, "TLSv1")
    _patch_probe(monkeypatch, ["TLSv1"])
    findings = await SSLTLSModule().scan("https://example.com")
    assert len(findings) == 1
    assert findings[0]["description"].count("TLSv1") == 1


async def test_legacy_only_server_is_reported_as_outdated_not_connection_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server chỉ có TLS cũ làm bắt tay mặc định thất bại -> báo TLS cũ, không báo 'không kết nối được'."""

    def handshake_fails(host: str, port: int) -> Any:
        raise ssl.SSLError("tlsv1 alert protocol version")

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", handshake_fails)
    _patch_probe(monkeypatch, ["TLSv1"])
    findings = await SSLTLSModule().scan("https://old.example.com")
    assert [f["name"] for f in findings] == ["outdated_tls_version"]
    assert "chỉ hỗ trợ" in findings[0]["description"]


async def test_failed_handshake_without_legacy_support_stays_connection_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handshake_fails(host: str, port: int) -> Any:
        raise ssl.SSLError("handshake failure")

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", handshake_fails)
    _patch_probe(monkeypatch, [])
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["ssl_connection_failed"]


async def test_certificate_errors_do_not_trigger_the_legacy_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chứng chỉ sai/tự ký không liên quan phiên bản TLS -> không dò."""

    def bad_cert(host: str, port: int) -> Any:
        raise ssl.SSLCertVerificationError("self-signed certificate")

    def probe_must_not_run(host: str, port: int) -> list[str]:
        raise AssertionError("probe should not run for certificate errors")

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", bad_cert)
    monkeypatch.setattr(ssl_tls, "_probe_legacy_tls", probe_must_not_run)
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["cert_self_signed"]


async def test_non_ssl_errors_do_not_trigger_the_legacy_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lỗi mạng thuần (connection refused) không phải vấn đề giao thức."""

    def refused(host: str, port: int) -> Any:
        raise ConnectionRefusedError("refused")

    def probe_must_not_run(host: str, port: int) -> list[str]:
        raise AssertionError("probe should not run for network errors")

    monkeypatch.setattr(ssl_tls, "_fetch_certificate", refused)
    monkeypatch.setattr(ssl_tls, "_probe_legacy_tls", probe_must_not_run)
    findings = await SSLTLSModule().scan("https://example.com")
    assert [f["name"] for f in findings] == ["ssl_connection_failed"]


# ---------------- _probe_legacy_tls(): dò thử với server TLS cục bộ thật ----------------


@contextmanager
def _local_tls_server(tmp_path: Any, min_version: ssl.TLSVersion, max_version: ssl.TLSVersion) -> Iterator[int]:
    """Mở server TLS trên 127.0.0.1 chỉ chấp nhận đúng dải phiên bản; trả về cổng."""
    if shutil.which("openssl") is None:
        pytest.skip("cần openssl CLI để sinh chứng chỉ thử nghiệm")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    # Config tối thiểu của riêng test: một số bản openssl trên Windows (vd Strawberry Perl)
    # trỏ tới file openssl.cnf không tồn tại và `req` sẽ lỗi nếu dựa vào cấu hình toàn cục.
    config = tmp_path / "openssl.cnf"
    config.write_text("[req]\ndistinguished_name = dn\nprompt = no\n[dn]\nCN = localhost\n")
    try:
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
             "-config", str(config), "-keyout", str(key), "-out", str(cert)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"openssl CLI của máy này không sinh được chứng chỉ thử nghiệm: {exc.stderr[-200:]!r}")
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cert), str(key))
        context.set_ciphers("ALL:@SECLEVEL=0")
        context.minimum_version = min_version
        context.maximum_version = max_version
    except (ssl.SSLError, ValueError):
        pytest.skip("OpenSSL của máy này không cho dựng server TLS phiên bản này")

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    listener.settimeout(0.2)
    stop = threading.Event()

    def serve() -> None:
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except (TimeoutError, OSError):
                continue
            try:
                with context.wrap_socket(conn, server_side=True):
                    pass
            except (ssl.SSLError, OSError):
                conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        stop.set()
        thread.join(timeout=2)
        listener.close()


@pytest.fixture
def real_probe(monkeypatch: pytest.MonkeyPatch):
    """Bỏ bản giả của `_probe_legacy_tls` (autouse ở conftest) để dùng hàm thật."""
    monkeypatch.undo()
    return ssl_tls._probe_legacy_tls


def test_probe_detects_a_server_that_accepts_tls_1_0(tmp_path: Any, real_probe: Any) -> None:
    with _local_tls_server(tmp_path, ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1) as port:
        found = real_probe("127.0.0.1", port)
    if not found:
        pytest.skip("máy quét này không thể thử TLS 1.0 (OpenSSL đã tắt)")
    assert found == ["TLSv1"]


def test_probe_finds_nothing_on_a_modern_only_server(tmp_path: Any, real_probe: Any) -> None:
    with _local_tls_server(tmp_path, ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3) as port:
        assert real_probe("127.0.0.1", port) == []


def test_probe_returns_nothing_when_the_port_is_closed(real_probe: Any) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    assert real_probe("127.0.0.1", port) == []
