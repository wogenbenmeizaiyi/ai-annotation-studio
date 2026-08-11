import logging

import boto3
from botocore.client import Config

from core.config import config

logger = logging.getLogger(__name__)


class S3Client:
    _instance = None
    _s3_client = None

    def __new__(cls):
        # 确保只创建一个实例
        if cls._instance is None:
            cls._instance = super(S3Client, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        # 初始化 S3 客户端配置 (从 config.py 读取)
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            config=Config(signature_version=config.S3_SIGNATURE_VERSION),
            region_name=config.S3_REGION,
        )
        logger.info("S3 客户端已初始化")

    def get_client(self):
        return self._s3_client


# 实例化单例
s3_instance = S3Client()

# 导出 s3 客户端对象，方便在其他文件中直接 `from s3_client import s3`
s3 = s3_instance.get_client()
