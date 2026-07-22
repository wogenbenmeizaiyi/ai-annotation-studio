import logging

import pika

from core.config import config
from core.mq.rabbitmq import RabbitMQConnection

logger = logging.getLogger(__name__)

_task_infra_declared = False


def ensure_task_infra(channel: pika.channel.Channel | None = None) -> None:
    """声明 worker 任务队列和任务死信队列。"""
    global _task_infra_declared
    if _task_infra_declared:
        return

    ch = channel or RabbitMQConnection.get_channel()
    ch.exchange_declare(
        exchange=config.TASK_DEAD_LETTER_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )
    ch.queue_declare(queue=config.TASK_DEAD_LETTER_QUEUE, durable=True)
    ch.queue_bind(
        queue=config.TASK_DEAD_LETTER_QUEUE,
        exchange=config.TASK_DEAD_LETTER_EXCHANGE,
        routing_key=config.TASK_DEAD_LETTER_ROUTING_KEY,
    )
    ch.exchange_declare(
        exchange=config.QUEUE_NAME,
        exchange_type="direct",
        durable=True,
    )
    ch.queue_declare(
        queue=config.QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": config.TASK_DEAD_LETTER_EXCHANGE,
            "x-dead-letter-routing-key": config.TASK_DEAD_LETTER_ROUTING_KEY,
        },
    )
    ch.queue_bind(
        queue=config.QUEUE_NAME,
        exchange=config.QUEUE_NAME,
        routing_key=config.QUEUE_NAME,
    )
    _task_infra_declared = True
    logger.info(
        "Declared task queue %s and dead-letter queue %s",
        config.QUEUE_NAME,
        config.TASK_DEAD_LETTER_QUEUE,
    )
