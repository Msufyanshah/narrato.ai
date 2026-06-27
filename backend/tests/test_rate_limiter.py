import sys
import os
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.rate_limiter import check_generation_limit, get_generation_count, get_redis

TEST_USER = 'rate-limit-test-999'

async def cleanup_redis():
    r = await get_redis()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await r.delete(f"gen_limit:{TEST_USER}:{today}")
    await r.aclose()

async def test():
    await cleanup_redis()
    try:
        # Test 1: First 10 calls allowed
        for i in range(10):
            allowed, remaining = await check_generation_limit(TEST_USER)
            assert allowed == True, f'Call {i+1} was blocked!'
            assert remaining == 10 - (i + 1)
        print('Test 1 PASS: first 10 calls allowed')

        # Test 2: 11th call is blocked
        allowed, remaining = await check_generation_limit(TEST_USER)
        assert allowed == False, '11th call should be blocked!'
        assert remaining == 0
        print('Test 2 PASS: 11th call blocked correctly')
    finally:
        await cleanup_redis()

if __name__ == "__main__":
    asyncio.run(test())
