from fastapi import APIRouter, Request

from app.core.auth import get_request_auth, require_task_manager
from app.models.annotation import CocoCategory
from app.models.api_response import ApiResponse
from app.schemas.task import TaskCreateRequest, CocoCategoryRequest
from app.services.task_store import TaskStore

task_store = TaskStore()
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/create")
def create_task(req: TaskCreateRequest, request: Request):
    auth = get_request_auth(request)
    categories = [
        CocoCategory(id=c.id or 0, name=c.name, supercategory=c.supercategory or "")
        for c in req.categories
    ]

    return task_store.create_task(
        name=req.name,
        description=req.description,
        detection_type=req.detection_type,
        categories=categories,
        owner_subject_id=auth.subject_id,
    )


@router.put("/update")
def update_task(req: TaskCreateRequest, request: Request):
    auth = get_request_auth(request)
    require_task_manager(req.name, auth)
    categories = (
        [
            CocoCategory(id=c.id or 0, name=c.name, supercategory=c.supercategory or "")
            for c in req.categories
        ]
        if req.categories
        else None
    )

    return task_store.update_task(
        name=req.name,
        detection_type=req.detection_type,
        description=req.description,
        categories=categories,
    )


@router.delete("/delete")
def delete_task(name: str, request: Request):
    require_task_manager(name, get_request_auth(request))
    return task_store.delete_task(name)


@router.get("/list")
def list_tasks(request: Request):
    auth = get_request_auth(request)
    return ApiResponse.success_response(
        data=task_store.load_all(auth.subject_id, auth.is_super_admin)
    )


@router.get("/task")
def get_task(name: str, request: Request):
    auth = get_request_auth(request)
    data = task_store.get_by_name(name, auth.subject_id, auth.is_super_admin)
    if not data:
        return ApiResponse.error_response(message=f"任务未找到: {name}", code=404)
    return ApiResponse.success_response(data=data)
