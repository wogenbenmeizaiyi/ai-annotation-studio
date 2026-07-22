import json
import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial

import pika

from core.config import config
from core.mq.rabbitmq import RabbitMQConnection

logger = logging.getLogger(__name__)

ResultMessageHandler = Callable[[dict], None]
RawResultMessageHandler = Callable[[bytes], None]

_infra_declared = False


def ensure_result_infra(channel: pika.channel.Channel | None = None) -> None:
    """声明 worker 结果发布/订阅使用的 exchange 和 queue。"""
    global _infra_declared
    if _infra_declared:
        return

    ch = channel or RabbitMQConnection.get_channel()
    ch.exchange_declare(
        exchange=config.RESULT_EXCHANGE,
        exchange_type="fanout",
        durable=True,
    )
    ch.exchange_declare(
        exchange=config.RESULT_DEAD_LETTER_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )
    ch.queue_declare(queue=config.RESULT_DEAD_LETTER_QUEUE, durable=True)
    ch.queue_bind(
        queue=config.RESULT_DEAD_LETTER_QUEUE,
        exchange=config.RESULT_DEAD_LETTER_EXCHANGE,
        routing_key=config.RESULT_DEAD_LETTER_ROUTING_KEY,
    )
    ch.queue_declare(
        queue=config.RESULT_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": config.RESULT_DEAD_LETTER_EXCHANGE,
            "x-dead-letter-routing-key": config.RESULT_DEAD_LETTER_ROUTING_KEY,
        },
    )
    ch.queue_bind(queue=config.RESULT_QUEUE, exchange=config.RESULT_EXCHANGE)
    _infra_declared = True


def compact_recognition_result(result_data: dict) -> dict:
    """构建下游队列消息，保留回调和结果入库需要的字段。"""

    def strip_meta(item: dict) -> dict:
        return {
            "url": item.get("url", ""),
            "service": item.get("service", ""),
            "detection_type": item.get("detection_type", ""),
            "count": item.get("count", 0),
            "image_key": item.get("image_key", ""),
            "coco_key": item.get("coco_key", ""),
            "images": item.get("images", []),
            "annotations": item.get("annotations", []),
            "categories": item.get("categories", []),
        }

    return {
        "task_id": result_data["task_id"],
        "service": result_data.get("detection_type", ""),
        "prompt_or_model": result_data.get("prompt_or_model", ""),
        "image_count": result_data.get("image_count", 0),
        "results": [strip_meta(r) for r in result_data.get("results", [])],
    }


def publish_result(payload: dict) -> None:
    """将识别结果发布到结果交换机，供回调服务或其他下游订阅。"""
    channel = RabbitMQConnection.get_channel()
    ensure_result_infra(channel)

    logger.info(
        "Publishing result for task %s to exchange '%s'",
        payload["task_id"],
        config.RESULT_EXCHANGE,
    )
    channel.basic_publish(
        exchange=config.RESULT_EXCHANGE,
        routing_key="",
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=pika.DeliveryMode.Persistent,
        ),
    )
    logger.info(
        "Task %s: Result published to exchange %s",
        payload["task_id"],
        config.RESULT_EXCHANGE,
    )


def subscribe_results(handler: ResultMessageHandler) -> None:
    """阻塞订阅识别结果队列，并把消息交给 handler 处理。"""
    channel = RabbitMQConnection.get_channel()
    ensure_result_infra(channel)
    channel.basic_qos(prefetch_count=1)

    def on_message(
        ch: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        try:
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("Result message body must be a JSON object.")
            handler(payload)
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
            logger.exception("Invalid result message, dead-lettering it.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception:
            logger.exception("Failed to handle result message, dead-lettering it.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=config.RESULT_QUEUE,
        on_message_callback=on_message,
        auto_ack=False,
    )
    logger.info("Subscribed result queue: %s", config.RESULT_QUEUE)
    channel.start_consuming()


def subscribe_raw_results(handler: RawResultMessageHandler) -> None:
    """阻塞订阅识别结果队列，把原始消息体交给 handler 处理。"""
    channel = RabbitMQConnection.get_channel()
    ensure_result_infra(channel)
    concurrency = max(config.RESULT_CONSUMER_CONCURRENCY, 1)
    channel.basic_qos(prefetch_count=concurrency)

    def ack_message(delivery_tag: int) -> None:
        if channel.is_open:
            channel.basic_ack(delivery_tag=delivery_tag)

    def nack_message(delivery_tag: int) -> None:
        if channel.is_open:
            channel.basic_nack(delivery_tag=delivery_tag, requeue=False)

    def handle_future_result(future: Future[None], delivery_tag: int) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Failed to handle raw result message, dead-lettering it.")
            channel.connection.add_callback_threadsafe(
                partial(nack_message, delivery_tag)
            )
        else:
            channel.connection.add_callback_threadsafe(
                partial(ack_message, delivery_tag)
            )

    with ThreadPoolExecutor(max_workers=concurrency) as executor:

        def on_message(
            ch: pika.channel.Channel,
            method: pika.spec.Basic.Deliver,
            properties: pika.spec.BasicProperties,
            body: bytes,
        ) -> None:
            delivery_tag = method.delivery_tag
            future = executor.submit(handler, body)
            future.add_done_callback(
                partial(handle_future_result, delivery_tag=delivery_tag)
            )

        channel.basic_consume(
            queue=config.RESULT_QUEUE,
            on_message_callback=on_message,
            auto_ack=False,
        )
        logger.info(
            "Subscribed raw result queue: %s concurrency=%s",
            config.RESULT_QUEUE,
            concurrency,
        )
        channel.start_consuming()
