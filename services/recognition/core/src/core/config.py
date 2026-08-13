import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("APP_ENV_FILE") or None)


class Config:
    AUTH_PUBLIC_KEY_PATH = os.getenv("AUTH_PUBLIC_KEY_PATH", ".local/auth/public.pem")
    AUTH_ISSUER = os.getenv("AUTH_ISSUER", "ai-annotation-studio-auth")
    AUTH_AUDIENCE = os.getenv("AUTH_AUDIENCE", "ai-annotation-studio")
    AUTH_ACCESS_COOKIE = os.getenv("AUTH_ACCESS_COOKIE", "studio_access")
    AUTH_CSRF_COOKIE = os.getenv("AUTH_CSRF_COOKIE", "studio_csrf")
    AUTH_REDIS_DB = int(os.getenv("AUTH_REDIS_DB", "3"))
    AUTH_REDIS_URL = os.getenv("AUTH_REDIS_URL", "")
    PLATFORM_ALLOWED_ORIGINS = [
        value.strip()
        for value in os.getenv(
            "PLATFORM_ALLOWED_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if value.strip()
    ]
    TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
    PUBLIC_SUBMIT_RATE = int(os.getenv("PUBLIC_SUBMIT_RATE", "30"))
    PUBLIC_DIRECT_RATE = int(os.getenv("PUBLIC_DIRECT_RATE", "10"))
    PUBLIC_QUERY_RATE = int(os.getenv("PUBLIC_QUERY_RATE", "120"))
    PUBLIC_MAX_IMAGES = int(os.getenv("PUBLIC_MAX_IMAGES", "300"))
    PUBLIC_MAX_UPLOAD_BYTES = int(
        os.getenv("PUBLIC_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))
    )
    PUBLIC_IMAGE_URL_ALLOWLIST = [
        value.strip().lower()
        for value in os.getenv("PUBLIC_IMAGE_URL_ALLOWLIST", "").split(",")
        if value.strip()
    ]
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
    RABBITMQ_USER = os.getenv("RABBITMQ_USER")
    RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")
    RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "task_queue")

    # 结果广播交换机：Worker 完成任务后将结果发布到此处（出口/路由器）
    RESULT_EXCHANGE = os.getenv(
        "RABBITMQ_RESULT_EXCHANGE", "events.image.disease_detected"
    )
    # 结果存储队列：绑定到 RESULT_EXCHANGE，用于下游系统消费识别结果（出口终点）
    RESULT_QUEUE = os.getenv(
        "RABBITMQ_RESULT_QUEUE", "events.image.disease_detected"
    )
    RESULT_DEAD_LETTER_EXCHANGE = os.getenv(
        "RABBITMQ_RESULT_DLX", f"{RESULT_QUEUE}.dlx"
    )
    RESULT_DEAD_LETTER_QUEUE = os.getenv("RABBITMQ_RESULT_DLQ", f"{RESULT_QUEUE}.dlq")
    RESULT_DEAD_LETTER_ROUTING_KEY = os.getenv(
        "RABBITMQ_RESULT_DLQ_ROUTING_KEY", RESULT_DEAD_LETTER_QUEUE
    )

    CALLBACK_RETRY_INTERVAL_SECONDS = int(
        os.getenv("CALLBACK_RETRY_INTERVAL_SECONDS", 0)
    )
    CALLBACK_RETRY_TIMEOUT_SECONDS = int(
        os.getenv("CALLBACK_RETRY_TIMEOUT_SECONDS", 10)
    )
    CALLBACK_REQUEST_TIMEOUT_SECONDS = int(
        os.getenv("CALLBACK_REQUEST_TIMEOUT_SECONDS", 10)
    )
    CALLBACK_MAX_ATTEMPTS = int(os.getenv("CALLBACK_MAX_ATTEMPTS", 1))
    IMAGE_RETRY_MAX_ATTEMPTS = int(os.getenv("IMAGE_RETRY_MAX_ATTEMPTS", 3))
    IMAGE_RETRY_DELAY_SECONDS = int(os.getenv("IMAGE_RETRY_DELAY_SECONDS", 30))
    RESULT_DB_BATCH_SIZE = int(os.getenv("RESULT_DB_BATCH_SIZE", 50))
    RESOURCE_CHECK_ENABLED = (
        os.getenv("RESOURCE_CHECK_ENABLED", "true").lower() == "true"
    )
    RESOURCE_CHECK_INTERVAL_SECONDS = int(
        os.getenv("RESOURCE_CHECK_INTERVAL_SECONDS", 5)
    )
    RESOURCE_MIN_SYSTEM_MEMORY_MB = int(
        os.getenv("RESOURCE_MIN_SYSTEM_MEMORY_MB", 1024)
    )
    RESOURCE_MIN_GPU_MEMORY_MB = int(os.getenv("RESOURCE_MIN_GPU_MEMORY_MB", 2048))
    RESOURCE_WAIT_TIMEOUT_SECONDS = int(os.getenv("RESOURCE_WAIT_TIMEOUT_SECONDS", 0))
    RESULT_CONSUMER_CONCURRENCY = int(os.getenv("RESULT_CONSUMER_CONCURRENCY", 4))
    MODELS_DIR = os.getenv("MODELS_DIR", "models")
    SAM_IMAGE_SIZE = int(os.getenv("SAM_IMAGE_SIZE", 1568))
    SAM_SEGMENTATION_EPSILON = float(os.getenv("SAM_SEGMENTATION_EPSILON", 4.0))

    RABBITMQ_HEARTBEAT = int(os.getenv("RABBITMQ_HEARTBEAT", 600))
    RABBITMQ_BLOCKED_CONNECTION_TIMEOUT = int(
        os.getenv("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", 300)
    )

    S3_ENDPOINT = os.getenv("S3_ENDPOINT")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_SIGNATURE_VERSION = os.getenv("S3_SIGNATURE_VERSION", "s3v4")
    S3_BUCKET = "ai-cmm"

    @classmethod
    def get_url(cls):
        return f"amqp://{cls.RABBITMQ_USER}:{cls.RABBITMQ_PASS}@{cls.RABBITMQ_HOST}:{cls.RABBITMQ_PORT}/{cls.RABBITMQ_VHOST}"

    # Broker 配置（如果你也在用 Redis 作为 broker）
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))  # 转整数
    REDIS_DB = int(os.getenv("REDIS_DB", 0))  # 转整数
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

    @property
    def AUTH_STATE_REDIS_URL(self):
        if self.AUTH_REDIS_URL:
            return self.AUTH_REDIS_URL
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/{self.AUTH_REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.AUTH_REDIS_DB}"

    # Backend URL
    @property
    def REDIS_BACKEND_URL(self):
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # 如果你同时用 Redis 作为 broker
    @property
    def BROKER_URL(self):
        # 返回 Redis URL 或其他 broker URL
        return self.REDIS_BACKEND_URL

    # pg数据库配置
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "annotation_studio")

    @property
    def DATABASE_URL(self):
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


config = Config()
