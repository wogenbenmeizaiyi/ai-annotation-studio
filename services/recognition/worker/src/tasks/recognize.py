import asyncio
import logging

from celery.exceptions import Reject

from core.config import config
from core.db import SessionLocal
from core.mq import (
    celery_app,
    compact_recognition_result,
    publish_result,
)
from core.schemas.recognition import RecognitionRequest
from core.storage.recognition_result_storage import (
    complete_recognition_result_storage,
    fail_recognition_result_storage,
    prepare_recognition_result_storage,
    save_recognition_image_result_batch,
)
from engine.services import (
    YoloDetectionService,
    YoloSegmentationService,
    SamSegmentationService,
    MultimodalService,
    RecognitionMethod,
)
from tasks.helpers import _image_to_bytes, download_image
from tasks.resources import wait_for_resources

logger = logging.getLogger(__name__)


class ImageProcessingRetriesExhausted(Exception):
    """单张图片重试耗尽。"""


SERVICE_MAP = {
    RecognitionMethod.YOLO_DETECTION: YoloDetectionService(),
    RecognitionMethod.YOLO_SEGMENTATION: YoloSegmentationService(),
    RecognitionMethod.SAM_SEGMENTATION: SamSegmentationService(),
    RecognitionMethod.MULTIMODAL: MultimodalService(),
}

DETECTION_TYPE_MAP = {
    1: RecognitionMethod.YOLO_DETECTION,
    2: RecognitionMethod.YOLO_SEGMENTATION,
    3: RecognitionMethod.SAM_SEGMENTATION,
    4: RecognitionMethod.MULTIMODAL,
}


def get_detection_type(method_value) -> RecognitionMethod | None:
    val = DETECTION_TYPE_MAP.get(method_value)
    if val:
        return val
    try:
        return RecognitionMethod(method_value)
    except ValueError:
        return None


def update_task_progress(task, task_id: str, meta: dict) -> None:
    """更新任务进度；遇到历史非法 FAILURE 结果时清理后重写。"""
    try:
        task.update_state(state="PROGRESS", meta=meta)
    except ValueError as exc:
        if "Exception information must include the exception type" not in str(exc):
            raise

        logger.warning(
            "Task %s: clearing invalid celery backend state before progress update",
            task_id,
        )
        task.backend.forget(task_id)
        task.update_state(state="PROGRESS", meta=meta)


async def process_single_image(
    service,
    url,
    prompt_or_model,
    confidence,
    project_name="通用",
    category_name="",
):
    """异步处理单张图片"""
    image, ext = download_image(url)
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


async def process_single_image_with_retry(
    service,
    url,
    prompt_or_model,
    confidence,
    project_name,
    category_name,
    task_id: str,
    image_index: int,
):
    """处理单张图片；失败时只重试当前图片，不重跑整个任务。"""
    max_attempts = max(config.IMAGE_RETRY_MAX_ATTEMPTS, 1)
    retry_delay = max(config.IMAGE_RETRY_DELAY_SECONDS, 0)

    for attempt in range(1, max_attempts + 1):
        try:
            return await process_single_image(
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
                "Task %s: image %d failed attempt %d/%d, retrying in %ss url=%s error=%s",
                task_id,
                image_index,
                attempt,
                max_attempts,
                retry_delay,
                url,
                exc,
            )
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)


@celery_app.task(
    name=config.RECOGNIZE_IMAGE_TASK_NAME,
    bind=True,
    default_retry_delay=30,
    max_retries=3,
)
def recognize_image(self, **kwargs) -> dict:
    task_id = kwargs.get("task_id", self.request.id)
    total = 0
    processed_count = 0
    db = None
    service = None
    try:
        method_value = kwargs.get("detection_type")
        detection_type = get_detection_type(method_value)
        if detection_type is None:
            raise ValueError(f"Invalid detection_type: {method_value}")

        prompt_or_model = kwargs.get("text", "")
        images = kwargs.get("images", [])
        confidence = kwargs.get("confidence", 0.5)
        project_name = kwargs.get("project_name") or "通用"
        category_name = kwargs.get("category_name") or ""

        if not images:
            logger.error("Task %s: images is required", task_id)
            return {
                "task_id": task_id,
                "progress": {"processed": 0, "total": 0, "percent": 0},
            }

        if (
            detection_type
            in (
                RecognitionMethod.SAM_SEGMENTATION,
                RecognitionMethod.MULTIMODAL,
            )
            and not prompt_or_model
        ):
            logger.error("Task %s: text is required for this detection type", task_id)
            return {
                "task_id": task_id,
                "progress": {"processed": 0, "total": 0, "percent": 0},
            }

        service = SERVICE_MAP[detection_type]
        total = len(images)
        db = SessionLocal()

        def mark_result_storage_failed(error: str) -> None:
            try:
                fail_recognition_result_storage(task_id, error, db)
            except Exception:
                logger.exception(
                    "Task %s: failed to mark recognition storage failed",
                    task_id,
                )

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
                detection_type.value,
                prompt_or_model,
            )
            result_batch.clear()

        async def process_all():
            nonlocal processed_count
            update_task_progress(
                self,
                task_id,
                {
                    "processed": 0,
                    "total": total,
                    "percent": 0,
                },
            )
            await wait_for_resources(task_id, 1)

            for i, url in enumerate(images):
                logger.info(
                    "Task %s: Processing image %s (%d/%d)",
                    task_id,
                    url,
                    i + 1,
                    total,
                )

                response = await process_single_image_with_retry(
                    service,
                    url,
                    prompt_or_model,
                    confidence,
                    project_name,
                    category_name,
                    task_id,
                    i + 1,
                )
                sr = service.serialize_response(response)
                sr["url"] = url
                sr["image_index"] = i

                if store_results_in_db:
                    result_batch.append(sr)
                    if len(result_batch) >= result_batch_size:
                        flush_result_batch()
                else:
                    serialized_results.append(sr)

                processed_count += 1

                update_task_progress(
                    self,
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
            "detection_type": detection_type.value,
            "service": detection_type.value,
            "prompt_or_model": prompt_or_model,
            "image_count": processed_count,
            "result_storage": "recognition_image_results",
            "progress": {"processed": total, "total": total, "percent": 100},
        }

        if store_results_in_db:
            complete_recognition_result_storage(task_id, result_summary, db)
            result_data = result_summary
        else:
            result_data = {
                "task_id": task_id,
                "detection_type": detection_type.value,
                "prompt_or_model": prompt_or_model,
                "image_count": processed_count,
                "results": serialized_results,
                "progress": {"processed": total, "total": total, "percent": 100},
            }

        # 暂停任务完成后的结果队列投递；当前阶段只需要 worker 入库。
        publish_result_queue = False
        if publish_result_queue:
            try:
                if store_results_in_db:
                    publish_result(result_data)
                else:
                    publish_result(compact_recognition_result(result_data))
            except Exception:
                logger.exception("Failed to publish result for task %s", task_id)

        # 查询接口只返回 progress，Redis 中只需存储这部分
        return {
            "task_id": task_id,
            "progress": {"processed": total, "total": total, "percent": 100},
        }

    except ImageProcessingRetriesExhausted as e:
        logger.exception("Task %s failed, dead-lettering: %s", task_id, e)
        if db is not None:
            db.rollback()
            mark_result_storage_failed(str(e))
        raise Reject(str(e), requeue=False) from e
    except Exception as e:
        if db is not None:
            db.rollback()
        if self.request.retries >= self.max_retries:
            logger.exception(
                "Task %s exhausted whole-task retries, dead-lettering: %s",
                task_id,
                e,
            )
            if db is not None:
                mark_result_storage_failed(str(e))
            raise Reject(str(e), requeue=False) from e

        logger.exception("Task %s failed: %s", task_id, e)
        raise self.retry(exc=e)
    finally:
        if service is not None:
            try:
                service.release_resources()
            except Exception:
                logger.exception(
                    "Task %s: failed to release recognition resources",
                    task_id,
                )
        if db is not None:
            db.close()
