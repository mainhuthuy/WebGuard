import asyncio
import ssl
import socket
import datetime
import warnings
from typing import Any
from urllib.parse import urlparse
from app.modules.base import HTTP_TIMEOUT, BaseModule


def _fetch_certificate(host: str, port: int) -> tuple[dict[str, Any], str | None]:
    """Kết nối TLS (blocking) và trả về (cert, phiên bản TLS). Chạy trong thread riêng."""
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=HTTP_TIMEOUT) as sock:
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            return ssock.getpeercert() or {}, ssock.version()

# Các phiên bản TLS cũ cần dò xem server còn chấp nhận không (Python không còn hỗ trợ SSLv3)
LEGACY_TLS_VERSIONS = (
    ("TLSv1", ssl.TLSVersion.TLSv1),
    ("TLSv1.1", ssl.TLSVersion.TLSv1_1),
)
PROBE_TIMEOUT = 5.0


def _probe_legacy_tls(host: str, port: int) -> list[str]:
    """Dò xem server còn chấp nhận TLS 1.0 / 1.1 không (blocking, chạy trong thread).

    Mỗi phiên bản cũ được thử bằng một lần bắt tay riêng, ép cả `minimum_version` lẫn
    `maximum_version` về đúng phiên bản đó. Không xác minh chứng chỉ vì ta chỉ quan tâm
    server có CHẤP NHẬN giao thức cũ hay không. Nếu máy quét không thể thử một phiên bản
    (OpenSSL tắt hẳn) thì bỏ qua phiên bản đó — kết quả là "không biết", không phải "an toàn".
    """
    supported: list[str] = []
    for name, version in LEGACY_TLS_VERSIONS:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                context.set_ciphers("ALL:@SECLEVEL=0")  # cho phép bộ mã hóa cũ
                context.minimum_version = version
                context.maximum_version = version
        except (ssl.SSLError, ValueError):
            continue
        try:
            with socket.create_connection((host, port), timeout=PROBE_TIMEOUT) as sock:
                with context.wrap_socket(sock, server_hostname=host):
                    supported.append(name)
        except (OSError, ssl.SSLError):
            continue
    return supported


class SSLTLSModule(BaseModule):
    @property
    def name(self) -> str:
        return "ssl_tls"
    
    @property
    def description(self) -> str:
        return "Kiểm tra cấu hình SSL/TLS của trang web"

    def _legacy_finding(self, versions: list[str], url: str, only_legacy: bool = False) -> dict:
        listed = ", ".join(versions)
        detail = (
            f"Server chỉ hỗ trợ giao thức TLS cũ: {listed}" if only_legacy
            else f"Server vẫn chấp nhận phiên bản TLS không an toàn: {listed}"
        )
        return {
            "module": self.name,
            "name": "outdated_tls_version",
            "severity": "high",
            "description": detail,
            "remediation": "Tắt TLS 1.0/1.1, chỉ cho phép TLS 1.2 hoặc TLS 1.3",
            "url": url
        }

    async def scan(self, url: str, **kwargs) -> list:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or 443
        findings = []
        # Bước 1: Kết nối SSL và lấy thông tin chứng chỉ
        try:
            # socket đồng bộ -> chạy trong thread để không chặn event loop
            cert, tls_version = await asyncio.to_thread(_fetch_certificate, host, port)
        except Exception as e:
            # Server chỉ hỗ trợ TLS cũ cũng làm bắt tay thất bại (client mặc định đòi TLS >= 1.2).
            # Chứng chỉ sai/tự ký (SSLCertVerificationError) là nguyên nhân khác -> không dò.
            if isinstance(e, ssl.SSLError) and not isinstance(e, ssl.SSLCertVerificationError):
                legacy = await asyncio.to_thread(_probe_legacy_tls, host, port)
                if legacy:
                    findings.append(self._legacy_finding(legacy, url, only_legacy=True))
                    return findings
            findings.append({
                "module": self.name,
                "name": "ssl_connection_failed",
                "severity": "critical",
                "description": f"Không thể kết nối SSL/TLS: {str(e)}",
                "remediation": "Đảm bảo trang web hỗ trợ HTTPS",
                "url": url
            })
            return findings
        # Bước 2: Kiểm tra phiên bản TLS cũ: phiên bản vừa thỏa thuận VÀ các phiên bản cũ
        # mà server vẫn chấp nhận (dù server cũng hỗ trợ TLS mới)
        legacy_versions = await asyncio.to_thread(_probe_legacy_tls, host, port)
        if tls_version in ["TLSv1", "TLSv1.1", "SSLv3"] and tls_version not in legacy_versions:
            legacy_versions.append(tls_version)
        if legacy_versions:
            findings.append(self._legacy_finding(legacy_versions, url))
        # Bước 3: Kiểm tra ngày hết hạn chứng chỉ
        if not cert:
            return findings
        expire_timestamp = ssl.cert_time_to_seconds(str(cert['notAfter']))
        expire_date = datetime.datetime.fromtimestamp(expire_timestamp, tz=datetime.timezone.utc)
        days_left = (expire_date - datetime.datetime.now(datetime.timezone.utc)).days
        if days_left < 0:
            findings.append({
                "module": self.name,
                "name": "cert_expired",
                "severity": "critical",
                "description": f"Chứng chỉ đã hết hạn {abs(days_left)} ngày trước",
                "remediation": "Gia hạn chứng chỉ SSL ngay lập tức",
                "url": url
            })
        elif days_left < 30:
            findings.append({
                "module": self.name,
                "name": "cert_expiring_soon",
                "severity": "medium",
                "description": f"Chứng chỉ sẽ hết hạn trong {days_left} ngày",
                "remediation": "Gia hạn chứng chỉ SSL trước khi hết hạn",
                "url": url
            })
        return findings
