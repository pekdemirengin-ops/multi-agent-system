"""Web Scraping Skill - URL'den icerik cekme."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import structlog

from skills.base_skill import BaseSkill, skill_registry

logger = structlog.get_logger(__name__)


class WebScrapingSkill(BaseSkill):
    """URL'den icerik ceker ve metin cikarir."""

    name = "web_scraping"
    description = "URL'den icerik ceker (HTML -> metin)"

    # Izin verilen domainler (guvenlik)
    ALLOWED_SCHEMES = {"http", "https"}

    # Maksimum icerik uzunlugu
    MAX_CONTENT_LENGTH = 10000

    def _extract_url(self, text: str) -> str | None:
        """Metinden URL cikarir."""
        # http/https URL pattern
        pattern = r'https?://[^\s<>"\')\]]+'
        matches = re.findall(pattern, text)
        if matches:
            # En uzun URL'i al
            return max(matches, key=len)
        return None

    def _validate_url(self, url: str) -> tuple[bool, str]:
        """URL guvenli mi kontrol eder."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in self.ALLOWED_SCHEMES:
                return False, f"Desteklenmeyen scheme: {parsed.scheme}"
            if not parsed.netloc:
                return False, "Gecersiz URL (domain yok)"
            return True, ""
        except Exception as e:
            return False, str(e)

    async def fetch_html(self, url: str, timeout: int = 10) -> str:
        """URL'den HTML ceker."""
        import httpx

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MultiAgentBot/1.0)"
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def extract_text(self, html: str) -> str:
        """HTML'den metin cikarir."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            # Fallback: regex ile temizle
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()[: self.MAX_CONTENT_LENGTH]

        soup = BeautifulSoup(html, "html.parser")

        # Script ve style'lari kaldir
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Ana icerik
        text = soup.get_text(separator=" ", strip=True)

        # Fazla bosluklari temizle
        text = re.sub(r"\s+", " ", text)
        return text.strip()[: self.MAX_CONTENT_LENGTH]

    async def execute(self, url: str = "", text: str = "", **kwargs) -> dict[str, Any]:
        """URL'den icerik ceker."""
        # URL'yi bul
        target_url = url or self._extract_url(text)
        if not target_url:
            return {"error": "URL bulunamadi"}

        # Guvenlik kontrolu
        is_valid, err = self._validate_url(target_url)
        if not is_valid:
            return {"error": f"Gecersiz URL: {err}"}

        try:
            logger.info("web_scraping.fetch", url=target_url[:100])
            html = await self.fetch_html(target_url)

            if not html:
                return {"error": "HTML bos"}

            content = self.extract_text(html)

            return {
                "url": target_url,
                "content": content,
                "content_length": len(content),
                "html_length": len(html),
            }

        except Exception as e:
            logger.exception("web_scraping.error", url=target_url[:100], error=str(e))
            return {"error": f"Icerik cekilemedi: {str(e)}"}


# Kayit
skill_registry.register(WebScrapingSkill())
