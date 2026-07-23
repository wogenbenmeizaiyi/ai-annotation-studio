from pathlib import Path

import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    ensure_signing_keys,
    hash_password,
    verify_password,
)
from app.models.user import User


def test_argon2_password_round_trip() -> None:
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("incorrect password", encoded)


def test_access_token_uses_ed25519_and_required_claims(tmp_path: Path) -> None:
    settings.APP_ENV = "test"
    settings.AUTH_PRIVATE_KEY_PATH = str(tmp_path / "private.pem")
    settings.AUTH_PUBLIC_KEY_PATH = str(tmp_path / "public.pem")
    _, public_path = ensure_signing_keys()
    user = User(
        id="8dba2eae-476e-4dac-8d8f-aa2ef79d0d8e",
        username="admin",
        username_normalized="admin",
        display_name="Administrator",
        password_hash="not-used",
        role="super_admin",
        status="active",
        token_version=3,
        must_change_password=False,
    )

    token, max_age = create_access_token(user, "session-id", "csrf-value")
    claims = jwt.decode(
        token,
        public_path.read_bytes(),
        algorithms=["EdDSA"],
        audience=settings.AUTH_AUDIENCE,
        issuer=settings.AUTH_ISSUER,
    )

    assert 0 < max_age <= settings.AUTH_ACCESS_TOKEN_MINUTES * 60
    assert claims["sub"] == user.id
    assert claims["sid"] == "session-id"
    assert claims["csrf"] == "csrf-value"
    assert claims["ver"] == 3
