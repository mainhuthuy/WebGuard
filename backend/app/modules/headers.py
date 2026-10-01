import httpx
from app.modules.base import HTTP_TIMEOUT, BaseModule

class HeadersModule(BaseModule):
    @property
    def name(self) -> str:
        return "headers"

    @property 
    def description(self) -> str:
        return "Kiểm tra HTTP Security Headers"

    SECURITY_HEADERS = [
        {
            "name" : "Content-Security-Policy",
            "severity" : "high",
            "description" : "CSP giúp ngăn chặn tấn công XSS bằng cách chỉ cho phép load tài nguyên từ nguồn tin cậy",
            "remediation" : "Thêm header: Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self';"
        },
        {
            "name": "Strict-Transport-Security",
            "severity": "high",
            "description": "HSTS ép trình duyệt luôn dùng HTTPS, chống tấn công Man-in-the-Middle",
            "remediation": "Thêm header: Strict-Transport-Security: max-age=31536000; includeSubDomains"
        },
        {
            "name" : "X-Frame-Options",
            "severity" : "medium",
            "description" : "XFO ngăn chặn tấn công Clickjacking bằng cách hạn chế frame",
            "remediation" : "Thêm header: X-Frame-Options: DENY"
        },
        {
            "name" : "X-Content-Type-Options",
            "severity" : "medium",
            "description" : "Ngăn chặn trình duyệt đoán sai Content-Type",
            "remediation" : "Thêm header: X-Content-Type-Options: nosniff"
        },
        {
            "name" : "X-XSS-Protection",
            "severity" : "low",
            "description" : "Bảo vệ XSS lỗi thời, CSP tốt hơn",
            "remediation" : "X-XSS-Protection: 1; mode=block (cần khi không có CSP)"
        },
        {
            "name" : "Referrer-Policy",
            "severity" : "low",
            "description" : "Kiểm soát thông tin referrer",
            "remediation" : "Thêm header: Referrer-Policy: strict-origin-when-cross-origin"
        },
        {
            "name" : "Permissions-Policy",
            "severity" : "medium",
            "description" : "Kiểm soát tính năng trình duyệt (camera, microphone...)",
            "remediation" : "Thêm header: Permissions-Policy: geolocation=(); microphone=(); camera=()"
        },
        {
            "name": "Cross-Origin-Opener-Policy",
            "severity": "medium",
            "description": "Ngăn chặn tấn công Spectre và các lỗ hổng liên quan đến cùng nguồn gốc",
            "remediation": "Thêm header: Cross-Origin-Opener-Policy: same-origin"
        },
        {
            "name": "Cross-Origin-Embedder-Policy",
            "severity": "medium",
            "description": "Ngăn chặn tải tài nguyên từ nguồn gốc khác vào cùng một ngữ cảnh",
            "remediation": "Thêm header: Cross-Origin-Embedder-Policy: require-corp"
        }
    ]

    async def scan(self, url: str, **kwargs) -> list:
        findings = []
        # Bước 1: Gửi request
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url)
        # Bước 2: Lấy headers từ response
        headers = response.headers
        # Bước 3: Duyệt qua từng header cần check
        for header in self.SECURITY_HEADERS:
            header_name = header["name"].lower()
            if header_name not in headers:
                findings.append({
                    "module": self.name,
                    "name" : header_name,
                    "severity" : header["severity"],
                    "description" : header["description"],
                    "remediation" : header["remediation"],
                    "url": url
                })
        # Bước 4: Trả về kết quả
        return findings