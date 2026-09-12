"""Integration tests for FastAPI application core configuration."""

from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest

from app.core import ScanNotFoundException, Settings
from app.main import create_application


class SamplePayload(BaseModel):
    """Model mẫu dùng để test lỗi validation dữ liệu."""
    target_url: str
    timeout: int


@pytest.fixture
def client() -> TestClient:
    """Khởi tạo TestClient với môi trường testing và các route giả lập để test lỗi."""
    settings = Settings(
        ENV="testing",
        DEBUG=True,
        CORS_ORIGINS=["http://localhost:5173"],
        _env_file=None,
    )
    test_app = create_application(settings=settings)

    # Thêm các route đặc biệt phục vụ việc test exception handlers
    @test_app.get("/test/custom-error")
    async def trigger_custom_error() -> None:
        raise ScanNotFoundException("scan_test_123")

    @test_app.post("/test/validation-error")
    async def trigger_validation_error(payload: SamplePayload) -> dict[str, str]:
        return {"target": payload.target_url}

    @test_app.get("/test/unhandled-error")
    async def trigger_unhandled_error() -> None:
        raise RuntimeError("Lỗi bất ngờ xảy ra trong server!")

    return TestClient(test_app, raise_server_exceptions=False)


def test_root_endpoint(client: TestClient) -> None:
    """Kiểm tra endpoint gốc và sự hiện diện của các header đo đạc."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "WebGuard API"
    assert data["status"] == "online"
    # Kiểm tra middleware có gắn đúng 2 header không
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_health_check_endpoint(client: TestClient) -> None:
    """Kiểm tra health check trả về đúng metadata môi trường."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "webguard-backend"
    assert data["environment"] == "testing"


def test_cors_headers(client: TestClient) -> None:
    """Kiểm tra CORS preflight (OPTIONS) phản hồi đúng origin được phép."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_request_id_propagation(client: TestClient) -> None:
    """Kiểm tra nếu client tự gửi X-Request-ID lên thì server phải giữ nguyên mã đó."""
    custom_id = "custom-trace-uuid-1234"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_custom_exception_handler(client: TestClient) -> None:
    """Kiểm tra WebGuardException trả về JSON chuẩn đồng nhất."""
    response = client.get("/test/custom-error")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SCAN_NOT_FOUND"
    assert "scan_test_123" in body["error"]["message"]
    assert body["error"]["details"] == {"scan_id": "scan_test_123"}


def test_validation_exception_handler(client: TestClient) -> None:
    """Kiểm tra khi gửi sai kiểu dữ liệu (timeout='abc' thay vì số) trả về HTTP 422."""
    response = client.post("/test/validation-error", json={"target_url": "https://example.com", "timeout": "not-an-int"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


def test_http_404_handler(client: TestClient) -> None:
    """Kiểm tra gọi route không tồn tại trả về đúng format JSON lỗi."""
    response = client.get("/duong-dan-khong-ton-tai")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_404"


def test_unhandled_exception_handler(client: TestClient) -> None:
    """Kiểm tra khi server gặp crash 500 vẫn trả về JSON lịch sự, không sập app."""
    response = client.get("/test/unhandled-error")
    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
