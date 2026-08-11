import os
from pathlib import Path

from dotenv import load_dotenv


def _load_environment() -> None:
    env_file = os.getenv("APP_ENV_FILE")
    if env_file:
        load_dotenv(Path(env_file), override=False)
        return
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _as_bool(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


_load_environment()


class Settings:
    APP_ENV = os.getenv("APP_ENV", "development")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "auth_service")

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
    REDIS_DB = int(os.getenv("REDIS_DB", "3"))

    AUTH_ISSUER = os.getenv("AUTH_ISSUER", "ai-annotation-studio-auth")
    AUTH_AUDIENCE = os.getenv("AUTH_AUDIENCE", "ai-annotation-studio")
    AUTH_PRIVATE_KEY_PATH = os.getenv(
        "AUTH_PRIVATE_KEY_PATH", ".local/keys/auth-private.pem"
    )
    AUTH_PUBLIC_KEY_PATH = os.getenv(
        "AUTH_PUBLIC_KEY_PATH", ".local/keys/auth-public.pem"
    )
    AUTH_COOKIE_SECURE = _as_bool(os.getenv("AUTH_COOKIE_SECURE", "false"))
    AUTH_ALLOWED_ORIGINS = [
        value.strip()
        for value in os.getenv(
            "AUTH_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if value.strip()
    ]
    AUTH_ACCESS_TOKEN_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15"))
    AUTH_REFRESH_TOKEN_DAYS = int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "7"))

    ACCESS_COOKIE = "studio_access"
    REFRESH_COOKIE = "studio_refresh"
    CSRF_COOKIE = "studio_csrf"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
