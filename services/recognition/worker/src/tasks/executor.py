import asyncio
import logging
from collections.abc import Awaitable, Callable

from celery.exceptions import Reject

from core.config import config
from core.db import SessionLocal
from core.mq.task_routing import (
    TaskQueueSpec,
    UnsupportedDetectionType,
    get_detection_method,
    get_task_queue_spec,
    normalize_detection_type,
)
from core.storage.recognition_result_storage import (
    complete_recognition_result_storage,
    fail_recognition_result_storage,
    prepare_recognition_result_storage,
    save_recognition_image_result_batch,
)
from tasks.helpers import _image_to_bytes, download_image

logger = logging.getLogger(__name__)


class ImageProcessingRetriesExhausted(Exception):
    """单张图片重试耗尽。"""


def mark_task_failed(task_id: str, error: str) -> None:
    """Best-effort terminal-state update that never masks queue rejection."""
    if not task_id:
        logger.error("Cannot mark recognition task failed without task_id: %s", error)
        return
    db = None
    try:
        db = SessionLocal()
        fail_recognition_result_storage(task_id, error, db)
    except Exception:
        if db is not None:
            db.rollback()
        logger.exception("Task %s: failed to persist terminal failure", task_id)
    finally:
        if db is not None:
            db.close()


def _request_routing_key(task) -> str:
    delivery_info = getattr(task.request, "delivery_info", None) or {}
    return delivery_info.get("routing_key", "")


def validate_task_delivery(
    task,
    detection_type: object,
    allowed_detection_types: frozenset[int],
) -> tuple[int, TaskQueueSpec]:
    """拒绝错投或越过 worker 资源边界的任务。"""
    try:
        normalized = normalize_detection_type(detection_type)
        spec = get_task_queue_spec(normalized)
    except UnsupportedDetectionType as exc:
        raise Reject(str(exc), requeue=False) from exc

    actual_routing_key = _request_routing_key(task)
    if (
        normalized not in allowed_detection_types
        or actual_routing_key != spec.routing_key
    ):
        raise Reject(
            "Task delivery does not match detection type: "
            f"detection_type={normalized}, routing_key={actual_routing_key!r}, "
            f"expected={spec.routing_key!r}",
            requeue=False,
        )
    return normalized, spec


def retry_on_expected_route(task, exc: Exception, spec: TaskQueueSpec):
    return task.retry(
        exc=exc,
        queue=spec.queue_name,
        exchange=spec.exchange_name,
        routing_key=spec.routing_key,
    )


async def _process_single_image(
    service,
    url: str,
    prompt_or_model: str,
    confidence: float,
    project_name: str,
    category_name: str,
):
    image, ext = download_image(url)
    from core.schemas.recognition import RecognitionRequest

    request = RecognitionRequest(
        image_data=_image_to_bytes(image),
        detection_type=prompt_or_model,
        confidence=confidence,
        project_name=project_name,
        extra={
            "image_ext": ext,
            "url": url,
            "category_name": category_name,
        },
    )
    result = await service.recognize(request)
    result.extra["url"] = url
    return result


async def _process_single_image_with_retry(
    service,
    url: str,
    prompt_or_model: str,
    confidence: float,
    project_name: str,
    category_name: str,
    task_id: str,
    image_index: int,
):
    max_attempts = max(config.IMAGE_RETRY_MAX_ATTEMPTS, 1)
    retry_delay = max(config.IMAGE_RETRY_DELAY_SECONDS, 0)
    for attempt in range(1, max_attempts + 1):
        try:
            return await _process_single_image(
                service,
                url,
                prompt_or_model,
                confidence,
                project_name,
                category_name,
            )
        except Exception as exc:
            if attempt >= max_attempts:
                logger.exception(
                    "Task %s: image %d failed after %d attempts url=%s",
                    task_id,
                    image_index,
                    attempt,
                    url,
                )
                raise ImageProcessingRetriesExhausted(str(exc)) from exc
            logger.warning(
                "Task %s: image %d failed attempt %d/%d, retrying in %ss",
                task_id,
                image_index,
                attempt,
                max_attempts,
                retry_delay,
            )
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)


def _update_progress(task, task_id: str, meta: dict) -> None:
    try:
        task.update_state(state="PROGRESS", meta=meta)
    except ValueError as exc:
        if "Exception information must include the exception type" not in str(exc):
            raise
        task.backend.forget(task_id)
        task.update_state(state="PROGRESS", meta=meta)


def execute_recognition_task(
    task,
    kwargs: dict,
    *,
    service_factory: Callable[[int], object],
    allowed_detection_types: frozenset[int],
    wait_for_resources: Callable[[str, int], Awaitable[None]],
    cleanup: Callable[[], None] | None = None,
) -> dict:
    task_id = kwargs.get("task_id", task.request.id)
    db = None
    service = None
    spec = None
    processed_count = 0
    try:
        detection_type, spec = validate_task_delivery(
            task,
            kwargs.get("detection_type"),
            allowed_detection_types,
        )
        method = get_detection_method(detection_type)
        prompt_or_model = kwargs.get("text", "")
        images = kwargs.get("images", [])
        confidence = kwargs.get("confidence", 0.5)
        project_name = kwargs.get("project_name") or "通用"
        category_name = kwargs.get("category_name") or ""
        if not images:
            raise ValueError("images is required")
        if detection_type in (3, 4) and not prompt_or_model:
            raise ValueError("text is required for this detection type")

        service = service_factory(detection_type)
        total = len(images)
        db = SessionLocal()
        store_results_in_db = prepare_recognition_result_storage(task_id, db)
        result_batch_size = max(config.RESULT_DB_BATCH_SIZE, 1)
        result_batch: list[dict] = []
        serialized_results: list[dict] = []

        def flush_result_batch() -> None:
            if not result_batch:
                return
            save_recognition_image_result_batch(
                task_id,
                result_batch,
                db,
                method.value,
                prompt_or_model,
            )
            result_batch.clear()

        async def process_all() -> None:
            nonlocal processed_count
            _update_progress(
                task,
                task_id,
                {"processed": 0, "total": total, "percent": 0},
            )
            for index, url in enumerate(images):
                await wait_for_resources(task_id, index + 1)
                response = await _process_single_image_with_retry(
                    service,
                    url,
                    prompt_or_model,
                    confidence,
                    project_name,
                    category_name,
                    task_id,
                    index + 1,
                )
                serialized = service.serialize_response(response)
                serialized["url"] = url
                serialized["image_index"] = index
                if store_results_in_db:
                    result_batch.append(serialized)
                    if len(result_batch) >= result_batch_size:
                        flush_result_batch()
                else:
                    serialized_results.append(serialized)
                processed_count += 1
                _update_progress(
                    task,
                    task_id,
                    {
                        "processed": processed_count,
                        "total": total,
                        "percent": int(processed_count / total * 100),
                    },
                )
            if store_results_in_db:
                flush_result_batch()

        asyncio.run(process_all())
        result_summary = {
            "event_type": "task_completed",
            "task_id": task_id,
            "detection_type": method.value,
            "service": method.value,
            "prompt_or_model": prompt_or_model,
            "image_count": processed_count,
            "result_storage": "recognition_image_results",
            "progress": {"processed": total, "total": total, "percent": 100},
        }
        if store_results_in_db:
            complete_recognition_result_storage(task_id, result_summary, db)
        return {
            "task_id": task_id,
            "progress": {"processed": total, "total": total, "percent": 100},
        }
    except Reject as exc:
        mark_task_failed(task_id, str(exc))
        raise
    except ImageProcessingRetriesExhausted as exc:
        if db is not None:
            db.rollback()
        mark_task_failed(task_id, str(exc))
        raise Reject(str(exc), requeue=False) from exc
    except Exception as exc:
        if db is not None:
            db.rollback()
        if task.request.retries >= task.max_retries:
            mark_task_failed(task_id, str(exc))
            raise Reject(str(exc), requeue=False) from exc
        if spec is None:
            mark_task_failed(task_id, str(exc))
            raise Reject(str(exc), requeue=False) from exc
        try:
            return retry_on_expected_route(task, exc, spec)
        except Exception as retry_publish_error:
            if not isinstance(retry_publish_error, Reject):
                raise
            mark_task_failed(task_id, str(retry_publish_error))
            raise
    finally:
        if service is not None:
            try:
                service.release_resources()
            except Exception:
                logger.exception("Task %s: failed to release resources", task_id)
        if cleanup is not None:
            try:
                cleanup()
            except Exception:
                logger.exception("Task %s: failed to clean up worker resources", task_id)
        if db is not None:
            db.close()
