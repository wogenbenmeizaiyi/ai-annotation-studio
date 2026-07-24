import math
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_super_admin,
    require_csrf,
)
from app.core.rate_limit import enforce_rate_limit
from app.core.redis_client import revoke_session, sync_user_state
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    get_jwks,
    hash_password,
    hash_refresh_token,
    new_csrf_token,
    new_refresh_token,
    normalize_username,
    verify_password,
)
from app.db.database import get_db
from app.models.user import AuditLog, RefreshSession, User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RegisterRequest,
    RoleUpdateRequest,
    UserPageResponse,
    UserResponse,
)


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _response(data=None, message: str = "success", code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def _serialize_user(user: User) -> dict:
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_platform_owner=user.is_platform_owner,
        status=user.status,
        must_change_password=user.must_change_password,
        created_at=user.created_at.isoformat(),
        approved_at=user.approved_at.isoformat() if user.approved_at else None,
    ).model_dump()


def _audit(
    db: Session,
    request: Request,
    action: str,
    actor_id: str | None = None,
    target_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            detail=detail,
            ip_address=_client_ip(request),
        )
    )


def _set_session_cookies(
    response: Response,
    user: User,
    session: RefreshSession,
    refresh_token: str,
    csrf_token: str,
) -> None:
    access_token, access_max_age = create_access_token(user, session.id, csrf_token)
    refresh_max_age = settings.AUTH_REFRESH_TOKEN_DAYS * 24 * 60 * 60
    response.set_cookie(
        settings.ACCESS_COOKIE,
        access_token,
        max_age=access_max_age,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        settings.REFRESH_COOKIE,
        refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="strict",
        path="/api/auth",
    )
    response.set_cookie(
        settings.CSRF_COOKIE,
        csrf_token,
        max_age=refresh_max_age,
        httponly=False,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_COOKIE, path="/")
    response.delete_cookie(settings.REFRESH_COOKIE, path="/api/auth")
    response.delete_cookie(settings.CSRF_COOKIE, path="/")


def _create_session(db: Session, request: Request, user: User) -> tuple[RefreshSession, str]:
    refresh_token = new_refresh_token()
    session = RefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=_now() + timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS),
        user_agent=request.headers.get("User-Agent", "")[:512],
        ip_address=_client_ip(request),
    )
    db.add(session)
    db.flush()
    return session, refresh_token


def _revoke_all_sessions(db: Session, user_id: str) -> None:
    sessions = (
        db.query(RefreshSession)
        .filter(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .all()
    )
    revoked_at = _now()
    for session in sessions:
        session.revoked_at = revoked_at
        revoke_session(session.id, settings.AUTH_ACCESS_TOKEN_MINUTES * 60)


def _get_user_or_404(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


def _ensure_admin_survives(db: Session, target: User) -> None:
    if target.role != "super_admin" or target.status != "active":
        return
    active_admins = (
        db.query(User).filter(User.role == "super_admin", User.status == "active").count()
    )
    if active_admins <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="不能禁用或降级最后一个有效超级管理员",
        )


def _ensure_account_action_allowed(
    current: AuthenticatedUser,
    target: User,
    *,
    operation: str,
) -> None:
    if target.is_platform_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="平台所有者账号受保护，请由所有者本人修改密码",
        )
    if current.model.is_platform_owner:
        return
    if operation == "role" or target.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有平台所有者可以管理超级管理员",
        )


@router.get("/.well-known/jwks.json")
def jwks() -> dict:
    return get_jwks()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    enforce_rate_limit("register", _client_ip(request), 10)
    normalized = normalize_username(payload.username)
    if db.query(User).filter(User.username_normalized == normalized).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    user = User(
        username=payload.username.strip(),
        username_normalized=normalized,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role="user",
        status="pending",
    )
    db.add(user)
    db.flush()
    _audit(db, request, "user.register", target_id=user.id)
    db.commit()
    sync_user_state(user)
    return _response(_serialize_user(user), "注册成功，等待超级管理员审批", 201)


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    normalized = normalize_username(payload.username)
    enforce_rate_limit("login-ip", _client_ip(request), 30)
    enforce_rate_limit("login-user", normalized, 10)
    user = db.query(User).filter(User.username_normalized == normalized).first()
    stored_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, stored_hash)
    if user is None or not password_valid:
        _audit(db, request, "user.login_failed", target_id=normalized)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status == "pending":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号等待审批")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    session, refresh_token = _create_session(db, request, user)
    csrf_token = new_csrf_token()
    _audit(db, request, "user.login", actor_id=user.id, target_id=session.id)
    db.commit()
    sync_user_state(user)
    _set_session_cookies(response, user, session, refresh_token, csrf_token)
    return _response(_serialize_user(user))


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE, "")
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE, "")
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if not refresh_token or not csrf_cookie or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭据无效")
    session = (
        db.query(RefreshSession)
        .filter(RefreshSession.token_hash == hash_refresh_token(refresh_token))
        .first()
    )
    if session is None or session.revoked_at is not None or session.expires_at <= _now():
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭据已失效")
    user = session.user
    if user.status != "active":
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")

    session.revoked_at = _now()
    revoke_session(session.id, settings.AUTH_ACCESS_TOKEN_MINUTES * 60)
    new_session, new_token = _create_session(db, request, user)
    new_csrf = new_csrf_token()
    _audit(db, request, "user.refresh", actor_id=user.id, target_id=new_session.id)
    db.commit()
    sync_user_state(user)
    _set_session_cookies(response, user, new_session, new_token, new_csrf)
    return _response(_serialize_user(user))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE, "")
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if csrf_cookie and not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF 校验失败")
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE, "")
    if refresh_token:
        session = (
            db.query(RefreshSession)
            .filter(RefreshSession.token_hash == hash_refresh_token(refresh_token))
            .first()
        )
        if session and session.revoked_at is None:
            session.revoked_at = _now()
            revoke_session(session.id, settings.AUTH_ACCESS_TOKEN_MINUTES * 60)
            _audit(db, request, "user.logout", actor_id=session.user_id, target_id=session.id)
            db.commit()
    _clear_session_cookies(response)
    return _response(message="已退出登录")


@router.get("/me")
def me(current: AuthenticatedUser = Depends(get_current_user)) -> dict:
    return _response(_serialize_user(current.model))


@router.patch("/me/password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request, current)
    if not verify_password(payload.current_password, current.model.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误")
    current.model.password_hash = hash_password(payload.new_password)
    current.model.must_change_password = False
    current.model.token_version += 1
    _revoke_all_sessions(db, current.model.id)
    _audit(db, request, "user.password_changed", actor_id=current.model.id)
    db.commit()
    sync_user_state(current.model)
    return _response(message="密码已修改，请重新登录")


@router.get("/admin/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    _: AuthenticatedUser = Depends(get_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(User)
    if status_filter:
        query = query.filter(User.status == status_filter)
    total = query.count()
    users = (
        query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    data = UserPageResponse(
        items=[UserResponse(**_serialize_user(user)) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    ).model_dump()
    return _response(data)


def _apply_status_change(
    user_id: str,
    new_status: str,
    action: str,
    request: Request,
    current: AuthenticatedUser,
    db: Session,
) -> dict:
    require_csrf(request, current)
    target = _get_user_or_404(db, user_id)
    _ensure_account_action_allowed(current, target, operation="status")
    if new_status == "disabled":
        _ensure_admin_survives(db, target)
    target.status = new_status
    target.approved_at = _now() if new_status == "active" else target.approved_at
    target.approved_by = current.model.id if new_status == "active" else target.approved_by
    target.token_version += 1
    _revoke_all_sessions(db, target.id)
    _audit(db, request, action, actor_id=current.model.id, target_id=target.id)
    db.commit()
    sync_user_state(target)
    return _response(_serialize_user(target))


@router.post("/admin/users/{user_id}/approve")
def approve_user(
    user_id: str,
    request: Request,
    current: AuthenticatedUser = Depends(get_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    return _apply_status_change(user_id, "active", "user.approved", request, current, db)


@router.post("/admin/users/{user_id}/disable")
def disable_user(
    user_id: str,
    request: Request,
    current: AuthenticatedUser = Depends(get_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    return _apply_status_change(user_id, "disabled", "user.disabled", request, current, db)


@router.post("/admin/users/{user_id}/enable")
def enable_user(
    user_id: str,
    request: Request,
    current: AuthenticatedUser = Depends(get_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    return _apply_status_change(user_id, "active", "user.enabled", request, current, db)


@router.put("/admin/users/{user_id}/role")
def update_role(
    user_id: str,
    payload: RoleUpdateRequest,
    request: Request,
    current: AuthenticatedUser = Depends(get_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request, current)
    if payload.role not in {"super_admin", "user"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="角色无效")
    target = _get_user_or_404(db, user_id)
    _ensure_account_action_allowed(current, target, operation="role")
    if target.role == "super_admin" and payload.role != "super_admin":
        _ensure_admin_survives(db, target)
    target.role = payload.role
    target.token_version += 1
    _revoke_all_sessions(db, target.id)
    _audit(db, request, "user.role_changed", current.model.id, target.id, payload.role)
    db.commit()
    sync_user_state(target)
    return _response(_serialize_user(target))


@router.post("/admin/users/{user_id}/reset-password")
def reset_password(
    user_id: str,
    payload: PasswordResetRequest,
    request: Request,
    current: AuthenticatedUser = Depends(get_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_csrf(request, current)
    target = _get_user_or_404(db, user_id)
    _ensure_account_action_allowed(current, target, operation="password")
    target.password_hash = hash_password(payload.new_password)
    target.must_change_password = True
    target.token_version += 1
    _revoke_all_sessions(db, target.id)
    _audit(db, request, "user.password_reset", current.model.id, target.id)
    db.commit()
    sync_user_state(target)
    return _response(message="密码已重置，用户下次登录后必须修改密码")
