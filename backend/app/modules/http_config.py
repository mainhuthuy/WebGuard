from urllib.parse import urlencode, urlparse

import httpx

from app.modules.base import HTTP_TIMEOUT, BaseModule

REDIRECT_STATUSES = (301, 302, 303, 307, 308)
# Các phương thức HTTP không nên mở cho người dùng ẩn danh
RISKY_METHODS = ("PUT", "DELETE", "CONNECT")

# Tên tham số thường dùng để chuyển hướng sau đăng nhập/đăng xuất/liên kết ngoài
REDIRECT_PARAM_NAMES = (
    "redirect", "redirect_uri", "redirect_url", "url", "next", "return",
    "returnto", "return_url", "continue", "dest", "destination", "r",
)
# .invalid dành riêng cho mục đích test, không bao giờ phân giải được (RFC 2606) — an toàn để làm "mồi"
OPEN_REDIRECT_MARKER = "https://webguard-redirect-check.invalid/"


class HttpConfigModule(BaseModule):
    @property
    def name(self) -> str:
        return "http_config"

    @property
    def description(self) -> str:
        return "Kiểm tra cấu hình HTTP/HTTPS của server"

    def _finding(self, name: str, severity: str, description: str, remediation: str, url: str) -> dict:
        return {
            "module": self.name,
            "name": name,
            "severity": severity,
            "description": description,
            "remediation": remediation,
            "url": url,
        }

    @staticmethod
    def _plain_http_url(url: str) -> str:
        """URL phiên bản HTTP thuần của target (cổng 80, hoặc đúng cổng nếu target là http://)."""
        parsed = urlparse(url)
        netloc = parsed.netloc if parsed.scheme == "http" else (parsed.hostname or "")
        if ":" in netloc and parsed.scheme != "http":
            netloc = f"[{netloc}]"  # IPv6 literal
        return f"http://{netloc}/"

    async def _check_https_redirect(self, client: httpx.AsyncClient, url: str) -> dict | None:
        target = self._plain_http_url(url)
        try:
            response = await client.get(target)
        except httpx.HTTPError:
            return None  # cổng 80 đóng: chỉ phục vụ HTTPS, tốt
        location = response.headers.get("location", "")
        if response.status_code in REDIRECT_STATUSES and location.lower().startswith("https://"):
            return None
        # Redirect sang http:// hoặc đường dẫn tương đối vẫn nằm trên HTTP → chưa ép HTTPS
        if response.status_code >= 400:
            return None
        return self._finding(
            "https_not_enforced",
            "high",
            "Website vẫn phục vụ nội dung qua HTTP thuần mà không chuyển hướng sang HTTPS, "
            "nên người dùng có thể bị nghe lén hoặc bị hạ cấp kết nối",
            "Chuyển hướng 301 toàn bộ HTTP sang HTTPS và bật HSTS",
            target,
        )

    async def _check_trace(self, client: httpx.AsyncClient, url: str) -> dict | None:
        try:
            response = await client.request("TRACE", url)
        except httpx.HTTPError:
            return None
        if response.status_code == 200 and "trace" in response.text[:4096].lower():
            return self._finding(
                "http_trace_enabled",
                "medium",
                "Server bật phương thức HTTP TRACE, có thể bị lạm dụng để đánh cắp header/cookie (Cross-Site Tracing)",
                "Tắt TRACE (Apache: TraceEnable off; Nginx: mặc định đã chặn)",
                url,
            )
        return None

    async def _check_allowed_methods(self, client: httpx.AsyncClient, url: str) -> dict | None:
        try:
            response = await client.request("OPTIONS", url)
        except httpx.HTTPError:
            return None
        allow = response.headers.get("allow", "")
        methods = {m.strip().upper() for m in allow.split(",") if m.strip()}
        risky = [m for m in RISKY_METHODS if m in methods]
        if not risky:
            return None
        return self._finding(
            "risky_http_methods",
            "medium",
            f"Server quảng bá các phương thức có thể sửa/xóa dữ liệu: {', '.join(risky)}",
            "Chỉ cho phép GET/POST/HEAD cho người dùng ẩn danh; chặn PUT/DELETE/CONNECT",
            url,
        )

    async def _check_security_txt(self, client: httpx.AsyncClient, url: str) -> dict | None:
        parsed = urlparse(url)
        target = f"{parsed.scheme}://{parsed.netloc}/.well-known/security.txt"
        try:
            response = await client.get(target)
        except httpx.HTTPError:
            return None
        if response.status_code == 200 and "contact:" in response.text[:8192].lower():
            return None
        return self._finding(
            "security_txt_missing",
            "low",
            "Website không công bố security.txt nên nhà nghiên cứu khó báo cáo lỗ hổng cho bạn",
            "Tạo /.well-known/security.txt với Contact và Expires (RFC 9116)",
            target,
        )

    async def _check_open_redirect(self, client: httpx.AsyncClient, url: str) -> dict | None:
        """Dò xem server có chuyển hướng thẳng tới giá trị của một tham số phổ biến không.

        Chỉ gửi GET với query string vô hại, không theo redirect (httpx mặc định không theo),
        nên không có gì thực sự được tải từ domain .invalid cả.
        """
        separator = "&" if "?" in url else "?"
        for param in REDIRECT_PARAM_NAMES:
            probe = f"{url}{separator}{urlencode({param: OPEN_REDIRECT_MARKER})}"
            try:
                response = await client.get(probe)
            except httpx.HTTPError:
                continue
            location = response.headers.get("location", "")
            if response.status_code in REDIRECT_STATUSES and "webguard-redirect-check.invalid" in location:
                return self._finding(
                    "open_redirect", "medium",
                    f"Tham số '{param}' được dùng làm đích chuyển hướng mà không xác thực — server chuyển "
                    "thẳng người dùng tới địa chỉ do tham số này chỉ định",
                    "Chỉ cho phép chuyển hướng tới danh sách đường dẫn nội bộ cố định, hoặc kiểm tra "
                    "domain đích khớp với whitelist trước khi redirect",
                    probe,
                )
        return None

    async def scan(self, url: str, **kwargs) -> list:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            results = [
                await self._check_https_redirect(client, url),
                await self._check_trace(client, url),
                await self._check_allowed_methods(client, url),
                await self._check_security_txt(client, url),
                await self._check_open_redirect(client, url),
            ]
        return [r for r in results if r]
