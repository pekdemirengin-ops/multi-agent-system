"""Streaming endpoint testleri."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestStreamingEndpoint:
    def test_stream_requires_auth(self, client: TestClient) -> None:
        # Token'siz istek
        response = client.post(
            "/api/stream",
            json={"message": "Merhaba", "user_id": "test"},
        )
        # 401 dondurmeli (auth gerekli)
        assert response.status_code in (401, 403, 422)

    def test_stream_validates_message(self, client: TestClient) -> None:
        # Login
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        # Bos mesaj
        response = client.post(
            "/api/stream",
            json={"message": "", "user_id": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # 422 (Pydantic) veya 400
        assert response.status_code in (400, 422)

    def test_stream_response_format(self, client: TestClient) -> None:
        login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login.json()["access_token"]

        response = client.post(
            "/api/stream",
            json={"message": "Merhaba", "user_id": "test_stream"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # SSE formati
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")