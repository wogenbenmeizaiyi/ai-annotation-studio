import time

from fastapi import HTTPException, status
from redis.exceptions import RedisError

from app.core.redis_client import redis_client


def enforce_rate_limit(scope: str, identifier: str, limit: int) -> None:
    bucket = int(time.time() // 60)
    key = f"auth:rate:{scope}:{identifier}:{bucket}"
    try:
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, 70)
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证限流服务不可用",
        ) from exc
    if current > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请求过于频繁")
