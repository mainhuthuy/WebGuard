"""Integration tests for Report Export API endpoints."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core import Settings
from app.main import create_application


@pytest.fixture
def client() -> TestClient:
    """Khởi tạo TestClient cho ứng dụng WebGuard."""
    settings = Settings(
        ENV="testing",
        DEBUG=True,
        _env_file=None,
    )
    test_app = create_application(settings=settings)
    return TestClient(test_app, raise_server_exceptions=False)


def test_export_report_not_found(client: TestClient) -> None:
    """Kiểm tra xuất báo cáo với scan_id không tồn tại trả về 404."""
    response = client.get("/api/v1/report/non-existent-uuid/export?format=json")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SCAN_NOT_FOUND"


def test_export_report_json_pending(client: TestClient) -> None:
    """Kiểm tra xuất báo cáo JSON cho scan đang pending."""
    # 1. Tạo scan mới
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    scan_id = create_res.json()["scan_id"]

    # 2. Xuất báo cáo JSON
    export_res = client.get(f"/api/v1/report/{scan_id}/export?format=json")
    assert export_res.status_code == 200
    assert "application/json" in export_res.headers["content-type"]
    assert "attachment" in export_res.headers.get("content-disposition", "")

    data = export_res.json()
    assert data["scan_id"] == scan_id
    assert data["target_url"] == "https://example.com"
    assert data["total_findings"] == 0


def test_export_report_json_completed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra xuất báo cáo JSON sau khi quét hoàn tất có findings và scoring."""
    # 1. Tạo scan
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    scan_id = create_res.json()["scan_id"]

    # 2. Mock modules và chạy stream để quét xong
    async def mock_scan(self: Any, url: str) -> list[dict[str, Any]]:
        module_name = getattr(self, "name", "mock")
        return [
            {
                "module": module_name,
                "name": f"Mock {module_name} issue",
                "severity": "medium",
                "description": "Mock finding",
                "remediation": "Fix it",
                "url": url,
            }
        ]

    from app.modules.base import BaseModule
    monkeypatch.setattr(BaseModule, "scan", mock_scan)

    client.get(f"/api/v1/scan/{scan_id}/stream")

    # 3. Xuất báo cáo JSON
    export_res = client.get(f"/api/v1/report/{scan_id}/export?format=json")
    assert export_res.status_code == 200

    data = export_res.json()
    assert data["total_findings"] > 0
    assert data["scoring"] is not None
    assert data["severity_counts"]["medium"] > 0
    assert data["generated_at"] is not None


def test_export_report_html(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra xuất báo cáo HTML với template Jinja2."""
    # 1. Tạo scan
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    scan_id = create_res.json()["scan_id"]

    # 2. Mock và quét
    async def mock_scan(self: Any, url: str) -> list[dict[str, Any]]:
        module_name = getattr(self, "name", "mock")
        return [
            {
                "module": module_name,
                "name": f"Mock {module_name} issue",
                "severity": "high",
                "description": "Mock finding for HTML test",
                "remediation": "Fix it now",
                "url": url,
            }
        ]

    from app.modules.base import BaseModule
    monkeypatch.setattr(BaseModule, "scan", mock_scan)

    client.get(f"/api/v1/scan/{scan_id}/stream")

    # 3. Xuất báo cáo HTML
    export_res = client.get(f"/api/v1/report/{scan_id}/export?format=html")
    assert export_res.status_code == 200
    assert "text/html" in export_res.headers["content-type"]
    assert "attachment" in export_res.headers.get("content-disposition", "")

    html = export_res.text
    assert "WebGuard" in html
    assert "https://example.com" in html
    assert scan_id in html
