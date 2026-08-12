import logging

import pika

from core.mq.rabbitmq import RabbitMQConnection
from core.mq.task_routing import TASK_QUEUE_SPECS

logger = logging.getLogger(__name__)

_task_infra_declared = False


def ensure_task_infra(channel: pika.channel.Channel | None = None) -> None:
    """声明 worker 任务队列和任务死信队列。"""
    global _task_infra_declared
    if _task_infra_declared:
        return

    ch = channel or RabbitMQConnection.get_channel()
    for spec in TASK_QUEUE_SPECS.values():
        ch.exchange_declare(
            exchange=spec.dead_letter_exchange,
            exchange_type="direct",
            durable=True,
        )
        ch.queue_declare(queue=spec.dead_letter_queue, durable=True)
        ch.queue_bind(
            queue=spec.dead_letter_queue,
            exchange=spec.dead_letter_exchange,
            routing_key=spec.dead_letter_routing_key,
        )
        ch.exchange_declare(
            exchange=spec.exchange_name,
            exchange_type="direct",
            durable=True,
        )
        ch.queue_declare(
            queue=spec.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": spec.dead_letter_exchange,
                "x-dead-letter-routing-key": spec.dead_letter_routing_key,
            },
        )
        ch.queue_bind(
            queue=spec.queue_name,
            exchange=spec.exchange_name,
            routing_key=spec.routing_key,
        )
    _task_infra_declared = True
    logger.info(
        "Declared recognition task queues: %s",
        ", ".join(spec.queue_name for spec in TASK_QUEUE_SPECS.values()),
    )
