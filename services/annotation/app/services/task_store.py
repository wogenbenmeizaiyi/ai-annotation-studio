from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.api_response import ApiResponse
from app.models.task import TaskModel, CategoryModel
import app.models.image
import app.models.train_task


class TaskStore:
    def _get_category_id_map(self, db: Session, task_id: int) -> dict:
        cats = db.query(CategoryModel).filter(CategoryModel.task_id == task_id).all()
        return {c.name: c.id for c in cats}

    def _sync_categories(self, db: Session, task_id: int, categories: list):
        existing = (
            db.query(CategoryModel).filter(CategoryModel.task_id == task_id).all()
        )
        existing_names = {c.name for c in existing}

        for cat in categories:
            if cat.name not in existing_names:
                db.add(
                    CategoryModel(
                        task_id=task_id, name=cat.name, supercategory=cat.supercategory
                    )
                )

        existing_by_name = {c.name: c for c in existing}
        for cat in categories:
            if cat.name in existing_by_name:
                obj = existing_by_name[cat.name]
                obj.supercategory = cat.supercategory

    def create_task(
        self,
        name: str,
        description: str,
        detection_type: str,
        categories: Optional[List] = None,
        owner_subject_id: Optional[str] = None,
    ) -> ApiResponse:
        db: Session = SessionLocal()
        try:
            existing = (
                db.query(TaskModel)
                .filter(TaskModel.name == name, TaskModel.is_deleted == False)
                .first()
            )
            if existing:
                return ApiResponse.error_response(
                    message=f"任务名已存在: {name}", code=409
                )

            task = TaskModel(
                name=name,
                description=description,
                detection_type=detection_type,
                owner_subject_id=owner_subject_id,
            )
            db.add(task)
            db.flush()

            if categories:
                for cat in categories:
                    db.add(
                        CategoryModel(
                            task_id=task.id,
                            name=cat.name,
                            supercategory=cat.supercategory,
                        )
                    )

            db.commit()
            db.refresh(task)
            return ApiResponse.success_response(
                data=task.to_dict(), message="任务创建成功"
            )
        except Exception as e:
            db.rollback()
            return ApiResponse.error_response(
                message=f"创建任务失败: {str(e)}", code=500
            )
        finally:
            db.close()

    def update_task(
        self,
        name: str,
        detection_type: str,
        description: str,
        categories: Optional[List] = None,
    ) -> ApiResponse:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return ApiResponse.error_response(
                    message=f"任务未找到: {name}", code=404
                )

            task.description = description
            task.detection_type = detection_type
            task.updated_at = datetime.now(timezone.utc)

            if categories is not None:
                db.query(CategoryModel).filter(
                    CategoryModel.task_id == task.id
                ).delete()
                for cat in categories:
                    db.add(
                        CategoryModel(
                            task_id=task.id,
                            name=cat.name,
                            supercategory=cat.supercategory,
                        )
                    )
            db.commit()
            db.refresh(task)
            return ApiResponse.success_response(
                data=task.to_dict(), message="任务更新成功"
            )
        except Exception as e:
            db.rollback()
            return ApiResponse.error_response(
                message=f"更新任务失败: {str(e)}", code=500
            )
        finally:
            db.close()

    def delete_task(self, name: str) -> ApiResponse:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return ApiResponse.error_response(
                    message=f"任务未找到: {name}", code=404
                )

            task.is_deleted = True
            task.updated_at = datetime.now(timezone.utc)
            db.commit()
            return ApiResponse.success_response(data=None, message="任务删除成功")
        except Exception as e:
            db.rollback()
            return ApiResponse.error_response(
                message=f"删除任务失败: {str(e)}", code=500
            )
        finally:
            db.close()

    def load_all(self, viewer_subject_id: str, viewer_is_admin: bool) -> list:
        db: Session = SessionLocal()
        try:
            tasks = (
                db.query(TaskModel)
                .filter(TaskModel.is_deleted == False)
                .order_by(TaskModel.id)
                .all()
            )
            values = []
            for task in tasks:
                value = task.to_dict()
                value["can_manage"] = viewer_is_admin or (
                    task.owner_subject_id is not None
                    and task.owner_subject_id == viewer_subject_id
                )
                values.append(value)
            return values
        finally:
            db.close()

    def get_by_name(
        self,
        name: str,
        viewer_subject_id: Optional[str] = None,
        viewer_is_admin: bool = False,
    ):
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return None
            value = task.to_dict()
            if viewer_subject_id is not None:
                value["can_manage"] = viewer_is_admin or (
                    task.owner_subject_id is not None
                    and task.owner_subject_id == viewer_subject_id
                )
            return value
        finally:
            db.close()

    def _resolve_task_id(self, name: str) -> Optional[int]:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == name, TaskModel.is_deleted == False)
                .first()
            )
            return task.id if task else None
        finally:
            db.close()
