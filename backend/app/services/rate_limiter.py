# backend/app/services/rate_limiter.py
import redis.asyncio as aioredis
from datetime import datetime, timezone
from app.config import settings

MAX_DAILY_GENERATIONS = 10

async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)

async def check_generation_limit(user_id: str) -> tuple[bool, int]:
    """
    Returns (allowed: bool, remaining: int).
    Uses Redis INCR + EXPIRE with daily key.
    """
    r = await get_redis()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"gen_limit:{user_id}:{today}"

    count = await r.incr(key)
    if count == 1:
        # First generation today — set 24h expiry
        await r.expire(key, 86400)

    await r.aclose()

    if count > MAX_DAILY_GENERATIONS:
        return False, 0

    return True, MAX_DAILY_GENERATIONS - count

async def get_generation_count(user_id: str) -> int:
    """Get current generation count for today."""
    r = await get_redis()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"gen_limit:{user_id}:{today}"
    count = await r.get(key)
    await r.aclose()
    return int(count) if count else 0
