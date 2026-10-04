"""Kiểm tra an toàn cho URL mục tiêu (chống SSRF)."""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

from app.core.errors import InvalidTargetException

logger = logging.getLogger("app.core.security")


async def _resolve(hostname: str) -> list[str]:
    """Phân giải hostname thành danh sách địa chỉ IP (raise socket.gaierror nếu thất bại)."""
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    return [str(info[4][0]).split("%")[0] for info in infos]  # bỏ zone id của IPv6


async def assert_public_target(url: str) -> None:
    """Phân giải DNS của hostname và từ chối nếu bất kỳ địa chỉ nào không phải IP public.

    Chặn tên miền trỏ về loopback / private / link-local (vd: cloud metadata 169.254.169.254).
    Nếu DNS không phân giải được thì cho qua: phiên quét sẽ tự báo lỗi kết nối.

    Lưu ý: đây là kiểm tra tại thời điểm tạo scan; không chống được DNS rebinding hoàn toàn.
    """
    hostname = urlparse(url).hostname
    if not hostname:
        raise InvalidTargetException("URL không hợp lệ, không tìm thấy hostname")

    try:
        addresses = await _resolve(hostname)
    except socket.gaierror:
        logger.info(f"Không phân giải được DNS cho {hostname}, bỏ qua kiểm tra SSRF")
        return

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if not ip.is_global:
            logger.warning(f"Chặn target {hostname}: phân giải về địa chỉ không public {ip}")
            raise InvalidTargetException(
                "Tên miền phân giải về địa chỉ mạng nội bộ hoặc không công khai, không được phép quét",
                details={"hostname": hostname},
            )
