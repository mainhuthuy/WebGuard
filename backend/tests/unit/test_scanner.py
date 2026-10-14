from unittest.mock import AsyncMock

import pytest

from app.modules.scanner import Scanner
from app.schemas.scan import ScanResponse


def test_scanner_initialization():
    """Scanner phải khởi tạo đúng 7 modules bảo mật."""
    scanner = Scanner()
    assert len(scanner.modules) == 7
    module_names = [m.name for m in scanner.modules]
    assert "headers" in module_names
    assert "cookies" in module_names
    assert "ssl_tls" in module_names
    assert "information" in module_names
    assert "CORS" in module_names
    assert "content" in module_names
    assert "http_config" in module_names

@pytest.mark.asyncio
async def test_scanner_orchestrator_and_schema_validation():
    """Scanner chạy song song, gộp findings, tính điểm và khớp với Pydantic ScanResponse."""
    scanner = Scanner()

    # Mock kết quả trả về của từng module
    for m in scanner.modules:
        m.scan = AsyncMock(return_value=[{
            "module": m.name,
            "name": f"test_{m.name}",
            "severity": "medium",
            "description": "test desc",
            "remediation": "test remediation",
            "url": "https://test.com"
        }])

    result = await scanner.scan("https://test.com")

    # 1. Kiểm tra số lượng findings gộp (7 modules x 1 finding = 7)
    assert result["total_findings"] == 7
    assert len(result["findings"]) == 7

    # 2. Kiểm tra tính điểm: 100 - (7 x 3 điểm medium, mỗi module một loại riêng) = 79 -> Grade B
    assert result["scoring"]["score"] == 79
    assert result["scoring"]["grade"] == "B"

    # 3. Kiểm tra Hợp đồng dữ liệu Pydantic (Không được raise lỗi ValidationError)
    response_model = ScanResponse(**result)
    assert response_model.total_findings == 7
    assert response_model.scoring.grade == "B"

@pytest.mark.asyncio
async def test_scanner_resilience_when_module_fails():
    """Nếu 1 module bị văng Exception thì Scanner vẫn chạy tốt các module còn lại."""
    scanner = Scanner()

    # Cho module đầu tiên văng Exception giả lập
    scanner.modules[0].scan = AsyncMock(side_effect=Exception("Network Timeout"))

    # Các modules còn lại trả về kết quả bình thường
    for m in scanner.modules[1:]:
        m.scan = AsyncMock(return_value=[{
            "module": m.name,
            "name": "finding",
            "severity": "low",
            "description": "desc",
            "remediation": "rem",
            "url": "https://test.com"
        }])

    result = await scanner.scan("https://test.com")

    # Vẫn lấy được 6 findings từ 6 modules kia mà không bị crash
    assert result["total_findings"] == 6


def test_quick_mode_runs_only_headers_and_ssl() -> None:
    """Quick chỉ gồm Headers + SSL/TLS."""
    scanner = Scanner(mode="quick")
    assert [m.name for m in scanner.modules] == ["headers", "ssl_tls"]


def test_full_mode_runs_all_modules() -> None:
    """Full (và mặc định) gồm đủ 7 module."""
    assert len(Scanner(mode="full").modules) == 7
    assert len(Scanner().modules) == 7


async def test_quick_mode_stream_reports_two_modules() -> None:
    """Luồng SSE ở chế độ quick chỉ có 2 module và total_modules=2."""
    scanner = Scanner(mode="quick")

    class _Stub:
        def __init__(self, name: str) -> None:
            self.name = name
            self.description = name

        async def scan(self, url: str, **kwargs: object) -> list:
            return []

    scanner.modules = [_Stub("headers"), _Stub("ssl_tls")]  # type: ignore[list-item]
    events = [e async for e in scanner.scan_stream("https://example.com", "id-1")]
    assert events[0]["data"] == {"total_modules": 2}
    assert [e["module"] for e in events if e["event"] == "module_completed"] == [
        "headers",
        "ssl_tls",
    ]
