import math
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import config
from core.db import get_db
from core.s3.s3_client import s3
from core.schemas.recognition import RecognitionModelConfig
from core.storage.model_cache import SAM_DEFAULT_MODEL_FILE, SAM_DEFAULT_STORAGE_KEY

router = APIRouter(tags=["models"])

MODEL_STORAGE_PREFIX_BY_TYPE = {
    1: "平台/yolo/model",
    2: "平台/yolo/model",
    3: "平台/sam/model",
    4: "平台/multimodal/model",
}


@dataclass
class RecognitionModelCreateRequest:
    name: str
    detection_type: int
    uuid: str | None = None
    prompt: str | None = None
    model_file: str | None = None
    storage_key: str | None = None
    project_name: str = "通用"
    is_deleted: bool = False
    description: str = ""


@dataclass
class RecognitionModelUpdateRequest:
    name: str | None = None
    detection_type: int | None = None
    prompt: str | None = None
    model_file: str | None = None
    storage_key: str | None = None
    project_name: str | None = None
    is_deleted: bool | None = None
    description: str | None = None


def _datetime_to_text(value: Any) -> str | None:
    return value.isoformat() if value else None


def _serialize_model(row: RecognitionModelConfig) -> dict:
    return {
        "id": row.id,
        "uuid": row.uuid,
        "name": row.name,
        "detection_type": row.detection_type,
        "prompt": row.prompt,
        "model_file": row.model_file,
        "storage_key": row.storage_key,
        "project_name": row.project_name,
        "is_deleted": row.is_deleted,
        "description": row.description,
        "created_at": _datetime_to_text(row.created_at),
        "updated_at": _datetime_to_text(row.updated_at),
    }


def _build_model_storage_key(detection_type: int, model_file: str) -> str:
    prefix = MODEL_STORAGE_PREFIX_BY_TYPE.get(detection_type)
    if prefix is None:
        raise HTTPException(status_code=400, detail="不支持的识别类型")
    return str(PurePosixPath(prefix) / model_file)


def _commit_model(db: Session, row: RecognitionModelConfig) -> dict:
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="recognition model config already exists",
        ) from exc
    return _serialize_model(row)


@router.post("")
async def create_recognition_model(
    request: RecognitionModelCreateRequest,
    db: Session = Depends(get_db),
) -> dict:
    model_file = request.model_file
    storage_key = request.storage_key
    if request.detection_type == 3:
        model_file = SAM_DEFAULT_MODEL_FILE
        storage_key = SAM_DEFAULT_STORAGE_KEY

    row = RecognitionModelConfig(
        uuid=request.uuid or str(uuid.uuid4()),
        name=request.name,
        detection_type=request.detection_type,
        prompt=request.prompt,
        model_file=model_file,
        storage_key=storage_key,
        project_name=request.project_name,
        is_deleted=request.is_deleted,
        description=request.description,
    )
    return _commit_model(db, row)


@router.get("")
async def list_recognition_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=500),
    detection_type: int | None = Query(None),
    include_deleted: bool = Query(False, alias="includeDeleted"),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(RecognitionModelConfig)
    if not include_deleted:
        query = query.filter(RecognitionModelConfig.is_deleted.is_(False))
    if detection_type is not None:
        query = query.filter(RecognitionModelConfig.detection_type == detection_type)

    total = query.count()
    rows = (
        query.order_by(RecognitionModelConfig.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "page": page,
        "pageSize": page_size,
        "totalPages": math.ceil(total / page_size) if total else 0,
        "total": total,
        "items": [_serialize_model(row) for row in rows],
    }


@router.post("/upload")
async def upload_recognition_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    detection_type: int = Form(...),
    prompt: str | None = Form(None),
    project_name: str = Form("通用"),
    description: str = Form(""),
    storage_key: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    model_uuid = str(uuid.uuid4())
    if detection_type == 3:
        model_file = SAM_DEFAULT_MODEL_FILE
        object_key = SAM_DEFAULT_STORAGE_KEY
    else:
        suffix = PurePosixPath(file.filename or "").suffix or ".pt"
        model_file = f"{model_uuid}{suffix}"
        object_key = storage_key or _build_model_storage_key(
            detection_type,
            model_file,
        )

    try:
        await file.seek(0)
        s3.upload_fileobj(file.file, config.S3_BUCKET, object_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="模型文件上传失败") from exc

    row = RecognitionModelConfig(
        uuid=model_uuid,
        name=name,
        detection_type=detection_type,
        prompt=prompt,
        model_file=model_file,
        storage_key=object_key,
        project_name=project_name,
        is_deleted=False,
        description=description,
    )
    return _commit_model(db, row)


@router.get("/{model_uuid}")
async def get_recognition_model(
    model_uuid: str,
    db: Session = Depends(get_db),
) -> dict:
    row = (
        db.query(RecognitionModelConfig)
        .filter(RecognitionModelConfig.uuid == model_uuid)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="recognition model not found")
    return _serialize_model(row)


@router.put("/{model_uuid}")
async def update_recognition_model(
    model_uuid: str,
    request: RecognitionModelUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    row = (
        db.query(RecognitionModelConfig)
        .filter(RecognitionModelConfig.uuid == model_uuid)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="recognition model not found")

    for field_name in (
        "name",
        "detection_type",
        "prompt",
        "model_file",
        "storage_key",
        "project_name",
        "is_deleted",
        "description",
    ):
        value = getattr(request, field_name)
        if value is not None:
            setattr(row, field_name, value)

    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="recognition model config already exists",
        ) from exc
    return _serialize_model(row)


@router.delete("/{model_uuid}")
async def delete_recognition_model(
    model_uuid: str,
    db: Session = Depends(get_db),
) -> dict:
    row = (
        db.query(RecognitionModelConfig)
        .filter(RecognitionModelConfig.uuid == model_uuid)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="recognition model not found")

    row.is_deleted = True
    db.commit()
    return {"deleted": True, "uuid": model_uuid}
