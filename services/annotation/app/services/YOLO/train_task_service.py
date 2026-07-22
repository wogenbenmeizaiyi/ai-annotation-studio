import json
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any, Optional

from app.db.database import SessionLocal
from app.models.train_task import TrainTaskModel
from app.models.training_metric import TrainingMetricModel
from app.schemas.train_task import CreateTaskRequest, YoloTrainConfig
from app.services.YOLO.InMemoryTaskRepo import InMemoryTaskRepo
from app.services.YOLO.yolo_dataset_builder import YoloDatasetBuilder
from app.services.task_store import TaskStore
from app.core.config import settings
from app.core.s3.s3_client import s3
from app.services.YOLO.training_worker import PostgresTrainingWorker

logger = logging.getLogger(__name__)

TRAIN_DATA_DIR = Path(settings.TRAIN_DATA_DIR)
YOLO_MODEL_DIR = Path(settings.YOLO_MODEL_DIR)
S3_BUCKET = settings.S3_BUCKET_NAME


def sanitize_json_value(value: Any) -> Any:
    """清理 NaN/Infinity 和 numpy 标量，避免输出非法 JSON。"""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Real):
        float_value = float(value)
        if not math.isfinite(float_value):
            return None
        return float_value
    if isinstance(value, dict):
        return {key: sanitize_json_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return sanitize_json_value(value.item())
        except Exception:
            return None
    return value


def to_stream_metric(metric_data: dict) -> dict:
    """SSE不携带体积较大的逐类别指标，完整数据只保存在数据库。"""
    return {key: value for key, value in metric_data.items() if key != "per_class_metrics"}


class _TrainingEpochGuard:
    """只接受与训练轮次开始事件配对的fit结束回调。"""

    def __init__(self):
        self.pending = False

    def start(self) -> None:
        self.pending = True

    def consume(self, raw_epoch: int, total_epochs: int) -> Optional[int]:
        if not self.pending:
            return None
        self.pending = False
        return min(int(raw_epoch) + 1, max(int(total_epochs), 1))


class TrainTaskService:
    def __init__(self):
        self.yolo_dataset_builder = YoloDatasetBuilder()
        self.task_repo = InMemoryTaskRepo()
        self.task_store = TaskStore()
        self.worker = PostgresTrainingWorker(self)

    def start_training(
        self,
        create_task_request: CreateTaskRequest,
        parent_train_task_id: Optional[int] = None,
    ) -> int:
        task_name = create_task_request.task_name
        cfg: YoloTrainConfig = create_task_request.config

        task_id = self.task_store._resolve_task_id(task_name)
        if task_id is None:
            raise ValueError(f"任务未找到: {task_name}")

        base_dir = TRAIN_DATA_DIR / task_name
        outputs_dir = base_dir / "outputs"
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "train.log"

        db: SessionLocal = SessionLocal()
        try:
            if parent_train_task_id is not None:
                parent_task = db.get(TrainTaskModel, parent_train_task_id)
                if (
                    not parent_task
                    or parent_task.is_deleted
                    or parent_task.task_id != task_id
                    or parent_task.status != "FINISHED"
                ):
                    raise ValueError("来源训练任务不存在、未完成或不属于当前标注任务")
            now = datetime.now(timezone.utc)
            train_task = TrainTaskModel(
                task_id=task_id,
                parent_train_task_id=parent_train_task_id,
                model_name=cfg.model,
                status="QUEUED",
                current_epoch=0,
                total_epochs=cfg.epochs,
                progress=0,
                config_json=json.dumps(cfg.model_dump()),
                log_path=str(log_path),
                output_path=str(outputs_dir),
                priority=create_task_request.priority,
                queued_at=now,
            )
            db.add(train_task)
            db.flush()
            db_train_task_id = train_task.id
            run_dir = outputs_dir / f"task_{db_train_task_id}"
            train_task.output_path = str(run_dir)
            train_task.checkpoint_path = str(run_dir / "weights" / "last.pt")
            db.commit()
        finally:
            db.close()

        logger.info(
            "训练任务已入队: db_id=%s task_name=%s priority=%s",
            db_train_task_id,
            task_name,
            create_task_request.priority,
        )
        self.task_repo.set_status(db_train_task_id, "QUEUED")
        self.task_repo.update_progress(db_train_task_id, 0, cfg.epochs, 0)
        self.worker.wake()
        return db_train_task_id

    def start_worker(self) -> None:
        self.worker.start()

    def stop_worker(self) -> None:
        self.worker.stop()

    def retry_training_task(self, train_task_id: int) -> None:
        db = SessionLocal()
        try:
            train_task = (
                db.query(TrainTaskModel)
                .filter(
                    TrainTaskModel.id == train_task_id,
                    TrainTaskModel.is_deleted == False,
                )
                .first()
            )
            if not train_task:
                raise ValueError("训练任务不存在")
            if train_task.status == "FINISHED":
                raise ValueError("已完成的训练任务不能重试")
            if train_task.status in ("QUEUED", "CLAIMED", "RUNNING", "RECOVERING"):
                raise ValueError("训练任务已经在等待或运行，不能重复入队")
            train_task.status = "QUEUED"
            train_task.queued_at = datetime.now(timezone.utc)
            train_task.worker_id = None
            train_task.heartbeat_at = None
            train_task.finished_at = None
            train_task.error_message = None
            db.commit()
            self.task_repo.set_status(train_task.id, "QUEUED")
            self.worker.wake()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def execute_claimed_task(self, train_task_id: int) -> None:
        db = SessionLocal()
        try:
            train_task = db.get(TrainTaskModel, train_task_id)
            if not train_task or train_task.is_deleted:
                raise ValueError("训练任务不存在")
            if train_task.status != "CLAIMED":
                raise ValueError(f"训练任务状态不可执行: {train_task.status}")
            if not train_task.task:
                raise ValueError("关联的标注任务不存在")
            cfg = YoloTrainConfig.model_validate(json.loads(train_task.config_json or "{}"))
            task_name = train_task.task.name
            stored_dataset_yaml_path = train_task.dataset_yaml_path
        finally:
            db.close()

        base_dir = TRAIN_DATA_DIR / task_name
        outputs_dir = base_dir / "outputs"
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "train.log"
        run_dir = outputs_dir / f"task_{train_task_id}"
        checkpoint_path = run_dir / "weights" / "last.pt"
        resume_checkpoint = checkpoint_path if checkpoint_path.is_file() else None

        dataset_result = None
        if resume_checkpoint and stored_dataset_yaml_path:
            yaml_path = Path(stored_dataset_yaml_path)
            if not yaml_path.is_file():
                raise RuntimeError(
                    "训练任务的数据集快照已经丢失，为避免使用不同数据恢复训练，已拒绝继续"
                )
        elif resume_checkpoint and (base_dir / "data.yaml").is_file():
            # 兼容创建于数据集快照功能之前的旧训练任务。
            yaml_path = base_dir / "data.yaml"
        else:
            dataset_result = self.yolo_dataset_builder.build(task_name, cfg.val_split)
            yaml_path = dataset_result.yaml_path

        db = SessionLocal()
        try:
            train_task = db.get(TrainTaskModel, train_task_id)
            train_task.log_path = str(log_path)
            train_task.output_path = str(run_dir)
            train_task.checkpoint_path = str(checkpoint_path)
            if dataset_result is not None:
                train_task.dataset_fingerprint = dataset_result.fingerprint
                train_task.dataset_yaml_path = str(dataset_result.yaml_path)
                train_task.dataset_manifest_path = str(
                    dataset_result.yaml_path.parent / "manifest.json"
                )
            if resume_checkpoint:
                train_task.status = "RECOVERING"
                train_task.resume_count = (train_task.resume_count or 0) + 1
                existing_metrics = (
                    db.query(TrainingMetricModel)
                    .filter(
                        TrainingMetricModel.train_task_id == train_task_id,
                        TrainingMetricModel.is_deleted == False,
                    )
                    .order_by(TrainingMetricModel.epoch)
                    .all()
                )
                self.task_repo.epoch_metrics[train_task_id] = [
                    to_stream_metric(metric.to_dict()) for metric in existing_metrics
                ]
            else:
                db.query(TrainingMetricModel).filter(
                    TrainingMetricModel.train_task_id == train_task_id
                ).delete(synchronize_session=False)
                train_task.current_epoch = 0
                train_task.progress = 0
            db.commit()
        finally:
            db.close()

        self._run_training(
            train_task_id,
            yaml_path.resolve(),
            outputs_dir.resolve(),
            cfg,
            log_path,
            resume_checkpoint,
        )

    def mark_worker_failure(self, train_task_id: int, error: str) -> None:
        self.task_repo.set_status(train_task_id, "ERROR")
        self.task_repo.set_error(train_task_id, error)
        self._update_db_status(train_task_id, "ERROR", error)
        self._broadcast_status(train_task_id, {"status": "ERROR", "error": error})

    def _broadcast_status(self, train_task_id: int, data: dict):
        import asyncio

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.task_repo.broadcast(train_task_id, data))
        except Exception as e:
            logger.warning(f"SSE 推送异常: {e}")
        finally:
            if loop is not None:
                loop.close()

    def _run_training(
        self,
        db_train_task_id: int,
        yaml_path: Path,
        outputs_dir: Path,
        cfg: YoloTrainConfig,
        log_path: Path,
        resume_checkpoint: Optional[Path] = None,
    ):
        """在唯一GPU Worker中执行训练或断点恢复。"""
        from ultralytics import YOLO

        self.task_repo.set_status(db_train_task_id, "RUNNING")
        self._update_db_status(db_train_task_id, "RUNNING")
        self._broadcast_status(
            db_train_task_id,
            {"status": "RUNNING", "resumed": resume_checkpoint is not None},
        )

        try:
            model_path = resume_checkpoint or self._resolve_model_path(cfg.model)
            logger.info(
                "加载模型: task_id=%s path=%s resumed=%s",
                db_train_task_id,
                model_path,
                resume_checkpoint is not None,
            )
            model = YOLO(str(model_path))
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            self.task_repo.set_status(db_train_task_id, "ERROR")
            self.task_repo.set_error(db_train_task_id, str(e))
            self._update_db_status(db_train_task_id, "ERROR", str(e))
            self._broadcast_status(db_train_task_id, {"status": "ERROR", "error": str(e)})
            return

        # Ultralytics 会在训练循环结束后对 best.pt 再做一次 final_eval，并再次触发
        # on_fit_epoch_end。用 on_train_epoch_start 配对，避免把最终验证误记成新一轮。
        epoch_guard = _TrainingEpochGuard()

        def _on_train_epoch_start(_trainer):
            epoch_guard.start()

        # 每轮回调
        def _on_fit_epoch_end(trainer):
            total_epochs = max(int(trainer.epochs), 1)
            epoch = epoch_guard.consume(trainer.epoch, total_epochs)
            if epoch is None:
                logger.info(
                    "忽略训练结束后的重复验证回调: task_id=%s raw_epoch=%s total=%s",
                    db_train_task_id,
                    getattr(trainer, "epoch", None),
                    getattr(trainer, "epochs", None),
                )
                return
            try:
                metrics = trainer.metrics
                metric_data = {"epoch": epoch, "total": total_epochs}

                if metrics:
                    metric_data["precision"] = metrics.get("metrics/precision(B)")
                    metric_data["recall"] = metrics.get("metrics/recall(B)")
                    metric_data["map50"] = metrics.get("metrics/mAP50(B)")
                    metric_data["map50_95"] = metrics.get("metrics/mAP50-95(B)")
                    metric_data["mask_precision"] = metrics.get("metrics/precision(M)")
                    metric_data["mask_recall"] = metrics.get("metrics/recall(M)")
                    metric_data["mask_map50"] = metrics.get("metrics/mAP50(M)")
                    metric_data["mask_map50_95"] = metrics.get("metrics/mAP50-95(M)")
                    metric_data["val_box_loss"] = metrics.get("val/box_loss")
                    metric_data["val_seg_loss"] = metrics.get("val/seg_loss")
                    metric_data["val_cls_loss"] = metrics.get("val/cls_loss")
                    metric_data["val_dfl_loss"] = metrics.get("val/dfl_loss")

                if getattr(trainer, "tloss", None) is not None:
                    try:
                        labeled_losses = trainer.label_loss_items(trainer.tloss)
                        metric_data["train_box_loss"] = labeled_losses.get("train/box_loss")
                        metric_data["train_seg_loss"] = labeled_losses.get("train/seg_loss")
                        metric_data["train_cls_loss"] = labeled_losses.get("train/cls_loss")
                        metric_data["train_dfl_loss"] = labeled_losses.get("train/dfl_loss")
                    except Exception as loss_error:
                        logger.warning("读取训练损失失败: %s", loss_error)

                metric_data["fitness"] = getattr(trainer, "fitness", None)
                validator_metrics = getattr(
                    getattr(trainer, "validator", None),
                    "metrics",
                    None,
                )
                if validator_metrics is not None and hasattr(validator_metrics, "summary"):
                    try:
                        metric_data["per_class_metrics"] = validator_metrics.summary(
                            normalize=True,
                            decimals=6,
                        )
                    except Exception as class_metric_error:
                        logger.warning("读取逐类别评估指标失败: %s", class_metric_error)

                if hasattr(trainer, "lr") and trainer.lr:
                    lr_val = trainer.lr
                    if isinstance(lr_val, dict):
                        metric_data["lr_pg0"] = float(lr_val.get("lr/pg0", 0))
                        metric_data["lr_pg1"] = float(lr_val.get("lr/pg1", 0))
                        metric_data["lr_pg2"] = float(lr_val.get("lr/pg2", 0))
                    else:
                        lrs = list(lr_val)
                        if len(lrs) >= 3:
                            metric_data["lr_pg0"] = float(lrs[0])
                            metric_data["lr_pg1"] = float(lrs[1])
                            metric_data["lr_pg2"] = float(lrs[2])

                metric_data = sanitize_json_value(metric_data)

                # 存到内存
                self.task_repo.add_epoch_metric(
                    db_train_task_id,
                    to_stream_metric(metric_data),
                )
                self.task_repo.update_progress(
                    db_train_task_id,
                    epoch,
                    total_epochs,
                    min(100, int(epoch / total_epochs * 100)),
                )

                # 写数据库
                self._save_metric_to_db(db_train_task_id, metric_data)

                self._broadcast_status(db_train_task_id, {
                    "status": "RUNNING",
                    "epoch": epoch,
                    "total_epochs": total_epochs,
                    "progress": min(100, int(epoch / total_epochs * 100)),
                    "metrics": self.task_repo.get_epoch_metrics(db_train_task_id),
                })

                logger.info(
                    f"Epoch {epoch}/{total_epochs} | "
                    f"mAP50-95={metric_data.get('map50_95', 'N/A')}"
                )
            except Exception as e:
                logger.error(f"回调异常: {e}")

        def _on_train_end(trainer):
            try:
                self.task_repo.set_status(db_train_task_id, "FINISHED")
                self._update_db_status(db_train_task_id, "FINISHED")

                # 标记最优轮次
                self._mark_best_metric(db_train_task_id)

                # 上传模型到 S3
                s3_model_url = self._upload_model_to_s3(db_train_task_id, outputs_dir)
                if s3_model_url:
                    self._update_db_output(db_train_task_id, s3_model_url)

                self._broadcast_status(db_train_task_id, {
                    "status": "FINISHED",
                    "s3_model_url": s3_model_url,
                    "metrics": self.task_repo.get_epoch_metrics(db_train_task_id),
                })

                self.task_repo.cleanup(db_train_task_id)
                logger.info(f"训练完成: task_id={db_train_task_id}")

                try:
                    from app.services.agent.auto_analysis_service import auto_analysis_service

                    auto_analysis_service.schedule(db_train_task_id)
                except Exception as analysis_error:
                    logger.exception(
                        "自动质量分析调度失败: task_id=%s error=%s",
                        db_train_task_id,
                        analysis_error,
                    )
            except Exception as e:
                logger.error(f"训练结束回调异常: {e}")

        model.add_callback("on_train_epoch_start", _on_train_epoch_start)
        model.add_callback("on_fit_epoch_end", _on_fit_epoch_end)
        model.add_callback("on_train_end", _on_train_end)

        try:
            run_project = str(outputs_dir)
            run_name = f"task_{db_train_task_id}"
            run_dir = Path(run_project) / run_name
            self.task_repo.tasks.setdefault(db_train_task_id, {})["run_dir"] = str(run_dir)
            self._update_db_output(db_train_task_id, str(run_dir))
            if resume_checkpoint:
                train_kwargs = {"resume": True}
            else:
                train_kwargs = cfg.to_train_kwargs(
                    data_path=str(yaml_path),
                    project=run_project,
                    name=run_name,
                    exist_ok=run_dir.exists(),
                    workers=settings.YOLO_WORKERS,
                    supported_args=self._get_supported_yolo_args(),
                )
            logger.info(f"YOLO 训练参数: {train_kwargs}")
            model.train(**train_kwargs)
        except Exception as e:
            logger.error(f"训练失败: {e}")
            self.task_repo.set_status(db_train_task_id, "ERROR")
            self.task_repo.set_error(db_train_task_id, str(e))
            self._update_db_status(db_train_task_id, "ERROR", str(e))
            self._broadcast_status(db_train_task_id, {"status": "ERROR", "error": str(e)})

    def _get_supported_yolo_args(self) -> Optional[set[str]]:
        """读取当前 Ultralytics 版本支持的配置项，避免版本差异参数导致训练失败。"""
        try:
            from ultralytics.cfg import DEFAULT_CFG_DICT

            return set(DEFAULT_CFG_DICT.keys()) | {
                "data",
                "project",
                "name",
                "exist_ok",
                "plots",
                "verbose",
                "workers",
            }
        except Exception as e:
            logger.warning(f"读取 Ultralytics 参数列表失败，将不做参数过滤: {e}")
            return None

    def _resolve_model_path(self, model_name: str) -> Path:
        """解析本地模型路径，避免 Ultralytics 在缺失模型时自动下载"""
        configured_path = Path(model_name)
        if configured_path.is_absolute():
            candidates = [configured_path]
        else:
            model_dir = (
                YOLO_MODEL_DIR
                if YOLO_MODEL_DIR.is_absolute()
                else Path.cwd() / YOLO_MODEL_DIR
            )
            candidates = [model_dir / configured_path]
            if configured_path.suffix == "":
                candidates.append(model_dir / f"{model_name}.pt")

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        candidate_text = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"本地模型文件不存在: {candidate_text}")

    # ------------------------ # 数据库操作
    def _update_db_status(self, train_task_id: int, status: str, error: Optional[str] = None):
        db = SessionLocal()
        try:
            task = db.query(TrainTaskModel).filter(TrainTaskModel.id == train_task_id).first()
            if task:
                task.status = status
                if error:
                    task.error_message = error
                if status == "RUNNING":
                    task.progress = 1
                    task.pid = os.getpid()
                    task.started_at = task.started_at or datetime.now(timezone.utc)
                    task.heartbeat_at = datetime.now(timezone.utc)
                if status in ("FINISHED", "ERROR"):
                    task.pid = None
                    task.worker_id = None
                    task.heartbeat_at = None
                    task.finished_at = datetime.now(timezone.utc)
                if status == "FINISHED":
                    task.progress = 100
                db.commit()
        finally:
            db.close()

    def _save_metric_to_db(self, train_task_id: int, metric_data: dict):
        metric_data = sanitize_json_value(metric_data)
        db = SessionLocal()
        try:
            record = (
                db.query(TrainingMetricModel)
                .filter(
                    TrainingMetricModel.train_task_id == train_task_id,
                    TrainingMetricModel.epoch == metric_data["epoch"],
                )
                .first()
            )
            if not record:
                record = TrainingMetricModel(
                    train_task_id=train_task_id,
                    epoch=metric_data["epoch"],
                )
                db.add(record)
            for field in (
                "train_box_loss",
                "train_seg_loss",
                "train_cls_loss",
                "train_dfl_loss",
                "val_box_loss",
                "val_seg_loss",
                "val_cls_loss",
                "val_dfl_loss",
                "precision",
                "recall",
                "map50",
                "map50_95",
                "mask_precision",
                "mask_recall",
                "mask_map50",
                "mask_map50_95",
                "fitness",
                "per_class_metrics",
                "lr_pg0",
                "lr_pg1",
                "lr_pg2",
            ):
                setattr(record, field, metric_data.get(field))
            record.is_deleted = False
            task = db.get(TrainTaskModel, train_task_id)
            if task:
                epoch = int(metric_data["epoch"])
                total = int(metric_data.get("total") or task.total_epochs or epoch)
                task.current_epoch = epoch
                task.total_epochs = total
                task.progress = min(99, int(epoch / max(total, 1) * 100))
                task.heartbeat_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

    def _mark_best_metric(self, train_task_id: int):
        """检测任务按Box mAP、分割任务按Mask mAP标记最优轮次。"""
        db = SessionLocal()
        try:
            train_task = db.get(TrainTaskModel, train_task_id)
            detection_type = str(
                getattr(getattr(train_task, "task", None), "detection_type", "") or ""
            ).lower()
            score_column = (
                TrainingMetricModel.mask_map50_95
                if detection_type in ("segment", "segmentation")
                else TrainingMetricModel.map50_95
            )
            metrics = (
                db.query(TrainingMetricModel)
                .filter(
                    TrainingMetricModel.train_task_id == train_task_id,
                    score_column.isnot(None),
                )
                .order_by(score_column.desc())
                .all()
            )
            if metrics:
                for metric in metrics:
                    metric.is_best = False
                metrics[0].is_best = True
                db.commit()
        finally:
            db.close()

    def _update_db_output(self, train_task_id: int, s3_url: str):
        db = SessionLocal()
        try:
            task = db.query(TrainTaskModel).filter(TrainTaskModel.id == train_task_id).first()
            if task:
                task.output_path = s3_url
                db.commit()
        finally:
            db.close()

    # ------------------------ # S3 上传
    def _upload_model_to_s3(self, train_task_id: int, outputs_dir: Path) -> Optional[str]:
        """将 best.pt 上传到 S3，返回 S3 key"""
        train_info = self.task_repo.tasks.get(train_task_id, {})
        run_dir = train_info.get("run_dir")
        if run_dir:
            best_pt = Path(run_dir) / "weights" / "best.pt"
        else:
            best_pt = outputs_dir / f"task_{train_task_id}" / "weights" / "best.pt"
        if not best_pt.exists():
            logger.warning(f"模型文件不存在: {best_pt}")
            return None

        try:
            model_filename = f"{uuid.uuid4().hex[:16]}.pt"
            s3_key = f"yolo_models/{model_filename}"
            s3.upload_file(str(best_pt), S3_BUCKET, s3_key)
            logger.info(f"模型已上传到 S3: {s3_key}")
            return s3_key
        except Exception as e:
            logger.error(f"S3 上传失败: {e}")
            return None
