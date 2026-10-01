import httpx

from app.modules.base import HTTP_TIMEOUT, BaseModule

# Origin giả mạo dùng để dò xem server có "tin" mọi origin không
EVIL_ORIGIN = "https://evil.com"


class CorsModule(BaseModule):
    @property
    def name(self) -> str:
        return "CORS"
    
    @property
    def description(self) -> str:
        return "Kiểm tra cấu hình sai CORS"
    
    async def scan(self, url: str, **kwargs) -> list:
        findings = []
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # Check 1: Wildcard
            response = await client.get(url)
            acao = response.headers.get("access-control-allow-origin")
            if acao == "*":
                # Finding: wildcard origin
                findings.append({
                    "module": self.name,
                    "name": "cors_wildcard",
                    "severity": "high",
                    "description": "Server cho phép mọi origin truy cập (Access-Control-Allow-Origin: *)",
                    "remediation": "Chỉ định cụ thể domain được phép thay vì dùng wildcard *",
                    "url": url
                })
            # Check 2: Origin reflection
            response = await client.get(url, headers={"Origin": EVIL_ORIGIN})
            acao = response.headers.get("access-control-allow-origin")
            reflected = acao == EVIL_ORIGIN
            if reflected:
                # Finding: server phản hồi origin tùy tiện
                findings.append({
                    "module": self.name,
                    "name": "cors_origin_reflection",
                    "severity": "critical",
                    "description": "Server phản hồi lại bất kỳ Origin nào — cho phép trang web độc hại gọi API",
                    "remediation": "Kiểm tra Origin trong whitelist trước khi phản hồi, không phản hồi origin tùy tiện",
                    "url": url
                })
            # Check 3: Credentials — chỉ nguy hiểm khi origin lạ được PHẢN XẠ lại.
            # (Allow-Origin cố định + Allow-Credentials: true là cấu hình hợp lệ.)
            acac = response.headers.get("access-control-allow-credentials")
            if reflected and acac and acac.lower() == "true":
                # CRITICAL! Server cho phép gửi cookie từ origin bất kỳ
                findings.append({
                    "module": self.name,
                    "name": "cors_credentials_exposed",
                    "severity": "critical",
                    "description": "Server cho phép gửi cookie cross-origin — trang web độc hại có thể đánh cắp session",
                    "remediation": "Tắt Access-Control-Allow-Credentials hoặc giới hạn origin cụ thể",
                    "url": url
                })
        return findings