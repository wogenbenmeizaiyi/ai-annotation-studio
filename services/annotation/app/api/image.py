import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.models.api_response import ApiResponse
from app.models.annotation import CocoCategory
from app.services.image_store import ImageStore
from app.services.task_store import TaskStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image", tags=["Image"])
image_store = ImageStore()
task_store = TaskStore()


@router.post("/upload")
async def upload_image(
    task_name: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """
    上传图片到RustFS并在数据库创建记录，返回含预签名URL的图片信息
    """
    if not files:
        raise HTTPException(status_code=400, detail="No file uploaded")

    task_data = task_store.get_by_name(task_name)
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在")

    categories = [
        CocoCategory(
            id=c["id"], name=c["name"], supercategory=c.get("supercategory", "")
        )
        for c in task_data.get("categories", [])
    ]

    detection_type = task_data.get("detection_type", "")

    results = []
    for file in files:
        try:
            image_bytes = await file.read()
            if not image_bytes:
                continue

            response = image_store.upload_image(
                task_name=task_name,
                image_data=image_bytes,
                original_name=file.filename,
                detection_type=detection_type,
                categories=categories,
            )

            if response.success:
                results.append(response.data)
            else:
                results.append({"error": response.message})

        except Exception as e:
            logger.error(f"图片上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    return ApiResponse.success_response(
        data={"count": len(results), "files": results},
        message="图片上传完成",
    )


@router.get("/get/{image_id}")
def get_image(image_id: int):
    """
    获取单张图片信息（含RustFS预签名访问URL）
    """
    data = image_store.get_image_with_url(image_id)
    if not data:
        raise HTTPException(status_code=404, detail="图片不存在")

    return ApiResponse.success_response(data=data, message="获取图片信息成功")


@router.get("/list/{task_name}")
def get_image_list_by_task(
    task_name: str,
    page: int | None = None,
    page_size: int | None = None,
):
    if page is None or page_size is None:
        data = image_store.get_image_list_by_task_name(task_name)
        if not data:
            return ApiResponse.error_response(
                message="任务图片列表为空或任务不存在", code=404
            )
        return ApiResponse.success_response(data=data, message="获取图片列表成功")

    images, total, annotated_count = image_store.get_images_by_task_name_paged(
        task_name, page, page_size
    )

    return ApiResponse.success_response(
        data={
            "list": images,
            "page": page,
            "page_size": page_size,
            "total": total,
            "annotated_count": annotated_count,
            "total_pages": (total + page_size - 1) // page_size,
        },
        message="获取图片列表成功",
    )


@router.delete("/delete/{image_id}")
def delete_image(image_id: int):
    """
    删除图片（逻辑删除）
    """
    return image_store.delete_image(image_id)
