import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_client import redis_client, sync_user_state
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User


@dataclass(frozen=True)
class AuthenticatedUser:
    model: User
    claims: dict


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    token = request.cookies.get(settings.ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        claims = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效"
        ) from exc

    user = db.query(User).filter(User.id == claims["sub"]).first()
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")
    if user.token_version != int(claims["ver"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已撤销")
    if redis_client.exists(f"auth:revoked:{claims['sid']}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已撤销")
    sync_user_state(user)
    return AuthenticatedUser(model=user, claims=claims)


def require_csrf(request: Request, current: AuthenticatedUser) -> None:
    header_token = request.headers.get("X-CSRF-Token", "")
    cookie_token = request.cookies.get(settings.CSRF_COOKIE, "")
    claim_token = str(current.claims.get("csrf", ""))
    if not (
        header_token
        and cookie_token
        and secrets.compare_digest(header_token, cookie_token)
        and secrets.compare_digest(header_token, claim_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF 校验失败")


def get_super_admin(
    current: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current.model.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    return current
