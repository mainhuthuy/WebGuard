"""Integration tests for History API endpoints."""

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


def test_list_history_endpoint(client: TestClient) -> None:
    """Kiểm tra gọi GET /api/v1/history trả về danh sách có cấu trúc phân trang chuẩn."""
    # 1. Tạo một scan mới
    create_res = client.post("/api/v1/scan", json={"url": "https://history-test.com"})
    assert create_res.status_code == 201
    scan_id = create_res.json()["scan_id"]

    # 2. Lấy danh sách lịch sử
    res = client.get("/api/v1/history?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()

    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] >= 1

    # Kiểm tra item chứa scan vừa tạo
    found = any(item["id"] == scan_id for item in data["items"])
    assert found is True


def test_list_history_with_search_filter(client: TestClient) -> None:
    """Kiểm tra lọc lịch sử theo từ khóa URL."""
    unique_domain = "https://unique-filter-keyword.org"
    client.post("/api/v1/scan", json={"url": unique_domain})

    res = client.get("/api/v1/history?search_url=unique-filter-keyword")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any("unique-filter-keyword" in item["target_url"] for item in data["items"])


def test_get_history_stats_endpoint(client: TestClient) -> None:
    """Kiểm tra gọi GET /api/v1/history/stats trả về báo cáo số liệu."""
    res = client.get("/api/v1/history/stats")
    assert res.status_code == 200
    data = res.json()

    assert "total_scans" in data
    assert "completed_scans" in data
    assert "failed_scans" in data
    assert "cancelled_scans" in data
    assert "grade_distribution" in data
    assert isinstance(data["grade_distribution"], dict)


def test_delete_history_item_endpoint(client: TestClient) -> None:
    """Kiểm tra xóa một bản ghi lịch sử qua DELETE /api/v1/history/{id}."""
    create_res = client.post("/api/v1/scan", json={"url": "https://to-be-deleted.com"})
    scan_id = create_res.json()["scan_id"]

    # Xóa thành công
    del_res = client.delete(f"/api/v1/history/{scan_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Xóa lần 2 trả về 404
    del_res_404 = client.delete(f"/api/v1/history/{scan_id}")
    assert del_res_404.status_code == 404


def test_clear_history_endpoint(client: TestClient) -> None:
    """Kiểm tra dọn dẹp lịch sử qua DELETE /api/v1/history."""
    res = client.delete("/api/v1/history")
    assert res.status_code == 200
    assert res.json()["deleted"] is True


def test_history_items_include_mode(client: TestClient) -> None:
    """Danh sách lịch sử trả về mode của từng phiên quét."""
    created = client.post(
        "/api/v1/scan", json={"url": "https://history-mode.example.com", "mode": "quick"}
    ).json()
    items = client.get(
        "/api/v1/history", params={"search_url": "history-mode.example.com"}
    ).json()["items"]
    match = next(i for i in items if i["id"] == created["scan_id"])
    assert match["mode"] == "quick"
