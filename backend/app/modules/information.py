import httpx
from app.modules.base import BaseModule

class InformationModule(BaseModule):
    @property
    def name(self) -> str:
        return "information"

    @property
    def description(self) -> str:
        return "Rà soát lộ file và thông tin nhạy cảm"

    SENSITIVE_PATHS = [
        {
            "path" : "/.env",
            "severity" : "critical",
            "description": "File .env chứa biến môi trường nhạy cảm (mật khẩu, API keys)",
            "remediation": "Chặn truy cập file .env trong cấu hình web server"
        },
        {
            "path" : "/.git/HEAD",
            "severity" : "critical",
            "description" : "Lộ thông tin về git repository",
            "remediation" : "Xóa file .git/HEAD hoặc chặn truy cập"
        },
        {
            "path" : "/robots.txt",
            "severity" : "low",
            "description" : "File robots.txt chỉ dẫn cho bot biết nên crawl vào đâu, tránh đâu",
            "remediation" : "Nếu có những đường dẫn nhạy cảm cần che giấu thì hãy thêm vào file robots.txt"
        },
        {
            "path" : "/wp-admin",
            "severity" : "medium",
            "description" : "Cổng quản trị website",
            "remediation" : "Tăng cường bảo mật cho cổng quản trị"
        }
    ]

    async def scan(self, url: str, **kwargs) -> list:
        findings = []
        async with httpx.AsyncClient() as client:
            # Duyệt qua từng path
            for item in self.SENSITIVE_PATHS:
                target = url.rstrip("/") + item["path"]
                try:
                    response = await client.get(target)
                    if response.status_code == 200:
                        # File tồn tại → Finding!
                        findings.append({
                            "module" : self.name,
                            "name" : item["path"],
                            "severity" : item["severity"],
                            "description" : item["description"],
                            "remediation" : item["remediation"],
                            "url" : target
                        })
                except:
                    pass
            
            try:
                response = await client.get(url)
                server = response.headers.get("Server")
                if server:
                    findings.append({
                        "module" : self.name,
                        "name" : "Server header",
                        "severity" : "medium",
                        "description" : "Lộ thông tin về framework/công nghệ được sử dụng",
                        "remediation" : "Xóa header Server hoặc sử dụng Reverse Proxy để che giấu",
                        "url" : url
                    })
                # Check X-Powered-By header
                xpb = response.headers.get("X-Powered-By")
                if xpb:
                    findings.append({
                        "module": self.name,
                        "name": "X-Powered-By header",
                        "severity": "medium",
                        "description": f"Lộ thông tin framework: {xpb}",
                        "remediation": "Xóa header X-Powered-By",
                        "url": url
                    })
            except:
                pass
        return findings