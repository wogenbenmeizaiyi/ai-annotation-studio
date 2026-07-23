"""全局配置 - 从环境变量读取"""

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("APP_ENV_FILE") or None)


class Settings:
    """应用配置"""

    # ===== PostgreSQL =====
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "annotation_studio")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ===== RustFS (S3 compatible) =====
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_PUBLIC_ENDPOINT: str = os.getenv("S3_PUBLIC_ENDPOINT", S3_ENDPOINT)
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_SIGNATURE_VERSION: str = os.getenv("S3_SIGNATURE_VERSION", "s3v4")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "ai-cmm")
    S3_URL_EXPIRES: int = int(os.getenv("S3_URL_EXPIRES", "3600"))

    # ===== 训练数据目录（YOLO构建时本地临时目录） =====
    TRAIN_DATA_DIR: str = os.getenv("TRAIN_DATA_DIR", "storage/train_data")
    YOLO_MODEL_DIR: str = os.getenv("YOLO_MODEL_DIR", "models/yolo_models")
    YOLO_WORKERS: int = int(os.getenv("YOLO_WORKERS", "4"))
    TRAIN_QUEUE_POLL_SECONDS: float = float(os.getenv("TRAIN_QUEUE_POLL_SECONDS", "2"))
    TRAIN_WORKER_HEARTBEAT_SECONDS: int = int(
        os.getenv("TRAIN_WORKER_HEARTBEAT_SECONDS", "15")
    )
    TRAIN_WORKER_STALE_SECONDS: int = int(os.getenv("TRAIN_WORKER_STALE_SECONDS", "120"))

    # ===== YOLO Agent（OpenAI兼容接口，默认使用百炼） =====
    AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "")
    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "qwen3.7-plus")
    AGENT_BASE_URL: str = os.getenv(
        "AGENT_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    AGENT_TIMEOUT_SECONDS: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "60"))
    AGENT_MAX_OUTPUT_TOKENS: int = int(os.getenv("AGENT_MAX_OUTPUT_TOKENS", "2000"))
    AGENT_FORCE_IPV4: bool = os.getenv("AGENT_FORCE_IPV4", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    AGENT_LOG_FILE: str = os.getenv("AGENT_LOG_FILE", "agent.log")
    AGENT_LOG_MAX_BYTES: int = int(os.getenv("AGENT_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    AGENT_LOG_BACKUP_COUNT: int = int(os.getenv("AGENT_LOG_BACKUP_COUNT", "10"))

    # ===== SAM3 模型 =====
    SAM3_MODEL_PATH: str = os.getenv("SAM3_MODEL_PATH", "models/sam3.pt")

    # ===== 用户认证 =====
    AUTH_PUBLIC_KEY_PATH: str = os.getenv(
        "AUTH_PUBLIC_KEY_PATH", ".local/keys/auth-public.pem"
    )
    AUTH_ISSUER: str = os.getenv("AUTH_ISSUER", "ai-annotation-studio-auth")
    AUTH_AUDIENCE: str = os.getenv("AUTH_AUDIENCE", "ai-annotation-studio")
    AUTH_ACCESS_COOKIE: str = os.getenv("AUTH_ACCESS_COOKIE", "studio_access")
    AUTH_CSRF_COOKIE: str = os.getenv("AUTH_CSRF_COOKIE", "studio_csrf")
    AUTH_REDIS_HOST: str = os.getenv("AUTH_REDIS_HOST", os.getenv("REDIS_HOST", "localhost"))
    AUTH_REDIS_PORT: int = int(os.getenv("AUTH_REDIS_PORT", os.getenv("REDIS_PORT", "6379")))
    AUTH_REDIS_PASSWORD: str = os.getenv(
        "AUTH_REDIS_PASSWORD", os.getenv("REDIS_PASSWORD", "")
    )
    AUTH_REDIS_DB: int = int(os.getenv("AUTH_REDIS_DB", "3"))
    AUTH_ALLOWED_ORIGINS: list[str] = [
        value.strip()
        for value in os.getenv(
            "AUTH_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if value.strip()
    ]

    @property
    def AUTH_REDIS_URL(self) -> str:
        password = f":{self.AUTH_REDIS_PASSWORD}@" if self.AUTH_REDIS_PASSWORD else ""
        return f"redis://{password}{self.AUTH_REDIS_HOST}:{self.AUTH_REDIS_PORT}/{self.AUTH_REDIS_DB}"


settings = Settings()
