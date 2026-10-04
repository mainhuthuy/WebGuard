import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from app.modules.base import HTTP_TIMEOUT, BaseModule

# Tên cookie trông giống cookie phiên/xác thực (dùng để đánh giá domain & thời hạn)
SESSION_COOKIE_PATTERN = re.compile(r"sess|sid|auth|token|jwt|login|csrf|xsrf", re.IGNORECASE)
LONG_LIVED_SECONDS = 30 * 24 * 3600  # 30 ngày


class CookiesModule(BaseModule):
    @property
    def name(self) -> str:
        return "cookies"

    @property
    def description(self) -> str:
        return "Kiểm tra cờ bảo mật của Cookie"

    COOKIE_FLAGS = [
        {
            "name" : "Secure",
            "severity" : "high",
            "description" : "Cookie chỉ gửi qua HTTPS",
            "remediation" : "Thêm cookie flag: Secure"
        },
        {
            "name" : "HttpOnly",
            "severity" : "high",
            "description" : "Ngăn cookie bị đánh cắp bởi XSS",
            "remediation" : "Thêm cookie flag: HttpOnly"
        },
        {
            "name" : "SameSite",
            "severity" : "medium",
            "description" : "Chống tấn công CSRF",
            "remediation" : "Thêm cookie flag: SameSite=Lax hoặc Strict"
        }
    ]

    # Cookie có đủ cờ nhưng cấu hình vẫn rủi ro (key = `name`, hiện ở trường flag_missing)
    COOKIE_ISSUES = [
        {
            "name": "SameSite=None",
            "severity": "medium",
            "description": "Cookie đặt SameSite=None nên được gửi kèm mọi request từ website khác (rủi ro CSRF)",
            "remediation": "Dùng SameSite=Lax hoặc Strict trừ khi thật sự cần dùng cross-site"
        },
        {
            "name": "cookie_prefix_violation",
            "severity": "low",
            "description": "Cookie dùng tiền tố __Host-/__Secure- nhưng thiếu thuộc tính bắt buộc nên trình duyệt sẽ từ chối",
            "remediation": "__Secure- cần Secure; __Host- cần Secure, Path=/ và không có Domain"
        },
        {
            "name": "cookie_broad_domain",
            "severity": "low",
            "description": "Cookie phiên đặt thuộc tính Domain nên được chia sẻ cho mọi subdomain (một subdomain bị chiếm là lộ phiên)",
            "remediation": "Bỏ thuộc tính Domain để cookie chỉ áp dụng cho đúng host phát hành"
        },
        {
            "name": "cookie_long_lived",
            "severity": "low",
            "description": "Cookie phiên/xác thực sống hơn 30 ngày, tăng thời gian kẻ tấn công có thể dùng cookie bị đánh cắp",
            "remediation": "Rút ngắn Max-Age/Expires hoặc dùng session cookie cho phiên đăng nhập"
        }
    ]

    @staticmethod
    def _lifetime_seconds(attributes: dict[str, str]) -> float | None:
        """Thời gian sống của cookie (giây) theo Max-Age (ưu tiên) hoặc Expires."""
        max_age = attributes.get("max-age")
        if max_age is not None:
            try:
                return float(max_age)
            except ValueError:
                return None
        expires = attributes.get("expires")
        if expires:
            try:
                when = parsedate_to_datetime(expires)
            except (TypeError, ValueError):
                return None
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            return (when - datetime.now(UTC)).total_seconds()
        return None

    def _risky_config(self, cookie_name: str, attributes: dict[str, str]) -> list[str]:
        """Các khóa COOKIE_ISSUES mà cookie này vi phạm."""
        issues: list[str] = []
        if attributes.get("samesite", "").lower() == "none":
            issues.append("SameSite=None")

        lowered = cookie_name.lower()
        if lowered.startswith("__secure-") and "secure" not in attributes or lowered.startswith("__host-") and (
            "secure" not in attributes
            or attributes.get("path") != "/"
            or "domain" in attributes
        ):
            issues.append("cookie_prefix_violation")

        sensitive = bool(SESSION_COOKIE_PATTERN.search(cookie_name))
        if sensitive and "domain" in attributes and not lowered.startswith("__host-"):
            issues.append("cookie_broad_domain")
        if sensitive:
            lifetime = self._lifetime_seconds(attributes)
            if lifetime is not None and lifetime > LONG_LIVED_SECONDS:
                issues.append("cookie_long_lived")
        return issues

    async def scan(self, url: str, **kwargs) -> list:
        findings = []

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url)

        # Lấy TẤT CẢ raw cookies (dạng string)
        raw_cookies = response.headers.get_list("set-cookie")

        # Nếu không có cookie nào → return luôn
        if not raw_cookies:
            return findings

        # Duyệt qua TỪNG cookie
        for cookie_str in raw_cookies:
            # Tách "tên=giá trị; Attr1; Attr2=giá trị" thành các phần theo dấu ;
            parts = [p.strip() for p in cookie_str.split(";")]
            # Tên cookie = phần trước dấu = của phần đầu tiên
            cookie_name = parts[0].split("=")[0].strip()
            # Chỉ so khớp TÊN THUỘC TÍNH (bỏ phần đầu là tên=giá trị): tránh nhầm với
            # cookie có tên/giá trị chứa chữ "secure", "samesite"...
            attribute_values = {
                p.split("=")[0].strip().lower(): (p.split("=", 1)[1].strip() if "=" in p else "")
                for p in parts[1:]
            }
            attributes = set(attribute_values)

            # Duyệt qua TỪNG flag cần check
            for flag in self.COOKIE_FLAGS:
                # Nếu thuộc tính KHÔNG có → append finding
                if flag["name"].lower() not in attributes:
                    findings.append({
                        "module": self.name,
                        "name" : cookie_name,
                        "flag_missing": flag["name"],
                        "severity" : flag["severity"],
                        "description" : flag["description"],
                        "remediation" : flag["remediation"],
                        "url": url
                    })

            # Cookie có đủ cờ nhưng cấu hình rủi ro
            risky = self._risky_config(cookie_name, attribute_values)
            for issue in self.COOKIE_ISSUES:
                if issue["name"] in risky:
                    findings.append({
                        "module": self.name,
                        "name": cookie_name,
                        "flag_missing": issue["name"],
                        "severity": issue["severity"],
                        "description": issue["description"],
                        "remediation": issue["remediation"],
                        "url": url
                    })
        return findings
