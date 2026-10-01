import httpx 
from app.modules.base import HTTP_TIMEOUT, BaseModule

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
            # Lấy tên cookie (phần trước dấu =)
            cookie_name = cookie_str.split("=")[0].strip()

            # Duyệt qua TỪNG flag cần check
            for flag in self.COOKIE_FLAGS:
                # Kiểm tra flag["name"].lower() có trong cookie_str.lower() không
                # Nếu KHÔNG có → append finding
                if flag["name"].lower() not in cookie_str.lower():
                    findings.append({
                        "module": self.name,
                        "name" : cookie_name,
                        "flag_missing": flag["name"],
                        "severity" : flag["severity"],
                        "description" : flag["description"],
                        "remediation" : flag["remediation"],
                        "url": url
                    })
        return findings
