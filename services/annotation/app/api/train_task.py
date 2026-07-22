import asyncio
import json

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.s3.s3_client import S3Client
from app.db.database import SessionLocal
from app.schemas.train_task import CreateTaskRequest
from app.models.api_response import ApiResponse
from app.models.task import TaskModel
from app.models.train_task import TrainTaskModel
from app.models.training_metric import TrainingMetricModel
from app.services.YOLO.train_task_service import TrainTaskService, sanitize_json_value

train_task_service = TrainTaskService()

router = APIRouter(prefix="/train", tags=["Train"])


def _api_response(response: ApiResponse) -> JSONResponse:
    return JSONResponse(content=sanitize_json_value(asdict(response)))


def _sse_data(data: dict) -> str:
    safe_data = sanitize_json_value(data)
    return f"data: {json.dumps(safe_data, ensure_ascii=False, allow_nan=False)}\n\n"


@router.post("/create")
def create_task(request: CreateTaskRequest):
    try:
        task_id = train_task_service.start_training(request)
        return _api_response(
            ApiResponse.success_response(
                data={"task_id": task_id},
                message="训练任务已进入队列",
            )
        )
    except Exception as e:
        return _api_response(ApiResponse.error_response(str(e)))


@router.get("/list")
def list_train_tasks(task_name: Optional[str] = None):
    """查询训练任务列表

    - 不传 task_name：返回所有训练任务（按创建时间倒序）
    - 传 task_name：返回该标注任务下的所有训练记录
    """
    db: Session = SessionLocal()
    try:
        query = db.query(TrainTaskModel).filter(TrainTaskModel.is_deleted == False)

        if task_name:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return _api_response(ApiResponse.success_response(data=[]))
            query = query.filter(TrainTaskModel.task_id == task.id)

        tasks = query.order_by(TrainTaskModel.created_at.desc()).all()
        return _api_response(
            ApiResponse.success_response(data=[t.to_dict() for t in tasks])
        )
    except Exception as e:
        return _api_response(ApiResponse.error_response(f"查询失败: {e}", code=500))
    finally:
        db.close()


@router.get("/{task_id}/stream")
async def stream_training(task_id: int):
    """SSE 端点：实时推送训练进度

    客户端可以随时连接：
    - 训练中：每轮推送完整指标列表
    - 训练完成：推送最终结果后关闭
    """
    queue = train_task_service.task_repo.subscribe(task_id)

    async def event_generator():
        try:
            # 先推送当前已有的指标（处理连接时训练已完成或正在进行的情况）
            existing_metrics = train_task_service.task_repo.get_epoch_metrics(task_id)
            status = _get_task_status(task_id)
            yield _sse_data({"status": status, "metrics": existing_metrics})
            if status in ("FINISHED", "ERROR", "CANCELLED"):
                return

            # 持续监听新事件
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield _sse_data(event)

                    # 训练结束，关闭连接
                    if event.get("status") in ("FINISHED", "ERROR", "CANCELLED"):
                        break
                except asyncio.TimeoutError:
                    # 30秒无新数据，发送心跳
                    yield ": heartbeat\n\n"
        except Exception:
            pass
        finally:
            train_task_service.task_repo.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}/metrics")
def get_training_metrics(task_id: int):
    """查询某训练任务的所有轮次指标（从数据库）"""
    db: Session = SessionLocal()
    try:
        task = (
            db.query(TrainTaskModel)
            .filter(TrainTaskModel.id == task_id, TrainTaskModel.is_deleted == False)
            .first()
        )
        if not task:
            return _api_response(ApiResponse.error_response("训练任务不存在", code=404))

        metrics = (
            db.query(TrainingMetricModel)
            .filter(
                TrainingMetricModel.train_task_id == task_id,
                TrainingMetricModel.is_deleted == False,
            )
            .order_by(TrainingMetricModel.epoch)
            .all()
        )

        result = {
            "task": task.to_dict(),
            "metrics": [m.to_dict() for m in metrics],
        }
        return _api_response(ApiResponse.success_response(data=result))
    except Exception as e:
        return _api_response(ApiResponse.error_response(f"查询失败: {e}", code=500))
    finally:
        db.close()


@router.get("/{task_id}/model/download")
def download_model(task_id: int):
    """获取训练模型的 S3 预签名下载链接"""
    db: Session = SessionLocal()
    try:
        task = (
            db.query(TrainTaskModel)
            .filter(TrainTaskModel.id == task_id, TrainTaskModel.is_deleted == False)
            .first()
        )
        if not task:
            return _api_response(ApiResponse.error_response("训练任务不存在", code=404))

        if task.status != "FINISHED" or not task.output_path:
            return _api_response(ApiResponse.error_response("模型文件尚未生成", code=404))

        s3_client = S3Client()
        download_url = s3_client.generate_presigned_url(
            bucket=settings.S3_BUCKET_NAME,
            key=task.output_path,
            expires_in=3600,
        )
        return _api_response(
            ApiResponse.success_response(
                data={
                    "download_url": download_url,
                    "expires_in": 3600,
                    "model_name": task.model_name,
                    "filename": task.output_path.rsplit("/", 1)[-1],
                }
            )
        )
    except Exception as e:
        return _api_response(
            ApiResponse.error_response(f"生成下载链接失败: {e}", code=500)
        )
    finally:
        db.close()


@router.delete("/{task_id}")
def delete_train_task(task_id: int):
    """逻辑删除训练任务及其每轮指标（模型文件保留在 S3 上）"""
    db: Session = SessionLocal()
    try:
        task = (
            db.query(TrainTaskModel)
            .filter(TrainTaskModel.id == task_id, TrainTaskModel.is_deleted == False)
            .first()
        )
        if not task:
            return _api_response(ApiResponse.error_response("训练任务不存在", code=404))
        if task.status in ("CLAIMED", "RUNNING", "RECOVERING"):
            return _api_response(ApiResponse.error_response("运行中的训练任务不能删除", code=409))

        was_queued = task.status == "QUEUED"
        if was_queued:
            task.status = "CANCELLED"
        task.is_deleted = True

        # 级联逻辑删除关联的每轮指标
        db.query(TrainingMetricModel).filter(
            TrainingMetricModel.train_task_id == task_id
        ).update({TrainingMetricModel.is_deleted: True})

        db.commit()
        if was_queued:
            train_task_service._broadcast_status(task_id, {"status": "CANCELLED"})
        return _api_response(
            ApiResponse.success_response(data=None, message="删除成功")
        )
    except Exception as e:
        db.rollback()
        return _api_response(ApiResponse.error_response(f"删除失败: {e}", code=500))
    finally:
        db.close()


@router.post("/{task_id}/retry")
def retry_train_task(task_id: int):
    """重新启动失败或等待中的训练任务。"""
    try:
        train_task_service.retry_training_task(task_id)
        return _api_response(
            ApiResponse.success_response(
                message="训练任务已重新进入队列",
                data={"task_id": task_id},
            )
        )
    except Exception as e:
        return _api_response(ApiResponse.error_response(str(e)))


@router.get("/{task_id}")
def get_task_status(task_id: int):
    """查询训练任务状态"""
    db: Session = SessionLocal()
    try:
        task = (
            db.query(TrainTaskModel)
            .filter(TrainTaskModel.id == task_id, TrainTaskModel.is_deleted == False)
            .first()
        )
        if not task:
            return _api_response(ApiResponse.error_response("训练任务不存在", code=404))
        return _api_response(ApiResponse.success_response(data=task.to_dict()))
    except Exception as e:
        return _api_response(ApiResponse.error_response(f"查询失败: {e}", code=500))
    finally:
        db.close()


def _get_task_status(task_id: int) -> str:
    """获取任务状态（不查DB，从内存获取）"""
    tasks = train_task_service.task_repo.tasks
    if task_id in tasks:
        return tasks[task_id].get("status", "UNKNOWN")
    # fallback to DB
    db: Session = SessionLocal()
    try:
        task = (
            db.query(TrainTaskModel)
            .filter(TrainTaskModel.id == task_id, TrainTaskModel.is_deleted == False)
            .first()
        )
        return task.status if task else "UNKNOWN"
    finally:
        db.close()
