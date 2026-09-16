"""Guvenlik modulu - rate limiting, input validation."""
from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ============================================================
# Input Validation
# ============================================================

# Maksimum mesaj uzunlugu
MAX_MESSAGE_LENGTH = 2000
MIN_MESSAGE_LENGTH = 1

# Yasakli pattern'ler (basit prompt injection / zararli denemeler)
FORBIDDEN_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?previous",
    r"system\s*:\s*you\s+are",
    r"<script[^>]*>.*?</script>",
    r"javascript\s*:",
    r"data\s*:\s*text/html",
    r"\$\{.*\}",  # template injection
    r"\.\./\.\./",  # path traversal
]


def validate_message(message: str) -> tuple[bool, str]:
    """Mesaji dogrular. (gecerli_mi, hata_mesaji) doner."""
    if not message or not message.strip():
        return False, "Mesaj bos olamaz"

    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Mesaj cok uzun (max {MAX_MESSAGE_LENGTH} karakter)"

    if len(message) < MIN_MESSAGE_LENGTH:
        return False, "Mesaj cok kisa"

    # Yasakli pattern kontrolu
    lower_msg = message.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, lower_msg, re.IGNORECASE):
            logger.warning("security.forbidden_pattern", pattern=pattern[:30])
            return False, "Mesaj guvenlik nedeniyle reddedildi"

    return True, "OK"


def validate_user_id(user_id: str) -> tuple[bool, str]:
    """Kullanici ID'sini dogrular."""
    if not user_id:
        return False, "user_id bos olamaz"

    if len(user_id) > 100:
        return False, "user_id cok uzun"

    # Sadece harf, rakam, tire, alt cizgi
    if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", user_id):
        return False, "user_id sadece harf, rakam, _-.@ icerebilir"

    return True, "OK"


def sanitize_output(text: str) -> str:
    """Ciktiyi temizle (HTML injection engelle)."""
    if not text:
        return text
    # HTML tag'lerini escape et
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text


# ============================================================
# Rate Limiting (basit in-memory)
# ============================================================

class RateLimiter:
    """Basit in-memory rate limiter (IP bazli)."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str) -> tuple[bool, int]:
        """Rate limit kontrolu.

        Returns:
            (izin_var_mi, kalan_hak)
        """
        import time

        now = time.time()
        window_start = now - self.window_seconds

        # Eski kayitlari temizle
        if key in self._requests:
            self._requests[key] = [
                t for t in self._requests[key] if t > window_start
            ]
        else:
            self._requests[key] = []

        # Limit kontrolu
        if len(self._requests[key]) >= self.max_requests:
            logger.warning("security.rate_limit_exceeded", key=key)
            return False, 0

        # Yeni istek ekle
        self._requests[key].append(now)
        return True, self.max_requests - len(self._requests[key])

    def reset(self, key: str) -> None:
        self._requests.pop(key, None)

    def stats(self) -> dict[str, Any]:
        return {
            "total_keys": len(self._requests),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
        }


# Global rate limiter (30 istek / 60 saniye)
rate_limiter = RateLimiter(max_requests=30, window_seconds=60)