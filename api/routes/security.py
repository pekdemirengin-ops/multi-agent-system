"""Guvenlik istatistikleri."""
from fastapi import APIRouter

from core.security import rate_limiter

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/rate-limit-stats")
async def rate_limit_stats():
    """Rate limiter istatistikleri."""
    return rate_limiter.stats()