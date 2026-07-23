import math
import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from core.db import get_db
from core.auth import AuthContext, get_request_auth, require_owner
from core.schemas.recognition import (
    RecognitionCombination,
    RecognitionCombinationModel,
    RecognitionModelConfig,
)

router = APIRouter(tags=["combinations"])


@dataclass
class RecognitionCombinationCreateRequest:
    name: str
    model_uuids: list[str]
    project_name: str = "通用"
    description: str = ""


@dataclass
class RecognitionCombinationUpdateRequest:
    name: str | None = None
    model_uuids: list[str] | None = None
    project_name: str | None = None
    description: str | None = None
    is_deleted: bool | None = None


def _datetime_to_text(value) -> str | None:
    return value.isoformat() if value else None


def _serialize_model(row: RecognitionModelConfig) -> dict:
    return {
        "uuid": row.uuid,
        "name": row.name,
        "detection_type": row.detection_type,
        "prompt": row.prompt,
        "model_file": row.model_file,
        "storage_key": row.storage_key,
        "project_name": row.project_name,
        "description": row.description,
    }


def _serialize_combination(row: RecognitionCombination, auth: AuthContext) -> dict:
    return {
        "uuid": row.uuid,
        "name": row.name,
        "project_name": row.project_name,
        "description": row.description,
        "is_deleted": row.is_deleted,
        "owner_subject_id": row.owner_subject_id,
        "can_manage": auth.can_manage(row.owner_subject_id),
        "models": [_serialize_model(link.model) for link in row.model_links],
        "created_at": _datetime_to_text(row.created_at),
        "updated_at": _datetime_to_text(row.updated_at),
    }


def _get_combination(
    combination_uuid: str,
    db: Session,
) -> RecognitionCombination:
    row = (
        db.query(RecognitionCombination)
        .options(
            selectinload(RecognitionCombination.model_links).selectinload(
                RecognitionCombinationModel.model
            )
        )
        .filter(RecognitionCombination.uuid == combination_uuid)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="综合检测配置不存在")
    return row


def _resolve_models(
    model_uuids: list[str], db: Session
) -> list[RecognitionModelConfig]:
    if not model_uuids:
        raise HTTPException(status_code=400, detail="模型列表不能为空")
    if len(model_uuids) != len(set(model_uuids)):
        raise HTTPException(status_code=400, detail="模型列表不能包含重复 UUID")

    rows = (
        db.query(RecognitionModelConfig)
        .filter(
            RecognitionModelConfig.uuid.in_(model_uuids),
            RecognitionModelConfig.is_deleted.is_(False),
        )
        .all()
    )
    models_by_uuid = {row.uuid: row for row in rows}
    missing_uuids = [item for item in model_uuids if item not in models_by_uuid]
    if missing_uuids:
        raise HTTPException(
            status_code=400,
            detail=f"模型不存在或已删除: {', '.join(missing_uuids)}",
        )
    return [models_by_uuid[item] for item in model_uuids]


def _sync_models(
    row: RecognitionCombination,
    models: list[RecognitionModelConfig],
) -> None:
    """按请求列表同步关联，保留未变模型的关联记录。"""
    links_by_model_uuid = {link.model.uuid: link for link in row.model_links}
    target_uuids = {model.uuid for model in models}

    for link in list(row.model_links):
        if link.model.uuid not in target_uuids:
            row.model_links.remove(link)

    for index, model in enumerate(models):
        link = links_by_model_uuid.get(model.uuid)
        if link is None:
            row.model_links.append(
                RecognitionCombinationModel(model=model, sort_order=index)
            )
        else:
            link.sort_order = index


@router.post("")
async def create_recognition_combination(
    payload: RecognitionCombinationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    auth = get_request_auth(request)
    models = _resolve_models(payload.model_uuids, db)
    row = RecognitionCombination(
        uuid=str(uuid.uuid4()),
        name=payload.name,
        project_name=payload.project_name,
        description=payload.description,
        is_deleted=False,
        owner_subject_id=auth.subject_id,
    )
    _sync_models(row, models)
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="综合检测配置已存在") from exc

    return _serialize_combination(_get_combination(row.uuid, db), auth)


@router.get("")
async def list_recognition_combinations(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=500),
    project_name: str | None = Query(None, alias="projectName"),
    include_deleted: bool = Query(False, alias="includeDeleted"),
    db: Session = Depends(get_db),
) -> dict:
    auth = get_request_auth(request)
    query = db.query(RecognitionCombination)
    if not include_deleted:
        query = query.filter(RecognitionCombination.is_deleted.is_(False))
    if project_name:
        query = query.filter(RecognitionCombination.project_name == project_name)

    total = query.count()
    rows = (
        query.options(
            selectinload(RecognitionCombination.model_links).selectinload(
                RecognitionCombinationModel.model
            )
        )
        .order_by(RecognitionCombination.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "page": page,
        "pageSize": page_size,
        "totalPages": math.ceil(total / page_size) if total else 0,
        "total": total,
        "items": [_serialize_combination(row, auth) for row in rows],
    }


@router.get("/detail")
async def get_recognition_combination(
    request: Request,
    uuid: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    auth = get_request_auth(request)
    return _serialize_combination(_get_combination(uuid, db), auth)


@router.put("")
async def update_recognition_combination(
    payload: RecognitionCombinationUpdateRequest,
    request: Request,
    uuid: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    auth = get_request_auth(request)
    row = _get_combination(uuid, db)
    require_owner(auth, row.owner_subject_id)
    if payload.model_uuids is not None:
        _sync_models(row, _resolve_models(payload.model_uuids, db))

    for field_name in ("name", "project_name", "description", "is_deleted"):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(row, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="综合检测配置更新失败") from exc

    return _serialize_combination(_get_combination(uuid, db), auth)


@router.delete("")
async def delete_recognition_combination(
    request: Request,
    uuid: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    auth = get_request_auth(request)
    row = _get_combination(uuid, db)
    require_owner(auth, row.owner_subject_id)
    row.is_deleted = True
    db.commit()
    return {"deleted": True, "uuid": uuid}
