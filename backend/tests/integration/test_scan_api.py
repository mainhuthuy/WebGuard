"""Integration tests for Scan API endpoints."""

from typing import Any

from fastapi.testclient import TestClient
import pytest

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


def test_create_scan_success(client: TestClient) -> None:
    """Kiểm tra tạo lượt quét mới thành công với URL hợp lệ (HTTP 201)."""
    payload = {"url": "https://example.com"}
    response = client.post("/api/v1/scan", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "scan_id" in data
    assert len(data["scan_id"]) > 0
    assert data["target_url"] == "https://example.com"
    assert data["status"] == "pending"
    assert "created_at" in data


def test_create_scan_invalid_scheme(client: TestClient) -> None:
    """Kiểm tra URL không dùng http/https bị Pydantic bắt lỗi 422."""
    payload = {"url": "ftp://files.example.com"}
    response = client.post("/api/v1/scan", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_create_scan_blocked_localhost_ssrf(client: TestClient) -> None:
    """Kiểm tra cơ chế chống SSRF chặn quét localhost / 127.0.0.1."""
    # Test localhost
    res1 = client.post("/api/v1/scan", json={"url": "http://localhost:8000"})
    assert res1.status_code == 422

    # Test loopback IP
    res2 = client.post("/api/v1/scan", json={"url": "http://127.0.0.1:8000"})
    assert res2.status_code == 422


def test_create_scan_blocked_private_ip_ssrf(client: TestClient) -> None:
    """Kiểm tra cơ chế chống SSRF chặn quét IP mạng nội bộ."""
    payload = {"url": "http://192.168.1.1"}
    response = client.post("/api/v1/scan", json=payload)

    assert response.status_code == 422


def test_stream_scan_not_found(client: TestClient) -> None:
    """Kiểm tra khi scan_id không tồn tại thì trả về HTTP 404."""
    response = client.get("/api/v1/scan/non-existent-uuid/stream")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SCAN_NOT_FOUND"


def test_stream_scan_success_and_replay(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra luồng stream SSE hoạt động đầy đủ từ start đến complete và tính năng replay."""
    # 1. Tạo một scan mới
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    assert create_res.status_code == 201
    scan_id = create_res.json()["scan_id"]

    # 2. Mock các module quét để test chạy nhanh và độc lập mạng
    async def mock_scan(self: Any, url: str) -> list[dict[str, Any]]:
        module_name = getattr(self, "name", "mock")
        return [
            {
                "module": module_name,
                "name": f"Mock {module_name} issue",
                "severity": "medium",
                "description": "Mock finding for test",
                "remediation": "Fix it",
                "url": url,
            }
        ]

    from app.modules.base import BaseModule
    monkeypatch.setattr(BaseModule, "scan", mock_scan)

    # 3. Kết nối tới SSE stream
    stream_res = client.get(f"/api/v1/scan/{scan_id}/stream")
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]

    body = stream_res.text
    assert "event: start" in body
    assert "event: module_start" in body
    assert "event: module_completed" in body
    assert "event: scoring" in body
    assert "event: complete" in body

    # 4. Kiểm tra replay: Khi scan đã hoàn tất, gọi lại stream sẽ trả ngay sự kiện complete
    replay_res = client.get(f"/api/v1/scan/{scan_id}/stream")
    assert replay_res.status_code == 200
    assert "event: complete" in replay_res.text
    assert "Phiên quét đã hoàn tất từ trước" in replay_res.text


def test_get_scan_not_found(client: TestClient) -> None:
    """Kiểm tra lấy kết quả quét với scan_id không tồn tại trả về 404."""
    response = client.get("/api/v1/scan/non-existent-uuid")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SCAN_NOT_FOUND"


def test_get_scan_pending(client: TestClient) -> None:
    """Kiểm tra lấy kết quả quét khi scan còn đang ở trạng thái pending."""
    # 1. Tạo scan mới (trạng thái pending)
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    assert create_res.status_code == 201
    scan_id = create_res.json()["scan_id"]

    # 2. Truy vấn kết quả ngay (chưa quét)
    get_res = client.get(f"/api/v1/scan/{scan_id}")
    assert get_res.status_code == 200
    data = get_res.json()

    assert data["scan_id"] == scan_id
    assert data["target_url"] == "https://example.com"
    assert data["status"] == "pending"
    assert data["total_findings"] == 0
    assert data["findings"] == []
    assert data["scoring"] is None
    assert data["completed_at"] is None


def test_get_scan_completed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra lấy kết quả quét đầy đủ sau khi stream quét hoàn tất."""
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

    stream_res = client.get(f"/api/v1/scan/{scan_id}/stream")
    assert stream_res.status_code == 200

    # 3. Lấy kết quả quét
    get_res = client.get(f"/api/v1/scan/{scan_id}")
    assert get_res.status_code == 200
    data = get_res.json()

    assert data["scan_id"] == scan_id
    assert data["status"] == "completed"
    assert data["total_findings"] > 0
    assert len(data["findings"]) > 0
    assert data["scoring"] is not None
    assert "score" in data["scoring"]
    assert "grade" in data["scoring"]
    assert data["completed_at"] is not None


def test_cancel_scan_endpoint_success(client: TestClient) -> None:
    """Kiểm tra gọi endpoint hủy phiên quét đang pending."""
    # 1. Tạo scan
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    assert create_res.status_code == 201
    scan_id = create_res.json()["scan_id"]

    # 2. Gọi POST /scan/{id}/cancel
    cancel_res = client.post(f"/api/v1/scan/{scan_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["scan_id"] == scan_id
    assert cancel_data["status"] == "cancelled"

    # 3. Lấy lại kết quả scan -> trạng thái phải là cancelled
    get_res = client.get(f"/api/v1/scan/{scan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "cancelled"


def test_cancel_scan_endpoint_not_found(client: TestClient) -> None:
    """Kiểm tra hủy scan không tồn tại trả về 404."""
    cancel_res = client.post("/api/v1/scan/non-existent-uuid/cancel")
    assert cancel_res.status_code == 404



