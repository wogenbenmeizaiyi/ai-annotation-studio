import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import jwt
from fastapi import HTTPException, Request, WebSocket, status
from jwt import InvalidTokenError
from redis import Redis

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.image import ImageModel
from app.models.agent import AgentConfigProposalModel
from app.models.task import TaskModel
from app.models.train_task import TrainTaskModel


_redis = Redis.from_url(settings.AUTH_REDIS_URL, decode_responses=True)


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

    def can_manage(self, owner_subject_id: Optional[str]) -> bool:
        return self.is_super_admin or (
            owner_subject_id is not None and owner_subject_id == self.subject_id
        )


def _decode_token(token: str) -> dict:
    public_key = Path(settings.AUTH_PUBLIC_KEY_PATH).expanduser().read_bytes()
    return jwt.decode(
        token,
        public_key,
        algorithms=["EdDSA"],
        audience=settings.AUTH_AUDIENCE,
        issuer=settings.AUTH_ISSUER,
        options={"require": ["sub", "sid", "ver", "csrf", "exp", "iat"]},
    )


def _validate_token(token: str) -> AuthContext:
    try:
        claims = _decode_token(token)
    except (InvalidTokenError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态无效") from exc
    raw_state = _redis.get(f"auth:user:{claims['sub']}")
    if not raw_state:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户状态不可用")
    state = json.loads(raw_state)
    if state.get("status") != "active" or int(state.get("token_version", 0)) != int(
        claims["ver"]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已撤销")
    if _redis.exists(f"auth:revoked:{claims['sid']}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已撤销")
    if claims.get("must_change_password"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="请先修改密码")
    return AuthContext(
        subject_id=str(claims["sub"]),
        username=str(claims.get("username", "")),
        role=str(state.get("role", claims.get("role", "user"))),
        session_id=str(claims["sid"]),
        csrf=str(claims["csrf"]),
    )


def authenticate_request(request: Request) -> AuthContext:
    token = request.cookies.get(settings.AUTH_ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    context = _validate_token(token)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        header = request.headers.get("X-CSRF-Token", "")
        cookie = request.cookies.get(settings.AUTH_CSRF_COOKIE, "")
        if not (
            header
            and cookie
            and secrets.compare_digest(header, cookie)
            and secrets.compare_digest(header, context.csrf)
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF 校验失败")
    return context


def get_request_auth(request: Request) -> AuthContext:
    context = getattr(request.state, "auth", None)
    if not isinstance(context, AuthContext):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return context


def authenticate_websocket(websocket: WebSocket) -> AuthContext:
    token = websocket.cookies.get(settings.AUTH_ACCESS_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return _validate_token(token)


def require_task_manager(task_name: str, context: AuthContext) -> TaskModel:
    db = SessionLocal()
    try:
        task = (
            db.query(TaskModel)
            .filter(TaskModel.name == task_name, TaskModel.is_deleted.is_(False))
            .first()
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        if not context.can_manage(task.owner_subject_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该任务")
        db.expunge(task)
        return task
    finally:
        db.close()


def require_image_manager(image_id: int, context: AuthContext) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(ImageModel, TaskModel)
            .join(TaskModel, ImageModel.task_id == TaskModel.id)
            .filter(ImageModel.id == image_id, ImageModel.is_deleted.is_(False))
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
        if not context.can_manage(row[1].owner_subject_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该图片")
    finally:
        db.close()


def require_s3_key_manager(s3_key: str, context: AuthContext) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(ImageModel, TaskModel)
            .join(TaskModel, ImageModel.task_id == TaskModel.id)
            .filter(ImageModel.s3_key == s3_key, ImageModel.is_deleted.is_(False))
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
        if not context.can_manage(row[1].owner_subject_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该图片")
    finally:
        db.close()


def require_train_manager(train_task_id: int, context: AuthContext) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(TrainTaskModel, TaskModel)
            .join(TaskModel, TrainTaskModel.task_id == TaskModel.id)
            .filter(TrainTaskModel.id == train_task_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="训练任务不存在")
        if not context.can_manage(row[1].owner_subject_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该训练任务")
    finally:
        db.close()


def require_proposal_manager(proposal_id: str, context: AuthContext) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(AgentConfigProposalModel, TaskModel)
            .join(TaskModel, AgentConfigProposalModel.task_id == TaskModel.id)
            .filter(AgentConfigProposalModel.id == proposal_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="训练草案不存在")
        if not context.can_manage(row[1].owner_subject_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该训练草案")
    finally:
        db.close()
