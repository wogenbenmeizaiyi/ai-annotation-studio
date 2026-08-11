import platform

from celery import Celery
from kombu import Exchange, Queue

from core.config import config

celery_app = Celery(
    "worker",
    broker=config.get_url(),
    backend=config.REDIS_BACKEND_URL,
    include=["tasks.recognize"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_queues=(
        Queue(
            config.QUEUE_NAME,
            Exchange(config.QUEUE_NAME, type="direct", durable=True),
            routing_key=config.QUEUE_NAME,
            durable=True,
            queue_arguments={
                "x-dead-letter-exchange": config.TASK_DEAD_LETTER_EXCHANGE,
                "x-dead-letter-routing-key": config.TASK_DEAD_LETTER_ROUTING_KEY,
            },
        ),
        Queue(
            config.TASK_DEAD_LETTER_QUEUE,
            Exchange(config.TASK_DEAD_LETTER_EXCHANGE, type="direct", durable=True),
            routing_key=config.TASK_DEAD_LETTER_ROUTING_KEY,
            durable=True,
        ),
    ),
    task_default_queue=config.QUEUE_NAME,
    task_default_exchange=config.QUEUE_NAME,
    task_default_exchange_type="direct",
    task_default_routing_key=config.QUEUE_NAME,
    task_routes={
        config.RECOGNIZE_IMAGE_TASK_NAME: {
            "queue": config.QUEUE_NAME,
            "routing_key": config.QUEUE_NAME,
        },
        "tasks.recognize.*": {
            "queue": config.QUEUE_NAME,
            "routing_key": config.QUEUE_NAME,
        },
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
)

if platform.system() == "Windows":
    celery_app.conf.update(worker_pool="solo")
