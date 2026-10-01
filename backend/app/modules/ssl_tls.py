import asyncio
import ssl
import socket
import datetime
from typing import Any
from urllib.parse import urlparse
from app.modules.base import HTTP_TIMEOUT, BaseModule


def _fetch_certificate(host: str, port: int) -> tuple[dict[str, Any], str | None]:
    """Kết nối TLS (blocking) và trả về (cert, phiên bản TLS). Chạy trong thread riêng."""
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=HTTP_TIMEOUT) as sock:
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            return ssock.getpeercert() or {}, ssock.version()

class SSLTLSModule(BaseModule):
    @property
    def name(self) -> str:
        return "ssl_tls"
    
    @property
    def description(self) -> str:
        return "Kiểm tra cấu hình SSL/TLS của trang web"

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
            findings.append({
                "module": self.name,
                "name": "ssl_connection_failed",
                "severity": "critical",
                "description": f"Không thể kết nối SSL/TLS: {str(e)}",
                "remediation": "Đảm bảo trang web hỗ trợ HTTPS",
                "url": url
            })
            return findings
        # Bước 2: Kiểm tra phiên bản TLS cũ
        if tls_version in ["TLSv1", "TLSv1.1", "SSLv3"]:
            findings.append({
                "module": self.name,
                "name": "outdated_tls_version",
                "severity": "high",
                "description": f"Phiên bản TLS không an toàn: {tls_version}",
                "remediation": "Nâng cấp lên TLS 1.2 hoặc TLS 1.3",
                "url": url
            })
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
