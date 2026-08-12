import logging
import math
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from core.db import get_db
from core.storage.model_cache import ModelUnavailableError, ensure_model_available
from core.mq import (
    get_recognition_task_result,
)
from core.mq.task_routing import UnsupportedDetectionType, normalize_detection_type
from core.storage.recognition_result_storage import get_recognition_task_record
from core.config import config
from core.public_security import validate_public_images
from core.schemas.recognition import (
    RecognitionImageResult,
    RecognitionMethod,
    RecognitionModelConfig,
    RecognitionTaskRecord,
)
from core.schemas.task import (
    RecognitionRecordedSubmitRequest,
    RecognitionStatus,
    RecognitionSubmitRequest,
    TaskProgress,
    TypedRecognitionSubmitRequest,
)
from engine.services import (
    BaseRecognitionService,
    MultimodalService,
    RecognitionRequest,
    SamSegmentationService,
    YoloDetectionService,
    YoloSegmentationService,
)
from recognition_submission import (
    RecognitionTaskPublishError,
    submit_recorded_recognition,
)

router = APIRouter(tags=["recognition"])
logger = logging.getLogger(__name__)

DIRECT_SERVICE_MAP: dict[RecognitionMethod, BaseRecognitionService] = {
    RecognitionMethod.YOLO_DETECTION: YoloDetectionService(),
    RecognitionMethod.YOLO_SEGMENTATION: YoloSegmentationService(),
    RecognitionMethod.SAM_SEGMENTATION: SamSegmentationService(),
    RecognitionMethod.MULTIMODAL: MultimodalService(),
}

DIRECT_METHOD_BY_TYPE = {
    1: RecognitionMethod.YOLO_DETECTION,
    2: RecognitionMethod.YOLO_SEGMENTATION,
    3: RecognitionMethod.SAM_SEGMENTATION,
    4: RecognitionMethod.MULTIMODAL,
}


def _file_ext(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    return suffix or "jpg"


def _serialize_image_result(row: RecognitionImageResult) -> dict:
    result_payload = row.result_payload or {}
    return {
        "image_index": row.image_index,
        "url": row.source_url,
        "service": row.service,
        "detection_type": row.detection_type,
        "count": row.annotation_count,
        "image_key": row.image_key,
        "coco_key": row.coco_key,
        "images": result_payload.get("images", []),
        "annotations": result_payload.get("annotations", []),
        "categories": result_payload.get("categories", []),
        "created_at": _datetime_to_text(row.created_at),
    }


def _serialize_coco_payload(row: RecognitionImageResult) -> dict:
    result_payload = row.result_payload or {}
    return {
        "url": row.source_url,
        "images": [
            {
                "id": image.get("id"),
                "width": image.get("width"),
                "height": image.get("height"),
            }
            for image in result_payload.get("images", [])
        ],
        "annotations": result_payload.get("annotations", []),
        "categories": result_payload.get("categories", []),
    }


def _datetime_to_text(value) -> str | None:
    return value.isoformat() if value else None


def _total_pages(total: int, page_size: int) -> int:
    return math.ceil(total / page_size) if total else 0


def _paginate(query, page: int, page_size: int) -> tuple[int, int, list]:
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return total, _total_pages(total, page_size), rows


def _serialize_task_record(row: RecognitionTaskRecord) -> dict:
    request_payload = row.request_payload or {}
    result_payload = row.result_payload or {}
    image_urls = (
        request_payload.get("image_urls") or request_payload.get("images") or []
    )
    progress = result_payload.get("progress") or {}
    image_count = (
        result_payload.get("image_count") or progress.get("total") or len(image_urls)
    )
    return {
        "task_id": row.task_id,
        "status": row.status,
        "detection_type": request_payload.get("detection_type"),
        "text": request_payload.get("text"),
        "project_name": request_payload.get("project_name"),
        "image_count": image_count,
        "error": row.last_callback_error if row.status == "failed" else None,
        "completed_at": _datetime_to_text(row.completed_at),
        "created_at": _datetime_to_text(row.created_at),
        "updated_at": _datetime_to_text(row.updated_at),
    }


async def _recognize_uploaded_image(
    service: BaseRecognitionService,
    method: RecognitionMethod,
    file: UploadFile,
    text: str,
    project_name: str,
    confidence: float,
) -> dict:
    if file.content_type and not file.content_type.lower().startswith("image/"):
        raise HTTPException(status_code=415, detail="只允许上传图片文件")
    image_data = await file.read()
    if not image_data:
        raise HTTPException(status_code=400, detail="file is required")
    if len(image_data) > config.PUBLIC_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片文件不能超过 20 MB")

    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    request = RecognitionRequest(
        image_data=image_data,
        detection_type=text,
        project_name=project_name or "通用",
        confidence=confidence,
        extra={
            "image_ext": _file_ext(file.filename),
            "url": file.filename or "",
        },
    )
    try:
        response = await service.recognize(request)
        response.extra["url"] = file.filename or ""
        serialized = service.serialize_response(response)
        return {
            "task_id": "",
            "service": method.value,
            "prompt_or_model": text,
            "image_count": 1,
            "results": [serialized],
        }
    finally:
        service.release_resources()


def _get_direct_recognition_text(model: RecognitionModelConfig) -> str:
    if model.detection_type in (1, 2):
        if not model.model_file:
            raise HTTPException(status_code=400, detail="YOLO 模型未配置模型文件")
        return Path(model.model_file).stem

    if model.detection_type == 3:
        if not model.prompt:
            raise HTTPException(status_code=400, detail="SAM 模型未配置提示词")
        model_name = Path(model.model_file).stem if model.model_file else "sam3"
        return f"{model_name}|{model.prompt}"

    if model.detection_type == 4:
        if not model.prompt:
            raise HTTPException(status_code=400, detail="多模态模型未配置提示词")
        return model.prompt

    raise HTTPException(status_code=400, detail="不支持的模型识别类型")


async def _recognize_uploaded_model(
    model: RecognitionModelConfig,
    file: UploadFile,
    confidence: float,
) -> dict:
    if file.content_type and not file.content_type.lower().startswith("image/"):
        raise HTTPException(status_code=415, detail="只允许上传图片文件")
    method = DIRECT_METHOD_BY_TYPE.get(model.detection_type)
    if method is None:
        raise HTTPException(status_code=400, detail="不支持的模型识别类型")

    try:
        await asyncio.to_thread(ensure_model_available, model)
    except ModelUnavailableError as exc:
        logger.warning("public direct model unavailable model_uuid=%s", model.uuid)
        raise HTTPException(status_code=503, detail="模型暂时不可用") from exc

    image_data = await file.read()
    if not image_data:
        raise HTTPException(status_code=400, detail="图片文件不能为空")
    if len(image_data) > config.PUBLIC_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="图片文件不能超过 20 MB")

    service = DIRECT_SERVICE_MAP[method]
    try:
        response = await service.recognize(
            RecognitionRequest(
                image_data=image_data,
                detection_type=_get_direct_recognition_text(model),
                project_name=model.project_name or "通用",
                confidence=confidence,
                extra={
                    "image_ext": _file_ext(file.filename),
                    "url": file.filename or "",
                    "category_name": model.name,
                },
            )
        )
        response.extra["url"] = file.filename or ""
        return {
            "model": {
                "uuid": model.uuid,
                "name": model.name,
                "detection_type": model.detection_type,
            },
            "result": service.serialize_response(response),
        }
    finally:
        service.release_resources()


def _validate_task_id(task_id: str) -> None:
    try:
        value = uuid.UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="任务 UUID 无效") from exc
    if value.version != 4 or str(value) != task_id.lower():
        raise HTTPException(status_code=400, detail="任务 UUID 必须是标准 UUIDv4")


@router.post("/recognize")
async def submit_recognition(
    request: RecognitionSubmitRequest,
    db: Session = Depends(get_db),
):
    """提交识别任务，并记录任务状态。"""
    validate_public_images(request.images)
    try:
        detection_type = normalize_detection_type(request.detection_type)
    except UnsupportedDetectionType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _submit_recorded_request(
        RecognitionRecordedSubmitRequest(
            detection_type=detection_type,
            text=request.text,
            images=request.images,
            project_name=request.project_name,
        ),
        db,
    )


def _submit_recorded_request(
    request: RecognitionRecordedSubmitRequest,
    db: Session,
) -> dict:
    validate_public_images(request.images)
    logger.info("submit recognition request received")
    try:
        task_id = submit_recorded_recognition(request, db)
    except UnsupportedDetectionType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RecognitionTaskPublishError as exc:
        raise HTTPException(
            status_code=503,
            detail="recognition task broker unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("submit recognition request failed")
        raise HTTPException(
            status_code=500, detail="failed to save task record"
        ) from exc

    logger.info("submit recognition request accepted task_id=%s", task_id)
    return RecognitionStatus(task_id=task_id, status="pending").to_response()


@router.post("/recognize/yolo-detection")
async def submit_yolo_detection(
    request: TypedRecognitionSubmitRequest,
    db: Session = Depends(get_db),
):
    """提交 YOLO 目标检测任务，并记录任务状态。"""
    return _submit_recorded_request(request.to_recorded_request(1), db)


@router.post("/recognize/yolo-segmentation")
async def submit_yolo_segmentation(
    request: TypedRecognitionSubmitRequest,
    db: Session = Depends(get_db),
):
    """提交 YOLO 实例分割任务，并记录任务状态。"""
    return _submit_recorded_request(request.to_recorded_request(2), db)


@router.post("/recognize/sam-segmentation")
async def submit_sam_segmentation(
    request: TypedRecognitionSubmitRequest,
    db: Session = Depends(get_db),
):
    """提交 SAM 分割任务，并记录任务状态。"""
    return _submit_recorded_request(request.to_recorded_request(3), db)


@router.post("/recognize/multimodal")
async def submit_multimodal(
    request: TypedRecognitionSubmitRequest,
    db: Session = Depends(get_db),
):
    """提交多模态识别任务，并记录任务状态。"""
    return _submit_recorded_request(request.to_recorded_request(4), db)


@router.get("/result")
async def get_result(
    task_id: str = Query(...),
    db: Session = Depends(get_db),
):
    _validate_task_id(task_id)

    record = get_recognition_task_record(task_id, db)
    if record is not None:
        record_status = (record.status or "").lower()
        progress = TaskProgress(
            processed=0,
            total=0,
            percent=0,
        )
        if record_status in {"success", "failed"}:
            return RecognitionStatus(
                task_id=task_id,
                status=record_status,
                error=record.last_callback_error if record_status == "failed" else None,
                progress=progress,
            ).to_response()
        if record_status == "processing":
            return RecognitionStatus(
                task_id=task_id,
                status="processing",
                progress=progress,
            ).to_response()

    result = get_recognition_task_result(task_id)

    try:
        state = result.state
    except Exception:
        logger.warning(
            "recognition result meta unreadable task_id=%s, falling back to db status",
            task_id,
        )
        if record is not None:
            return RecognitionStatus(
                task_id=task_id,
                status=(record.status or "pending").lower(),
                error=record.last_callback_error if record.status == "failed" else None,
            ).to_response()
        raise HTTPException(status_code=404, detail="任务不存在")

    if state == "PENDING":
        return RecognitionStatus(task_id=task_id, status="pending").to_response()

    if state == "PROGRESS":
        try:
            meta = result.info or {}
        except Exception:
            meta = {}
        return RecognitionStatus(
            task_id=task_id,
            status="processing",
            progress=TaskProgress(
                processed=meta.get("processed", 0),
                total=meta.get("total", 0),
                percent=meta.get("percent", 0),
            ),
        ).to_response()

    if state == "SUCCESS":
        try:
            task_result = result.get()
        except Exception:
            task_result = {}
        progress = (
            task_result.get("progress", {}) if isinstance(task_result, dict) else {}
        )
        return RecognitionStatus(
            task_id=task_id,
            status="success",
            progress=TaskProgress(
                processed=progress.get("processed", 0),
                total=progress.get("total", 0),
                percent=progress.get("percent", 0),
            ),
        ).to_response()

    if state == "FAILURE":
        try:
            meta = result.info if isinstance(result.info, dict) else {}
        except Exception:
            meta = {}
        return RecognitionStatus(
            task_id=task_id,
            status="failed",
            error="识别任务执行失败",
            progress=TaskProgress(
                processed=meta.get("processed", 0),
                total=meta.get("total", 0),
                percent=meta.get("percent", 0),
            ),
        ).to_response()

    return RecognitionStatus(task_id=task_id, status=state.lower()).to_response()


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=500),
    created_at_start: datetime | None = Query(None, alias="createdAtStart"),
    created_at_end: datetime | None = Query(None, alias="createdAtEnd"),
    status: Literal["pending", "processing", "success", "failed"] | None = Query(None),
    detection_type: int | None = Query(None, alias="detectionType", ge=1, le=4),
    project_name: str | None = Query(None, alias="projectName"),
    db: Session = Depends(get_db),
):
    """分页查询所有已入库的识别任务。"""
    if created_at_start and created_at_end and created_at_start > created_at_end:
        raise HTTPException(status_code=400, detail="创建时间起始值不能晚于结束值")

    query = db.query(RecognitionTaskRecord)
    if created_at_start:
        query = query.filter(RecognitionTaskRecord.created_at >= created_at_start)
    if created_at_end:
        query = query.filter(RecognitionTaskRecord.created_at <= created_at_end)
    if status:
        query = query.filter(RecognitionTaskRecord.status == status)
    if detection_type is not None:
        query = query.filter(
            RecognitionTaskRecord.request_payload["detection_type"].astext
            == str(detection_type)
        )
    if project_name and project_name.strip():
        query = query.filter(
            RecognitionTaskRecord.request_payload["project_name"].astext.ilike(
                f"%{project_name.strip()}%"
            )
        )

    query = query.order_by(RecognitionTaskRecord.created_at.desc())
    total, total_pages, rows = _paginate(query, page, page_size)
    return {
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "total": total,
        "items": [_serialize_task_record(row) for row in rows],
    }


@router.get("/tasks/results")
async def list_task_results(
    task_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=500),
    db: Session = Depends(get_db),
):
    """分页查询单个任务的所有识别结果。"""
    return _list_task_image_results(task_id, page, page_size, db)


def _list_task_image_results(
    task_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> dict:
    query = db.query(RecognitionImageResult).filter(
        RecognitionImageResult.task_id == task_id
    )
    query = query.order_by(RecognitionImageResult.image_index.asc())
    total, total_pages, rows = _paginate(query, page, page_size)
    return {
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "total": total,
        "items": [_serialize_image_result(row) for row in rows],
    }


@router.get("/tasks/coco")
async def list_task_coco_results(
    task_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=500),
    db: Session = Depends(get_db),
):
    """通过查询参数分页查询单个任务的对外 COCO 结果。"""
    _validate_task_id(task_id)
    return _list_task_coco_results(task_id, page, page_size, db)


def _list_task_coco_results(
    task_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> dict:
    query = db.query(RecognitionImageResult).filter(
        RecognitionImageResult.task_id == task_id
    )
    query = query.order_by(RecognitionImageResult.image_index.asc())
    total, total_pages, rows = _paginate(query, page, page_size)
    return {
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "total": total,
        "item": [_serialize_coco_payload(row) for row in rows],
    }


@router.post("/recognize/direct")
async def recognize_model_direct(
    model_uuid: str = Form(...),
    file: UploadFile = File(...),
    confidence: float = Form(0.5),
    db: Session = Depends(get_db),
) -> dict:
    """按模型 UUID 同步识别单张图片，不创建任务或投递消息队列。"""
    model = (
        db.query(RecognitionModelConfig)
        .filter(
            RecognitionModelConfig.uuid == model_uuid,
            RecognitionModelConfig.is_deleted.is_(False),
        )
        .first()
    )
    if model is None:
        raise HTTPException(status_code=404, detail="模型不存在或已删除")

    return await _recognize_uploaded_model(model, file, confidence)


@router.post("/recognize/direct/yolo-detection")
async def recognize_yolo_detection_direct(
    file: UploadFile = File(...),
    text: str = Form(...),
    project_name: str = Form("通用"),
    confidence: float = Form(0.5),
):
    """直接执行 YOLO 目标检测；multipart/form-data，仅支持单张图片。"""
    return await _recognize_uploaded_image(
        DIRECT_SERVICE_MAP[RecognitionMethod.YOLO_DETECTION],
        RecognitionMethod.YOLO_DETECTION,
        file,
        text,
        project_name,
        confidence,
    )


@router.post("/recognize/direct/yolo-segmentation")
async def recognize_yolo_segmentation_direct(
    file: UploadFile = File(...),
    text: str = Form(...),
    project_name: str = Form("通用"),
    confidence: float = Form(0.5),
):
    """直接执行 YOLO 实例分割；multipart/form-data，仅支持单张图片。"""
    return await _recognize_uploaded_image(
        DIRECT_SERVICE_MAP[RecognitionMethod.YOLO_SEGMENTATION],
        RecognitionMethod.YOLO_SEGMENTATION,
        file,
        text,
        project_name,
        confidence,
    )


@router.post("/recognize/direct/sam-segmentation")
async def recognize_sam_segmentation_direct(
    file: UploadFile = File(...),
    text: str = Form(...),
    project_name: str = Form("通用"),
    confidence: float = Form(0.5),
):
    """直接执行 SAM 分割；multipart/form-data，仅支持单张图片。"""
    return await _recognize_uploaded_image(
        DIRECT_SERVICE_MAP[RecognitionMethod.SAM_SEGMENTATION],
        RecognitionMethod.SAM_SEGMENTATION,
        file,
        text,
        project_name,
        confidence,
    )


@router.post("/recognize/direct/multimodal")
async def recognize_multimodal_direct(
    file: UploadFile = File(...),
    text: str = Form(...),
    project_name: str = Form("通用"),
    confidence: float = Form(0.5),
):
    """直接执行多模态识别；multipart/form-data，仅支持单张图片。"""
    return await _recognize_uploaded_image(
        DIRECT_SERVICE_MAP[RecognitionMethod.MULTIMODAL],
        RecognitionMethod.MULTIMODAL,
        file,
        text,
        project_name,
        confidence,
    )
