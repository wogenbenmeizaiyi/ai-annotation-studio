import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.agent import AgentTrainingAnalysisModel
from app.models.train_task import TrainTaskModel
from app.schemas.train_agent import AgentModelResult
from app.services.agent.model_client import AgentModelClient
from app.services.agent.training_analyzer import TrainingAnalyzer
from app.services.agent.yolo_agent import _extract_json, load_skill

logger = logging.getLogger("agent.auto_analysis")


class AutoTrainingAnalysisService:
    def __init__(self):
        self.model = AgentModelClient()
        self.analyzer = TrainingAnalyzer()

    def schedule(self, train_task_id: int) -> bool:
        """为已完成训练创建唯一分析记录并启动后台分析。"""
        db = SessionLocal()
        try:
            task = db.get(TrainTaskModel, train_task_id)
            if not task or task.is_deleted or task.status != "FINISHED":
                logger.warning(
                    "auto_analysis_not_scheduled train_task_id=%s reason=task_not_finished",
                    train_task_id,
                )
                return False
            existing = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.train_task_id == train_task_id)
                .first()
            )
            if existing:
                logger.info(
                    "auto_analysis_already_exists train_task_id=%s status=%s",
                    train_task_id,
                    existing.status,
                )
                return False
            db.add(
                AgentTrainingAnalysisModel(
                    train_task_id=train_task_id,
                    status="PENDING",
                    model_name=settings.AGENT_MODEL,
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info("auto_analysis_race_skipped train_task_id=%s", train_task_id)
            return False
        finally:
            db.close()

        self._start_worker(train_task_id)
        return True

    def recover_unfinished(self) -> int:
        """服务重启时恢复已经登记但未完成的自动分析。"""
        db = SessionLocal()
        try:
            records = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.status.in_(("PENDING", "RUNNING")))
                .all()
            )
            train_task_ids = [record.train_task_id for record in records]
            for record in records:
                record.status = "PENDING"
                record.error_message = None
            db.commit()
        finally:
            db.close()

        for train_task_id in train_task_ids:
            self._start_worker(train_task_id)
        return len(train_task_ids)

    def get(self, train_task_id: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        should_regenerate = False
        try:
            record = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.train_task_id == train_task_id)
                .with_for_update()
                .first()
            )
            if (
                record
                and record.status in ("COMPLETED", "FAILED")
                and record.analyzer_version != self.analyzer.VERSION
            ):
                record.status = "PENDING"
                record.error_message = None
                record.model_result_json = None
                record.started_at = None
                record.completed_at = None
                db.commit()
                should_regenerate = True
            result = self._serialize(record) if record else None
        finally:
            db.close()
        if should_regenerate:
            logger.info(
                "auto_analysis_version_upgrade train_task_id=%s from_version=%s to_version=%s",
                train_task_id,
                result.get("analyzer_version") if result else None,
                self.analyzer.VERSION,
            )
            self._start_worker(train_task_id)
        return result

    def _start_worker(self, train_task_id: int) -> None:
        thread = threading.Thread(
            target=self._run,
            args=(train_task_id,),
            daemon=True,
            name=f"agent-analysis-{train_task_id}",
        )
        thread.start()
        logger.info("auto_analysis_scheduled train_task_id=%s", train_task_id)

    def _run(self, train_task_id: int) -> None:
        self._mark_running(train_task_id)
        try:
            analysis = self.analyzer.analyze(train_task_id)
            self._save_deterministic_analysis(train_task_id, analysis)
            result = self._generate_summary(analysis)
            self._mark_completed(train_task_id, analysis, result)
            logger.info("auto_analysis_completed train_task_id=%s", train_task_id)
        except Exception as exc:
            self._mark_failed(train_task_id, str(exc))
            logger.exception(
                "auto_analysis_failed train_task_id=%s error_type=%s",
                train_task_id,
                type(exc).__name__,
            )

    def _generate_summary(self, analysis: Dict[str, Any]) -> AgentModelResult:
        if analysis.get("summary", {}).get("metric_count", 0) == 0:
            return AgentModelResult(
                reply="训练已经结束，但没有采集到可用于模型质量分析的轮次指标。",
                warnings=["没有训练指标，无法评价模型质量"],
            )
        system_prompt = (
            f"{load_skill()}\n\n"
            "你正在执行训练完成后的自动质量分析。只返回一个JSON对象，字段固定为"
            "reply、config_patch、changes、questions、warnings、ready_to_apply。"
            "config_patch必须为空，ready_to_apply必须为false。reply必须是一份可直接展示的完整Markdown报告，"
            "依次包含：执行结论、核心指标、收敛与过拟合、逐类别表现、问题根因、优化方案、"
            "下一轮实验目标和验收标准。存在comparison_to_parent时必须评价本轮调整是否优于上一轮。"
            "必须引用确定性分析中的具体数值。"
            "优化方案必须区分数据整改、训练参数和推理阈值；不得把推理阈值写成训练参数。"
            "若模型效果较差，必须给出按优先级排列的可操作方案；若证据不足必须明确说明。"
        )
        payload = {
            "mode": "automatic_final_analysis",
            "deterministic_analysis": analysis,
        }
        raw = asyncio.run(
            self.model.complete(
                system_prompt,
                [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            )
        )
        try:
            result = AgentModelResult.model_validate(_extract_json(raw))
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"自动分析模型返回校验失败: {exc}") from exc
        if result.config_patch or result.ready_to_apply:
            raise RuntimeError("自动质量分析不得返回可应用的训练参数草案")
        return result

    @staticmethod
    def _save_deterministic_analysis(
        train_task_id: int,
        analysis: Dict[str, Any],
    ) -> None:
        db = SessionLocal()
        try:
            record = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.train_task_id == train_task_id)
                .first()
            )
            if not record:
                raise RuntimeError("自动分析记录不存在")
            record.analyzer_version = str(analysis.get("analyzer_version", ""))
            record.analysis_json = json.dumps(analysis, ensure_ascii=False)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _mark_running(train_task_id: int) -> None:
        db = SessionLocal()
        try:
            record = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.train_task_id == train_task_id)
                .first()
            )
            if not record:
                raise RuntimeError("自动分析记录不存在")
            record.status = "RUNNING"
            record.started_at = datetime.now(timezone.utc)
            record.error_message = None
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _mark_completed(
        train_task_id: int,
        analysis: Dict[str, Any],
        result: AgentModelResult,
    ) -> None:
        db = SessionLocal()
        try:
            record = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.train_task_id == train_task_id)
                .first()
            )
            if not record:
                raise RuntimeError("自动分析记录不存在")
            record.status = "COMPLETED"
            record.analyzer_version = str(analysis.get("analyzer_version", ""))
            record.analysis_json = json.dumps(analysis, ensure_ascii=False)
            record.model_result_json = result.model_dump_json()
            record.completed_at = datetime.now(timezone.utc)
            record.error_message = None
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _mark_failed(train_task_id: int, error: str) -> None:
        db = SessionLocal()
        try:
            record = (
                db.query(AgentTrainingAnalysisModel)
                .filter(AgentTrainingAnalysisModel.train_task_id == train_task_id)
                .first()
            )
            if record:
                record.status = "FAILED"
                record.error_message = error[:2000]
                record.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    @staticmethod
    def _serialize(record: AgentTrainingAnalysisModel) -> Dict[str, Any]:
        return {
            "id": record.id,
            "train_task_id": record.train_task_id,
            "status": record.status,
            "analyzer_version": record.analyzer_version,
            "model_name": record.model_name,
            "analysis": json.loads(record.analysis_json) if record.analysis_json else None,
            "model_result": (
                json.loads(record.model_result_json) if record.model_result_json else None
            ),
            "error_message": record.error_message,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }


auto_analysis_service = AutoTrainingAnalysisService()
