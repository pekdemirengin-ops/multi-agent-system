"""Tools testleri - Tavily API."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestWebSearch:
    def test_format_empty(self) -> None:
        from tools.web_search import format_results
        assert format_results([]) == "Sonuc bulunamadi."

    def test_format_with_results(self) -> None:
        from tools.web_search import format_results
        results = [
            {"title": "Test 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
            {"title": "Test 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
        ]
        formatted = format_results(results)
        assert "Test 1" in formatted
        assert "Snippet 1" in formatted
        assert "https://example.com/1" in formatted

    def test_search_returns_list(self) -> None:
        with patch("tavily.TavilyClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {
                "results": [
                    {"title": "T1", "url": "https://example.com", "content": "C1", "score": 0.9},
                    {"title": "T2", "url": "https://example2.com", "content": "C2", "score": 0.8},
                ],
                "answer": "",
            }
            mock_client.return_value = mock_instance

            from tools.web_search import search
            results = search("test query", max_results=2)
            assert isinstance(results, list)
            assert len(results) == 2


class TestConfig:
    def test_settings_defaults(self) -> None:
        from core.config import get_settings
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "api_port")
        assert settings.api_port > 0
