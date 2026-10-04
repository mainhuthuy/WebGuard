"""Integration tests for POST /scan/{id}/explain (BYOK AI explain endpoint)."""

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core import Settings
from app.main import create_application


@pytest.fixture
def client() -> TestClient:
    settings = Settings(ENV="testing", DEBUG=True, _env_file=None)
    return TestClient(create_application(settings=settings), raise_server_exceptions=False)


def _completed_scan_id(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> str:
    """Tạo 1 scan và chạy cho hoàn tất (mock modules để không gọi mạng thật)."""

    async def mock_scan(self: Any, url: str) -> list[dict[str, Any]]:
        return [{
            "module": "headers",
            "name": "content-security-policy",
            "severity": "high",
            "description": "Thiếu CSP",
            "remediation": "Thêm header CSP",
            "url": url,
        }]

    from app.modules.base import BaseModule
    monkeypatch.setattr(BaseModule, "scan", mock_scan)

    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    scan_id = create_res.json()["scan_id"]
    client.get(f"/api/v1/scan/{scan_id}/stream")
    return scan_id


def _ok_openai_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": "## Plan\nFix the CSP header first."}}]},
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )


def test_explain_scan_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/v1/scan/non-existent-uuid/explain",
        json={"provider": "openai", "api_key": "sk-fake-key-123"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"


def test_explain_scan_not_completed_yet(client: TestClient) -> None:
    create_res = client.post("/api/v1/scan", json={"url": "https://example.com"})
    scan_id = create_res.json()["scan_id"]

    response = client.post(
        f"/api/v1/scan/{scan_id}/explain",
        json={"provider": "openai", "api_key": "sk-fake-key-123"},
    )
    assert response.status_code == 400
    assert "chưa hoàn tất" in response.json()["error"]["message"]


def test_explain_scan_rejects_unsupported_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_id = _completed_scan_id(client, monkeypatch)
    response = client.post(
        f"/api/v1/scan/{scan_id}/explain",
        json={"provider": "mystery-ai", "api_key": "sk-fake-key-123"},
    )
    assert response.status_code == 422  # Pydantic Enum validation


def test_explain_scan_rejects_too_short_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_id = _completed_scan_id(client, monkeypatch)
    response = client.post(
        f"/api/v1/scan/{scan_id}/explain",
        json={"provider": "openai", "api_key": "x"},
    )
    assert response.status_code == 422


def test_explain_scan_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_id = _completed_scan_id(client, monkeypatch)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok_openai_response()
        response = client.post(
            f"/api/v1/scan/{scan_id}/explain",
            json={"provider": "openai", "api_key": "sk-fake-key-123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o-mini"
    assert "Fix the CSP header" in data["explanation"]
    # API key chỉ được dùng để gọi provider, không bao giờ xuất hiện trong response về client
    assert "sk-fake-key-123" not in response.text


def test_explain_scan_invalid_api_key_is_passed_through_as_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_id = _completed_scan_id(client, monkeypatch)
    bad_key_response = httpx.Response(
        401,
        json={"error": {"message": "Incorrect API key provided"}},
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = bad_key_response
        response = client.post(
            f"/api/v1/scan/{scan_id}/explain",
            json={"provider": "openai", "api_key": "sk-wrong-key-000"},
        )

    assert response.status_code == 401
    assert "sk-wrong-key-000" not in response.text


def test_explain_scan_with_custom_model(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_id = _completed_scan_id(client, monkeypatch)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _ok_openai_response()
        response = client.post(
            f"/api/v1/scan/{scan_id}/explain",
            json={"provider": "openai", "api_key": "sk-fake-key-123", "model": "gpt-4o"},
        )
    assert response.status_code == 200
    assert response.json()["model"] == "gpt-4o"
