"""Tools testleri."""
from __future__ import annotations

from unittest.mock import patch

from tools.web_search import format_results


class TestWebSearch:
    def test_format_empty(self) -> None:
        result = format_results([])
        assert "bulunamadi" in result.lower() or "sonuc" in result.lower()

    def test_format_with_results(self) -> None:
        results = [
            {"title": "Test 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
            {"title": "Test 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
        ]
        formatted = format_results(results)
        assert "Test 1" in formatted
        assert "https://example.com/1" in formatted
        assert "Test 2" in formatted

    @patch("tools.web_search.DDGS")
    def test_search_returns_list(self, mock_ddgs: object) -> None:
        from tools.web_search import search

        mock_instance = mock_ddgs.return_value.__enter__.return_value  # type: ignore[attr-defined]
        mock_instance.text.return_value = [
            {"title": "T", "href": "https://x.com", "body": "B"}
        ]

        result = search("test", max_results=1)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "T"
        assert result[0]["url"] == "https://x.com"


class TestConfig:
    def test_settings_defaults(self) -> None:
        from core.config import Settings

        s = Settings(
            app_env="test",
            redis_url="redis://test:6379/0",
            use_redis_bus=False,
        )
        assert s.app_env == "test"
        assert s.redis_url == "redis://test:6379/0"
        assert s.use_redis_bus is False