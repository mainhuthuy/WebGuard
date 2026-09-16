import asyncio
from collections.abc import AsyncGenerator
import logging
from typing import Any

from app.modules.cookies import CookiesModule
from app.modules.cors import CorsModule
from app.modules.headers import HeadersModule
from app.modules.information import InformationModule
from app.modules.scoring import ScoringEngine
from app.modules.ssl_tls import SSLTLSModule
from app.schemas.scan import ScanEventType

logger = logging.getLogger("app.modules.scanner")


class Scanner:
    def __init__(self) -> None:
        # Khởi tạo tất cả modules
        self.modules = [
            HeadersModule(),
            CookiesModule(),
            SSLTLSModule(),
            InformationModule(),
            CorsModule(),
        ]
        self.scoring = ScoringEngine()

    async def scan(self, url: str) -> dict[str, Any]:
        # 1. Chạy song song tất cả modules bằng asyncio.gather()
        tasks = [module.scan(url) for module in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 2. Gộp tất cả findings thành 1 list
        findings: list[dict[str, Any]] = []
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
            "scoring": scoring,
        }

    async def scan_stream(
        self, url: str, scan_id: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Thực hiện quét bảo mật và phát sự kiện tiến trình thời gian thực qua AsyncGenerator."""
        all_findings: list[dict[str, Any]] = []
        empty_findings: list[dict[str, Any]] = []
        total_modules = len(self.modules)

        # 1. Bắn sự kiện START
        yield {
            "event": ScanEventType.START.value,
            "scan_id": scan_id,
            "progress": 5,
            "message": f"Bắt đầu phiên quét an ninh cho mục tiêu: {url}",
            "module": None,
            "findings": empty_findings,
            "data": {"total_modules": total_modules},
        }

        # 2. Lần lượt quét từng module
        for idx, module in enumerate(self.modules, start=1):
            step_progress = 10 + int((idx - 1) * (75 / total_modules))
            yield {
                "event": ScanEventType.MODULE_START.value,
                "scan_id": scan_id,
                "progress": step_progress,
                "message": f"Đang kiểm tra: {module.description}...",
                "module": module.name,
                "findings": empty_findings,
                "data": None,
            }

            module_findings: list[dict[str, Any]] = []
            try:
                raw_res = await module.scan(url)
                if isinstance(raw_res, list):
                    module_findings = raw_res
                elif isinstance(raw_res, dict):
                    module_findings = [raw_res]
            except Exception as e:
                logger.warning(
                    f"Module {module.name} gặp lỗi khi quét {url}: {e}"
                )
                module_findings = []

            all_findings.extend(module_findings)
            completed_progress = 10 + int(idx * (75 / total_modules))

            yield {
                "event": ScanEventType.MODULE_COMPLETED.value,
                "scan_id": scan_id,
                "progress": completed_progress,
                "message": f"Hoàn thành {module.name} (phát hiện {len(module_findings)} vấn đề)",
                "module": module.name,
                "findings": module_findings,
                "data": {"count": len(module_findings)},
            }

        # 3. Tính điểm an ninh
        scoring = self.scoring.calculate(all_findings)
        yield {
            "event": ScanEventType.SCORING.value,
            "scan_id": scan_id,
            "progress": 95,
            "message": f"Tổng kết: Điểm {scoring.get('score')} - Hạng {scoring.get('grade')}",
            "module": None,
            "findings": empty_findings,
            "data": {"scoring": scoring},
        }

        # 4. Bắn sự kiện COMPLETE
        yield {
            "event": ScanEventType.COMPLETE.value,
            "scan_id": scan_id,
            "progress": 100,
            "message": "Phiên quét an ninh hoàn tất thành công!",
            "module": None,
            "findings": all_findings,
            "data": {
                "url": url,
                "total_findings": len(all_findings),
                "scoring": scoring,
            },
        }

