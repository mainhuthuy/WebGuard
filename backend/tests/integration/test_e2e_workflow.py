"""End-to-End (E2E) integration tests for complete WebGuard user journeys and workflows."""

from typing import Any

from fastapi.testclient import TestClient
import pytest

from app.core import Settings
from app.main import create_application
from app.modules.base import BaseModule


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


def test_full_scan_lifecycle_e2e(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra toàn bộ luồng nghiệp vụ E2E:

    Root check -> Tạo Scan -> Stream SSE -> Lấy kết quả chi tiết ->
    Xuất JSON -> Xuất HTML -> Kiểm tra Lịch sử -> Kiểm tra Thống kê -> Xóa Scan.
    """
    # 1. Kiểm tra API gốc online
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert root_res.json()["status"] == "online"

    # 2. Tạo một phiên quét mới (POST /api/v1/scan)
    target_url = "https://e2e-workflow-target.com"
    create_res = client.post("/api/v1/scan", json={"url": target_url})
    assert create_res.status_code == 201
    scan_id = create_res.json()["scan_id"]
    assert create_res.json()["status"] == "pending"

    # 3. Mock Scanner.scan_stream để test chạy nhanh và ổn định
    from app.modules.scanner import Scanner

    async def mock_scan_stream(self: Any, url: str, scan_id: str) -> Any:
        yield {
            "event": "start",
            "scan_id": scan_id,
            "progress": 0,
            "message": "Start E2E scan",
            "module": None,
            "findings": [],
            "data": None,
        }
        mock_findings = [
            {
                "module": "headers",
                "name": "Missing CSP Header",
                "severity": "high",
                "description": "E2E simulated finding",
                "remediation": "Add CSP header",
                "url": url,
            }
        ]
        yield {
            "event": "complete",
            "scan_id": scan_id,
            "progress": 100,
            "message": "E2E scan completed",
            "module": None,
            "findings": mock_findings,
            "data": {
                "url": url,
                "total_findings": 1,
                "scoring": {"score": 85, "grade": "B", "total_findings": 1},
            },
        }

    monkeypatch.setattr(Scanner, "scan_stream", mock_scan_stream)


    # 4. Kết nối SSE Stream để chạy và nhận tiến trình (GET /api/v1/scan/{id}/stream)
    stream_res = client.get(f"/api/v1/scan/{scan_id}/stream")
    assert stream_res.status_code == 200
    assert "event: start" in stream_res.text
    assert "event: complete" in stream_res.text

    # 5. Lấy chi tiết kết quả quét (GET /api/v1/scan/{id})
    detail_res = client.get(f"/api/v1/scan/{scan_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["scan_id"] == scan_id
    assert detail_data["status"] == "completed"
    assert detail_data["total_findings"] > 0
    assert detail_data["scoring"] is not None
    assert detail_data["completed_at"] is not None

    # 6. Xuất báo cáo định dạng JSON (GET /api/v1/report/{id}/export?format=json)
    json_rep_res = client.get(f"/api/v1/report/{scan_id}/export?format=json")
    assert json_rep_res.status_code == 200
    json_rep_data = json_rep_res.json()
    assert json_rep_data["scan_id"] == scan_id
    assert json_rep_data["severity_counts"]["high"] > 0

    # 7. Xuất báo cáo định dạng HTML (GET /api/v1/report/{id}/export?format=html)
    html_rep_res = client.get(f"/api/v1/report/{scan_id}/export?format=html")
    assert html_rep_res.status_code == 200
    assert "text/html" in html_rep_res.headers["content-type"]
    assert "WebGuard" in html_rep_res.text
    assert scan_id in html_rep_res.text

    # 8. Kiểm tra phiên quét xuất hiện trong danh sách Lịch sử (GET /api/v1/history)
    history_res = client.get(f"/api/v1/history?search_url={target_url}")
    assert history_res.status_code == 200
    hist_data = history_res.json()
    assert hist_data["total"] >= 1
    found_item = next(
        (item for item in hist_data["items"] if item["id"] == scan_id), None
    )
    assert found_item is not None
    assert found_item["status"] == "completed"

    # 9. Kiểm tra Thống kê lịch sử (GET /api/v1/history/stats)
    stats_res = client.get("/api/v1/history/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_scans"] >= 1
    assert stats_res.json()["completed_scans"] >= 1

    # 10. Xóa phiên quét khỏi lịch sử (DELETE /api/v1/history/{id})
    del_res = client.delete(f"/api/v1/history/{scan_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 11. Kiểm tra scan_id đã bị xóa sạch (GET /api/v1/scan/{id} -> 404)
    after_del_res = client.get(f"/api/v1/scan/{scan_id}")
    assert after_del_res.status_code == 404


def test_scan_cancellation_workflow_e2e(client: TestClient) -> None:
    """Kiểm tra toàn bộ luồng hủy quét (Cancellation Flow):

    Tạo scan -> Hủy scan -> Kiểm tra trạng thái cancelled -> Không thể hủy lại ->
    Kiểm tra lịch sử hiển thị trạng thái cancelled.
    """
    # 1. Tạo scan
    create_res = client.post(
        "/api/v1/scan", json={"url": "https://cancel-test-target.org"}
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["scan_id"]

    # 2. Hủy phiên quét (POST /api/v1/scan/{id}/cancel)
    cancel_res = client.post(f"/api/v1/scan/{scan_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 3. Truy vấn trạng thái scan -> cancelled
    get_res = client.get(f"/api/v1/scan/{scan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "cancelled"

    # 4. Thử hủy lại lần nữa -> 400 Bad Request
    re_cancel_res = client.post(f"/api/v1/scan/{scan_id}/cancel")
    assert re_cancel_res.status_code == 400

    # 5. Kiểm tra trong lịch sử có trạng thái cancelled
    hist_res = client.get("/api/v1/history?status=cancelled")
    assert hist_res.status_code == 200
    assert any(item["id"] == scan_id for item in hist_res.json()["items"])


def test_api_validation_errors_e2e(client: TestClient) -> None:
    """Kiểm tra phản hồi chuẩn hóa HTTP 422 Unprocessable Content cho các input lỗi."""
    # 1. Body rỗng khi tạo scan
    res1 = client.post("/api/v1/scan", json={})
    assert res1.status_code == 422

    # 2. URL scheme sai (ftp://)
    res2 = client.post("/api/v1/scan", json={"url": "ftp://files.org"})
    assert res2.status_code == 422

    # 3. Export report với định dạng không hợp lệ (format=pdf)
    res3 = client.get("/api/v1/report/any-id/export?format=pdf")
    assert res3.status_code == 422

    # 4. Phân trang page = 0
    res4 = client.get("/api/v1/history?page=0")
    assert res4.status_code == 422

    # 5. Phân trang page_size > 100
    res5 = client.get("/api/v1/history?page_size=500")
    assert res5.status_code == 422


def test_health_check_integration(client: TestClient) -> None:
    """Kiểm tra endpoint /api/v1/health phản hồi trạng thái uptime và metrics."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "total_scans" in data

