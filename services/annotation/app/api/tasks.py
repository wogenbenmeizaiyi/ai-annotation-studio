from fastapi import APIRouter

from app.models.annotation import CocoCategory
from app.models.api_response import ApiResponse
from app.schemas.task import TaskCreateRequest, CocoCategoryRequest
from app.services.task_store import TaskStore

task_store = TaskStore()
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/create")
def create_task(req: TaskCreateRequest):
    categories = [
        CocoCategory(id=c.id or 0, name=c.name, supercategory=c.supercategory or "")
        for c in req.categories
    ]

    return task_store.create_task(
        name=req.name,
        description=req.description,
        detection_type=req.detection_type,
        categories=categories,
    )


@router.put("/update")
def update_task(req: TaskCreateRequest):
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
def delete_task(name: str):
    return task_store.delete_task(name)


@router.get("/list")
def list_tasks():
    return ApiResponse.success_response(data=task_store.load_all())


@router.get("/task")
def get_task(name: str):
    data = task_store.get_by_name(name)
    if not data:
        return ApiResponse.error_response(message=f"任务未找到: {name}", code=404)
    return ApiResponse.success_response(data=data)
