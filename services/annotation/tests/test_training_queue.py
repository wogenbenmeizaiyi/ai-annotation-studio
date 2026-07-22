import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.image import ImageModel
from app.models.task import CategoryModel, TaskModel
from app.models.train_task import TrainTaskModel
from app.models.training_metric import TrainingMetricModel
from app.services.YOLO.training_worker import PostgresTrainingWorker


class TrainingQueueTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        TaskModel.__table__.create(self.engine)
        TrainTaskModel.__table__.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        db = self.session_factory()
        try:
            task = TaskModel(name="queue-test", detection_type="detection")
            db.add(task)
            db.flush()
            now = datetime.now(timezone.utc)
            db.add_all(
                [
                    TrainTaskModel(
                        task_id=task.id,
                        status="QUEUED",
                        priority=0,
                        queued_at=now - timedelta(minutes=2),
                    ),
                    TrainTaskModel(
                        task_id=task.id,
                        status="QUEUED",
                        priority=10,
                        queued_at=now - timedelta(minutes=1),
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

    def tearDown(self):
        self.engine.dispose()

    def test_claims_one_task_and_respects_priority(self):
        worker = PostgresTrainingWorker(SimpleNamespace())
        with patch(
            "app.services.YOLO.training_worker.SessionLocal",
            self.session_factory,
        ):
            claimed_id = worker._claim_next_task()
            second_claim = worker._claim_next_task()

        db = self.session_factory()
        try:
            claimed = db.get(TrainTaskModel, claimed_id)
            self.assertEqual(claimed.priority, 10)
            self.assertEqual(claimed.status, "CLAIMED")
            self.assertEqual(claimed.attempt_count, 1)
            self.assertIsNone(second_claim)
        finally:
            db.close()

    def test_requeues_task_with_expired_heartbeat(self):
        db = self.session_factory()
        try:
            task = db.query(TrainTaskModel).order_by(TrainTaskModel.id).first()
            task.status = "RUNNING"
            task.worker_id = "dead-worker"
            task.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
            db.commit()
            task_id = task.id
        finally:
            db.close()

    def test_shutdown_requeues_owned_running_task(self):
        worker = PostgresTrainingWorker(SimpleNamespace())
        db = self.session_factory()
        try:
            task = db.query(TrainTaskModel).order_by(TrainTaskModel.id).first()
            task.status = "RUNNING"
            task.worker_id = worker.worker_id
            task.heartbeat_at = datetime.now(timezone.utc)
            db.commit()
            task_id = task.id
        finally:
            db.close()

        with patch(
            "app.services.YOLO.training_worker.SessionLocal",
            self.session_factory,
        ):
            worker._release_owned_tasks()

        db = self.session_factory()
        try:
            recovered = db.get(TrainTaskModel, task_id)
            self.assertEqual(recovered.status, "QUEUED")
            self.assertIsNone(recovered.worker_id)
        finally:
            db.close()

        worker = PostgresTrainingWorker(SimpleNamespace())
        with patch(
            "app.services.YOLO.training_worker.SessionLocal",
            self.session_factory,
        ):
            worker._requeue_stale_tasks()

        db = self.session_factory()
        try:
            recovered = db.get(TrainTaskModel, task_id)
            self.assertEqual(recovered.status, "QUEUED")
            self.assertIsNone(recovered.worker_id)
            self.assertIsNone(recovered.heartbeat_at)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
