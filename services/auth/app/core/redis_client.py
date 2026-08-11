import json
from typing import Any

from redis import Redis

from app.core.config import settings
from app.models.user import User


redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


def user_state_key(user_id: str) -> str:
    return f"auth:user:{user_id}"


def revoked_session_key(session_id: str) -> str:
    return f"auth:revoked:{session_id}"


def sync_user_state(user: User) -> None:
    payload = {
        "status": user.status,
        "role": user.role,
        "token_version": user.token_version,
    }
    redis_client.set(user_state_key(user.id), json.dumps(payload), ex=8 * 24 * 60 * 60)


def load_user_state(user_id: str) -> dict[str, Any] | None:
    raw = redis_client.get(user_state_key(user_id))
    return json.loads(raw) if raw else None


def revoke_session(session_id: str, ttl_seconds: int) -> None:
    redis_client.set(revoked_session_key(session_id), "1", ex=max(1, ttl_seconds))
