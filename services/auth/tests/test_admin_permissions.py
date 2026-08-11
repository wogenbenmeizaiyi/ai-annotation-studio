import pytest
from fastapi import HTTPException

from app.api.routes import _ensure_account_action_allowed
from app.core.dependencies import AuthenticatedUser
from app.models.user import User


def _user(
    *,
    role: str,
    is_platform_owner: bool = False,
) -> User:
    return User(
        id="owner" if is_platform_owner else f"{role}-user",
        username="test",
        username_normalized="test",
        display_name="Test",
        password_hash="hash",
        role=role,
        is_platform_owner=is_platform_owner,
        status="active",
    )


def _actor(*, is_platform_owner: bool) -> AuthenticatedUser:
    return AuthenticatedUser(
        model=_user(role="super_admin", is_platform_owner=is_platform_owner),
        claims={},
    )


@pytest.mark.parametrize("operation", ["status", "role", "password"])
def test_platform_owner_account_is_always_protected(operation: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _ensure_account_action_allowed(
            _actor(is_platform_owner=True),
            _user(role="super_admin", is_platform_owner=True),
            operation=operation,
        )
    assert exc_info.value.status_code == 409


@pytest.mark.parametrize("operation", ["status", "role", "password"])
def test_regular_admin_cannot_manage_another_admin(operation: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _ensure_account_action_allowed(
            _actor(is_platform_owner=False),
            _user(role="super_admin"),
            operation=operation,
        )
    assert exc_info.value.status_code == 403


def test_regular_admin_cannot_assign_roles() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _ensure_account_action_allowed(
            _actor(is_platform_owner=False),
            _user(role="user"),
            operation="role",
        )
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("operation", ["status", "password"])
def test_regular_admin_can_manage_regular_users(operation: str) -> None:
    _ensure_account_action_allowed(
        _actor(is_platform_owner=False),
        _user(role="user"),
        operation=operation,
    )


@pytest.mark.parametrize("operation", ["status", "role", "password"])
def test_platform_owner_can_manage_other_accounts(operation: str) -> None:
    _ensure_account_action_allowed(
        _actor(is_platform_owner=True),
        _user(role="super_admin"),
        operation=operation,
    )
