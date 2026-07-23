import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pwdlib import PasswordHash

from app.core.config import settings
from app.models.user import User


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-password-value")


def normalize_username(username: str) -> str:
    return username.strip().casefold()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def ensure_signing_keys() -> tuple[Path, Path]:
    private_path = Path(settings.AUTH_PRIVATE_KEY_PATH).expanduser().resolve()
    public_path = Path(settings.AUTH_PUBLIC_KEY_PATH).expanduser().resolve()
    if private_path.exists() and public_path.exists():
        return private_path, public_path
    if settings.APP_ENV.lower() == "production":
        raise RuntimeError("生产环境必须挂载认证签名密钥")

    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


def _load_private_key() -> Ed25519PrivateKey:
    private_path, _ = ensure_signing_keys()
    key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("认证私钥必须是 Ed25519 私钥")
    return key


def load_public_key():
    _, public_path = ensure_signing_keys()
    return serialization.load_pem_public_key(public_path.read_bytes())


def get_key_id() -> str:
    public_key = load_public_key()
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()[:16]


def get_jwks() -> dict[str, list[dict[str, str]]]:
    public_key = load_public_key()
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "x": _base64url(raw),
                "use": "sig",
                "alg": "EdDSA",
                "kid": get_key_id(),
            }
        ]
    }


def create_access_token(user: User, session_id: str, csrf_token: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES)
    claims = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "must_change_password": user.must_change_password,
        "ver": user.token_version,
        "sid": session_id,
        "csrf": csrf_token,
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": str(secrets.token_hex(16)),
    }
    token = jwt.encode(
        claims,
        _load_private_key(),
        algorithm="EdDSA",
        headers={"kid": get_key_id()},
    )
    return token, int((expires - now).total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        load_public_key(),
        algorithms=["EdDSA"],
        audience=settings.AUTH_AUDIENCE,
        issuer=settings.AUTH_ISSUER,
        options={"require": ["sub", "sid", "ver", "csrf", "exp", "iat"]},
    )


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)
