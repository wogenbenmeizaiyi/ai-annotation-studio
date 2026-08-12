import platform

from celery import Celery
from kombu import Exchange, Queue

from core.config import config
from core.mq.task_routing import TASK_QUEUE_SPECS, route_recognition_task


def _task_queues() -> tuple[Queue, ...]:
    queues: list[Queue] = []
    for spec in TASK_QUEUE_SPECS.values():
        queues.append(
            Queue(
                spec.queue_name,
                Exchange(spec.exchange_name, type="direct", durable=True),
                routing_key=spec.routing_key,
                durable=True,
                queue_arguments={
                    "x-dead-letter-exchange": spec.dead_letter_exchange,
                    "x-dead-letter-routing-key": spec.dead_letter_routing_key,
                },
            )
        )
        queues.append(
            Queue(
                spec.dead_letter_queue,
                Exchange(spec.dead_letter_exchange, type="direct", durable=True),
                routing_key=spec.dead_letter_routing_key,
                durable=True,
            )
        )
    return tuple(queues)


celery_app = Celery(
    "worker",
    broker=config.get_url(),
    backend=config.REDIS_BACKEND_URL,
)

default_spec = TASK_QUEUE_SPECS["yolo"]
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_queues=_task_queues(),
    task_default_queue=default_spec.queue_name,
    task_default_exchange=default_spec.exchange_name,
    task_default_exchange_type="direct",
    task_default_routing_key=default_spec.routing_key,
    task_routes=(route_recognition_task,),
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
)

if platform.system() == "Windows":
    celery_app.conf.update(worker_pool="solo")
