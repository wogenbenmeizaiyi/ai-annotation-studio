import logging
import os
import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import or_, text

from app.core.config import settings
from app.db.database import SessionLocal, engine
from app.models.train_task import TrainTaskModel

if TYPE_CHECKING:
    from app.services.YOLO.train_task_service import TrainTaskService

logger = logging.getLogger(__name__)


class PostgresTrainingWorker:
    """使用PostgreSQL作为持久队列，并通过advisory lock选举唯一GPU Worker。"""

    ADVISORY_LOCK_ID = 0x594F4C4F
    CLAIM_LOCK_ID = ADVISORY_LOCK_ID + 1
    ACTIVE_STATUSES = ("CLAIMED", "RUNNING", "RECOVERING")

    def __init__(self, service: "TrainTaskService"):
        self.service = service
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="postgres-gpu-worker",
        )
        self._thread.start()
        logger.info("训练队列Worker已启动: worker_id=%s", self.worker_id)

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._thread and self._thread.is_alive():
            self._release_owned_tasks()
        logger.info("训练队列Worker已收到停止信号: worker_id=%s", self.worker_id)

    def wake(self) -> None:
        self._wake_event.set()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                    acquired = bool(
                        connection.execute(
                            text("SELECT pg_try_advisory_lock(:lock_id)"),
                            {"lock_id": self.ADVISORY_LOCK_ID},
                        ).scalar()
                    )
                    if not acquired:
                        self._wait()
                        continue
                    logger.info("已取得单GPU Worker锁: worker_id=%s", self.worker_id)
                    try:
                        self._run_as_leader()
                    finally:
                        connection.execute(
                            text("SELECT pg_advisory_unlock(:lock_id)"),
                            {"lock_id": self.ADVISORY_LOCK_ID},
                        )
            except Exception:
                logger.exception("训练队列Worker循环异常: worker_id=%s", self.worker_id)
                self._wait()

    def _run_as_leader(self) -> None:
        while not self._stop_event.is_set():
            self._requeue_stale_tasks()
            train_task_id = self._claim_next_task()
            if train_task_id is None:
                self._wait()
                continue
            self._execute(train_task_id)

    def _wait(self) -> None:
        self._wake_event.wait(settings.TRAIN_QUEUE_POLL_SECONDS)
        self._wake_event.clear()

    def _requeue_stale_tasks(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.TRAIN_WORKER_STALE_SECONDS
        )
        db = SessionLocal()
        try:
            stale_tasks = (
                db.query(TrainTaskModel)
                .filter(
                    TrainTaskModel.is_deleted == False,
                    TrainTaskModel.status.in_(self.ACTIVE_STATUSES),
                    or_(
                        TrainTaskModel.heartbeat_at.is_(None),
                        TrainTaskModel.heartbeat_at < cutoff,
                    ),
                )
                .with_for_update(skip_locked=True)
                .all()
            )
            now = datetime.now(timezone.utc)
            for task in stale_tasks:
                logger.warning(
                    "检测到失联训练任务，重新入队: task_id=%s previous_worker=%s",
                    task.id,
                    task.worker_id,
                )
                task.status = "QUEUED"
                task.worker_id = None
                task.heartbeat_at = None
                task.queued_at = now
                task.error_message = None
            db.commit()
        finally:
            db.close()

    def _claim_next_task(self) -> Optional[int]:
        db = SessionLocal()
        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": self.CLAIM_LOCK_ID},
                )
            active_task = (
                db.query(TrainTaskModel.id)
                .filter(
                    TrainTaskModel.is_deleted == False,
                    TrainTaskModel.status.in_(self.ACTIVE_STATUSES),
                )
                .first()
            )
            if active_task:
                return None

            task = (
                db.query(TrainTaskModel)
                .filter(
                    TrainTaskModel.is_deleted == False,
                    TrainTaskModel.status == "QUEUED",
                )
                .order_by(
                    TrainTaskModel.priority.desc(),
                    TrainTaskModel.queued_at.asc(),
                    TrainTaskModel.id.asc(),
                )
                .with_for_update(skip_locked=True)
                .first()
            )
            if not task:
                return None
            now = datetime.now(timezone.utc)
            task.status = "CLAIMED"
            task.worker_id = self.worker_id
            task.heartbeat_at = now
            task.attempt_count = (task.attempt_count or 0) + 1
            db.commit()
            logger.info(
                "训练任务出队: task_id=%s worker_id=%s attempt=%s",
                task.id,
                self.worker_id,
                task.attempt_count,
            )
            return task.id
        finally:
            db.close()

    def _execute(self, train_task_id: int) -> None:
        heartbeat_stop = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(train_task_id, heartbeat_stop),
            daemon=True,
            name=f"train-heartbeat-{train_task_id}",
        )
        heartbeat_thread.start()
        try:
            self.service.execute_claimed_task(train_task_id)
        except Exception as exc:
            logger.exception("训练Worker执行失败: task_id=%s", train_task_id)
            self.service.mark_worker_failure(train_task_id, str(exc))
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=2)

    def _heartbeat_loop(self, train_task_id: int, stop_event: threading.Event) -> None:
        while not stop_event.wait(settings.TRAIN_WORKER_HEARTBEAT_SECONDS):
            db = SessionLocal()
            try:
                updated = (
                    db.query(TrainTaskModel)
                    .filter(
                        TrainTaskModel.id == train_task_id,
                        TrainTaskModel.worker_id == self.worker_id,
                        TrainTaskModel.status.in_(self.ACTIVE_STATUSES),
                    )
                    .update({TrainTaskModel.heartbeat_at: datetime.now(timezone.utc)})
                )
                db.commit()
                if not updated:
                    return
            except Exception:
                db.rollback()
                logger.exception("训练Worker心跳更新失败: task_id=%s", train_task_id)
            finally:
                db.close()

    def _release_owned_tasks(self) -> None:
        db = SessionLocal()
        try:
            tasks = (
                db.query(TrainTaskModel)
                .filter(
                    TrainTaskModel.worker_id == self.worker_id,
                    TrainTaskModel.status.in_(self.ACTIVE_STATUSES),
                )
                .with_for_update(skip_locked=True)
                .all()
            )
            now = datetime.now(timezone.utc)
            for task in tasks:
                task.status = "QUEUED"
                task.queued_at = now
                task.worker_id = None
                task.heartbeat_at = None
            db.commit()
            if tasks:
                logger.warning(
                    "服务停止时训练任务已重新入队: task_ids=%s",
                    [task.id for task in tasks],
                )
        finally:
            db.close()
