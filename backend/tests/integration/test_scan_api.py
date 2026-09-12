"""Integration tests for Scan API endpoints."""

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
