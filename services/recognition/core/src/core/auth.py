import json
import secrets
from dataclasses import dataclass
from pathlib import Path

import jwt
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError
from redis import Redis

from core.config import config


_redis = Redis.from_url(config.AUTH_STATE_REDIS_URL, decode_responses=True)


@dataclass(frozen=True)
class AuthContext:
    subject_id: str
    username: str
    role: str
    session_id: str
    csrf: str

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"

    def can_manage(self, owner_subject_id: str | None) -> bool:
        return self.is_super_admin or owner_subject_id == self.subject_id


def _decode_token(token: str) -> dict:
    public_key = Path(config.AUTH_PUBLIC_KEY_PATH).expanduser().read_bytes()
    return jwt.decode(
        token,
        public_key,
        algorithms=["EdDSA"],
        audience=config.AUTH_AUDIENCE,
        issuer=config.AUTH_ISSUER,
        options={"require": ["sub", "sid", "ver", "csrf", "exp", "iat"]},
    )


def authenticate_request(request: Request) -> AuthContext:
    token = request.cookies.get(config.AUTH_ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        claims = _decode_token(token)
        raw_state = _redis.get(f"auth:user:{claims['sub']}")
    except (InvalidTokenError, OSError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效",
        ) from exc
    if not raw_state:
        raise HTTPException(status_code=401, detail="用户状态不可用")
    state = json.loads(raw_state)
    if state.get("status") != "active" or int(state.get("token_version", 0)) != int(
        claims["ver"]
    ):
        raise HTTPException(status_code=401, detail="登录状态已撤销")
    if _redis.exists(f"auth:revoked:{claims['sid']}"):
        raise HTTPException(status_code=401, detail="登录状态已撤销")
    if claims.get("must_change_password"):
        raise HTTPException(status_code=403, detail="请先修改密码")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        header = request.headers.get("X-CSRF-Token", "")
        cookie = request.cookies.get(config.AUTH_CSRF_COOKIE, "")
        if not (
            header
            and cookie
            and secrets.compare_digest(header, cookie)
            and secrets.compare_digest(header, str(claims["csrf"]))
        ):
            raise HTTPException(status_code=403, detail="CSRF 校验失败")
    return AuthContext(
        subject_id=str(claims["sub"]),
        username=str(claims.get("username", "")),
        role=str(state.get("role", claims.get("role", "user"))),
        session_id=str(claims["sid"]),
        csrf=str(claims["csrf"]),
    )


def get_request_auth(request: Request) -> AuthContext:
    context = getattr(request.state, "auth", None)
    if not isinstance(context, AuthContext):
        raise HTTPException(status_code=401, detail="未登录")
    return context


def require_owner(context: AuthContext, owner_subject_id: str | None) -> None:
    if not context.can_manage(owner_subject_id):
        raise HTTPException(status_code=403, detail="无权修改该资源")
