from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from core.db import get_db
from core.public_security import validate_public_images
from core.storage.model_cache import ModelUnavailableError, ensure_model_available
from core.schemas.recognition import (
    RecognitionCombination,
    RecognitionCombinationModel,
    RecognitionModelConfig,
)
from core.schemas.task import RecognitionRecordedSubmitRequest
from recognition_submission import submit_recorded_recognition

router = APIRouter(tags=["project"])


@dataclass
class ProjectRecognitionRequest:
    """项目侧识别任务请求。"""

    model_ids: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    project_name: str = "通用"


def _get_task_text(model: RecognitionModelConfig) -> str:
    if model.detection_type in (1, 2):
        if not model.model_file:
            raise HTTPException(status_code=400, detail=f"模型未配置文件: {model.uuid}")
        return Path(model.model_file).stem

    if model.detection_type == 3:
        if not model.prompt:
            raise HTTPException(
                status_code=400, detail=f"SAM 模型未配置提示词: {model.uuid}"
            )
        model_name = Path(model.model_file).stem if model.model_file else "sam3"
        return f"{model_name}|{model.prompt}"

    if model.detection_type == 4:
        if not model.prompt:
            raise HTTPException(
                status_code=400,
                detail=f"多模态模型未配置提示词: {model.uuid}",
            )
        return model.prompt

    raise HTTPException(status_code=400, detail=f"不支持的模型类型: {model.uuid}")


def _get_models(
    model_ids: list[str],
    db: Session,
) -> list[RecognitionModelConfig]:
    if not model_ids:
        raise HTTPException(status_code=400, detail="模型 UUID 列表不能为空")
    if len(model_ids) != len(set(model_ids)):
        raise HTTPException(status_code=400, detail="模型 UUID 列表不能重复")

    rows = (
        db.query(RecognitionModelConfig)
        .filter(
            RecognitionModelConfig.uuid.in_(model_ids),
            RecognitionModelConfig.is_deleted.is_(False),
        )
        .all()
    )
    models_by_uuid = {row.uuid: row for row in rows}
    missing_ids = [model_id for model_id in model_ids if model_id not in models_by_uuid]
    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"模型不存在或已删除: {', '.join(missing_ids)}",
        )
    return [models_by_uuid[model_id] for model_id in model_ids]


@router.get("/combination")
async def get_project_combination(
    uuid: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """对外查询综合检测配置及其模型子任务。"""
    combination = (
        db.query(RecognitionCombination)
        .options(
            selectinload(RecognitionCombination.model_links).selectinload(
                RecognitionCombinationModel.model
            )
        )
        .filter(
            RecognitionCombination.uuid == uuid,
            RecognitionCombination.is_deleted.is_(False),
        )
        .first()
    )
    if combination is None:
        raise HTTPException(status_code=404, detail="任务组合不存在或已删除")

    return {
        "combination": {
            "uuid": combination.uuid,
            "name": combination.name,
            "project_name": combination.project_name,
            "description": combination.description,
        },
        "sub_tasks": [
            {
                "model_uuid": link.model.uuid,
                "model_name": link.model.name,
                "detection_type": link.model.detection_type,
                "description": link.model.description,
            }
            for link in combination.model_links
        ],
    }


@router.post("/recognize")
async def submit_project_recognition(
    request: ProjectRecognitionRequest,
    db: Session = Depends(get_db),
) -> dict:
    """项目侧识别任务入口，按模型 UUID 创建识别子任务。"""
    validate_public_images(request.images)

    models = _get_models(request.model_ids, db)
    task_specs = [(model, _get_task_text(model)) for model in models]
    try:
        for model, _ in task_specs:
            ensure_model_available(model)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    items: list[dict[str, str]] = []
    try:
        for model, task_text in task_specs:
            task_id = submit_recorded_recognition(
                RecognitionRecordedSubmitRequest(
                    detection_type=model.detection_type,
                    text=task_text,
                    category_name=model.name,
                    images=request.images,
                    project_name=request.project_name,
                ),
                db,
            )
            items.append(
                {
                    "model_uuid": model.uuid,
                    "model_name": model.name,
                    "sub_task_id": task_id,
                }
            )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="创建项目识别任务失败",
        ) from exc

    return {
        "code": 200,
        "message": "success",
        "data": {"items": items},
    }
