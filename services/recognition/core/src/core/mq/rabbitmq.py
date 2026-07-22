import logging

import pika

from core.config import config

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """RabbitMQ 阻塞连接单例。"""

    _instance: pika.BlockingConnection | None = None
    _channel: pika.channel.Channel | None = None

    @classmethod
    def get_connection(cls) -> pika.BlockingConnection:
        if cls._instance is None or not cls._instance.is_open:
            cls._instance = cls._create_connection()
            cls._channel = None
        return cls._instance

    @classmethod
    def get_channel(cls) -> pika.channel.Channel:
        if cls._channel is None or not cls._channel.is_open:
            cls._channel = cls.get_connection().channel()
        return cls._channel

    @classmethod
    def _create_connection(cls) -> pika.BlockingConnection:
        logger.info(
            "Connecting to RabbitMQ at %s:%d (vhost=%s)",
            config.RABBITMQ_HOST,
            config.RABBITMQ_PORT,
            config.RABBITMQ_VHOST,
        )
        credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=config.RABBITMQ_HOST,
            port=config.RABBITMQ_PORT,
            virtual_host=config.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=config.RABBITMQ_HEARTBEAT,
            blocked_connection_timeout=config.RABBITMQ_BLOCKED_CONNECTION_TIMEOUT,
        )
        connection = pika.BlockingConnection(parameters)
        logger.info("RabbitMQ connection established.")
        return connection

    @classmethod
    def close(cls) -> None:
        if cls._instance and cls._instance.is_open:
            cls._instance.close()
            cls._instance = None
            cls._channel = None
            logger.info("RabbitMQ connection closed.")
