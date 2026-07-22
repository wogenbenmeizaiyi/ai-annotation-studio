import boto3
from botocore.client import Config

from app.core.config import settings


class S3Client:
    _instance = None
    _s3_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Client, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version=settings.S3_SIGNATURE_VERSION),
            region_name=settings.S3_REGION,
        )
        print("S3/RustFS 客户端已初始化")

    def get_client(self):
        return self._s3_client

    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        生成 RustFS/S3 预签名访问链接

        Args:
            bucket: 桶名
            key: 对象key
            expires_in: 链接有效时间(秒), 默认1小时

        Returns:
            预签名URL字符串
        """
        return self._s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )


s3_instance = S3Client()
s3 = s3_instance.get_client()
