import asyncio
from app.modules.headers import HeadersModule
from app.modules.cookies import CookiesModule
from app.modules.ssl_tls import SSLTLSModule
from app.modules.information import InformationModule
from app.modules.cors import CorsModule
from app.modules.scoring import ScoringEngine

class Scanner:
    def __init__(self):
        # Khởi tạo tất cả modules
        self.modules = [
            HeadersModule(),
            CookiesModule(),
            SSLTLSModule(),
            InformationModule(),
            CorsModule()
        ]
        self.scoring = ScoringEngine()

    async def scan(self, url: str) -> dict:
        # 1. Chạy song song tất cả modules bằng asyncio.gather()
        tasks = [module.scan(url) for module in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 2. Gộp tất cả findings thành 1 list
        findings = []
        for result in results:
            if isinstance(result, list):
                findings.extend(result)
            elif isinstance(result, dict):
                findings.append(result)
        # 3. Tính điểm bằng ScoringEngine
        scoring = self.scoring.calculate(findings)
        # 4. Return kết quả tổng hợp
        return {
            "url": url,
            "total_findings": len(findings),
            "findings": findings,
            "scoring": scoring
        }
