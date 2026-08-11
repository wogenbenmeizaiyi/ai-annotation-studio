import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.agent import AgentConfigProposalModel
from app.models.task import CategoryModel, TaskModel
from app.schemas.train_task import CreateTaskRequest, YoloTrainConfig
from app.services.YOLO.train_task_service import TrainTaskService
from app.services.agent.config_policy import canonical_config, validate_training_config

logger = logging.getLogger("agent.proposal")


class ProposalService:
    def __init__(self, train_task_service: TrainTaskService):
        self.train_task_service = train_task_service

    def confirm(self, proposal_id: str, expected_config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("proposal_confirmation_started proposal_id=%s", proposal_id)
        db: Session = SessionLocal()
        try:
            proposal = (
                db.query(AgentConfigProposalModel)
                .filter(AgentConfigProposalModel.id == proposal_id)
                .with_for_update()
                .first()
            )
            if not proposal:
                raise ValueError("训练参数草案不存在")
            if proposal.status not in ("DRAFT", "CONFIRMED"):
                raise ValueError("训练参数草案已经失效或用于启动训练")
            category_count = (
                db.query(CategoryModel.id)
                .filter(CategoryModel.task_id == proposal.task_id)
                .count()
            )
            config, _ = validate_training_config(
                expected_config,
                list(range(category_count)),
            )
            serialized = canonical_config(config)
            config_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            if not secrets.compare_digest(config_hash, proposal.config_hash):
                raise ValueError("页面参数已发生变化，请重新生成或应用训练草案")

            raw_token = secrets.token_urlsafe(48)
            proposal.confirmation_token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            proposal.confirmation_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            proposal.confirmed_at = datetime.now(timezone.utc)
            proposal.confirmation_used = False
            proposal.status = "CONFIRMED"
            db.commit()
            logger.info(
                "proposal_confirmed proposal_id=%s task_id=%s expires_in_seconds=300",
                proposal.id,
                proposal.task_id,
            )
            return {
                "proposal_id": proposal.id,
                "confirmation_token": raw_token,
                "expires_in": 300,
                "status": proposal.status,
            }
        finally:
            db.close()

    def start(self, proposal_id: str, confirmation_token: str) -> Dict[str, Any]:
        logger.info("proposal_start_requested proposal_id=%s", proposal_id)
        db: Session = SessionLocal()
        proposal = None
        task_name = None
        config = None
        source_train_task_id = None
        try:
            proposal = (
                db.query(AgentConfigProposalModel)
                .filter(AgentConfigProposalModel.id == proposal_id)
                .with_for_update()
                .first()
            )
            if not proposal:
                raise ValueError("训练参数草案不存在")
            if proposal.status != "CONFIRMED" or proposal.confirmation_used:
                raise ValueError("训练参数草案尚未确认或确认已经使用")
            if (
                not proposal.confirmation_expires_at
                or proposal.confirmation_expires_at <= datetime.now(timezone.utc)
            ):
                raise ValueError("训练确认已经过期，请重新确认")
            actual_hash = hashlib.sha256(confirmation_token.encode("utf-8")).hexdigest()
            if not proposal.confirmation_token_hash or not secrets.compare_digest(
                actual_hash,
                proposal.confirmation_token_hash,
            ):
                raise ValueError("训练确认令牌无效")

            task = db.get(TaskModel, proposal.task_id)
            if not task or task.is_deleted:
                raise ValueError("关联的标注任务不存在")
            task_name = task.name
            source_train_task_id = proposal.source_train_task_id
            config = YoloTrainConfig.model_validate(json.loads(proposal.config_json))
            if (
                hashlib.sha256(canonical_config(config).encode("utf-8")).hexdigest()
                != proposal.config_hash
            ):
                raise ValueError("训练草案配置完整性校验失败")

            proposal.confirmation_used = True
            proposal.status = "STARTING"
            db.commit()
            logger.info(
                "proposal_start_authorized proposal_id=%s task_id=%s",
                proposal_id,
                proposal.task_id,
            )
        finally:
            db.close()

        try:
            train_task_id = self.train_task_service.start_training(
                CreateTaskRequest(task_name=task_name, config=config),
                parent_train_task_id=source_train_task_id,
            )
        except Exception as exc:
            self._mark_failed(proposal_id, str(exc))
            logger.exception(
                "proposal_start_failed proposal_id=%s error_type=%s",
                proposal_id,
                type(exc).__name__,
            )
            raise

        db = SessionLocal()
        try:
            proposal = db.get(AgentConfigProposalModel, proposal_id)
            proposal.status = "QUEUED"
            proposal.train_task_id = train_task_id
            db.commit()
            logger.info(
                "proposal_queued proposal_id=%s train_task_id=%s",
                proposal_id,
                train_task_id,
            )
            return {
                "proposal_id": proposal_id,
                "train_task_id": train_task_id,
                "status": "QUEUED",
            }
        finally:
            db.close()

    @staticmethod
    def _mark_failed(proposal_id: str, error: str) -> None:
        db: Session = SessionLocal()
        try:
            proposal = db.get(AgentConfigProposalModel, proposal_id)
            if proposal:
                proposal.status = "FAILED"
                proposal.error_message = error[:2000]
                db.commit()
        finally:
            db.close()
