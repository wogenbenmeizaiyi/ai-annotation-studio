from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.train_task import TrainTaskModel
from app.models.training_metric import TrainingMetricModel


def _slope(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2
    y_mean = sum(values) / len(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    if denominator == 0:
        return 0.0
    return sum(
        (index - x_mean) * (value - y_mean) for index, value in enumerate(values)
    ) / denominator


def _numbers(metrics: List[TrainingMetricModel], field: str) -> List[float]:
    return [
        float(value)
        for metric in metrics
        if (value := getattr(metric, field, None)) is not None
    ]


def _number(metric: TrainingMetricModel, field: str) -> Optional[float]:
    value = getattr(metric, field, None)
    return float(value) if value is not None else None


class TrainingAnalyzer:
    VERSION = "3.0"

    def analyze(self, train_task_id: int) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TrainTaskModel)
                .filter(TrainTaskModel.id == train_task_id, TrainTaskModel.is_deleted == False)
                .first()
            )
            if not task:
                raise ValueError("训练任务不存在")
            metrics = (
                db.query(TrainingMetricModel)
                .filter(
                    TrainingMetricModel.train_task_id == train_task_id,
                    TrainingMetricModel.is_deleted == False,
                )
                .order_by(TrainingMetricModel.epoch)
                .all()
            )
            parent_metrics: List[TrainingMetricModel] = []
            parent_train_task_id = getattr(task, "parent_train_task_id", None)
            if parent_train_task_id is not None:
                parent_metrics = (
                    db.query(TrainingMetricModel)
                    .filter(
                        TrainingMetricModel.train_task_id == parent_train_task_id,
                        TrainingMetricModel.is_deleted == False,
                    )
                    .order_by(TrainingMetricModel.epoch)
                    .all()
                )
            return self._build(task, metrics, parent_metrics)
        finally:
            db.close()

    def _build(
        self,
        task: TrainTaskModel,
        metrics: List[TrainingMetricModel],
        parent_metrics: Optional[List[TrainingMetricModel]] = None,
    ) -> Dict[str, Any]:
        if not metrics:
            return {
                "analyzer_version": self.VERSION,
                "task_id": task.id,
                "status": task.status,
                "stage": (
                    "in_progress"
                    if task.status in ("QUEUED", "CLAIMED", "RECOVERING", "RUNNING")
                    else "no_metrics"
                ),
                "summary": {"metric_count": 0},
                "signals": {},
                "evidence": ["当前没有可用于分析的轮次指标"],
                "recommendations": [],
                "limitations": ["至少产生一个训练轮次后才能分析模型质量"],
            }

        detection_type = str(
            getattr(getattr(task, "task", None), "detection_type", "detection")
            or "detection"
        ).lower()
        is_segmentation = detection_type in ("segment", "segmentation")
        primary_map_field = "mask_map50_95" if is_segmentation else "map50_95"
        primary_map50_field = "mask_map50" if is_segmentation else "map50"
        primary_metric_name = "Mask mAP50-95" if is_segmentation else "Box mAP50-95"

        map_values = [
            (metric, getattr(metric, primary_map_field, None))
            for metric in metrics
            if getattr(metric, primary_map_field, None) is not None
        ]
        best_metric: Optional[TrainingMetricModel] = None
        if map_values:
            best_metric = max(map_values, key=lambda item: item[1])[0]
        final = metrics[-1]
        tail = metrics[-min(10, len(metrics)):]

        map_tail = _numbers(tail, primary_map_field)
        train_loss_tail = [
            sum(values)
            for metric in tail
            if (values := [
                float(value)
                for value in (
                    getattr(metric, "train_box_loss", None),
                    getattr(metric, "train_seg_loss", None),
                    getattr(metric, "train_cls_loss", None),
                    getattr(metric, "train_dfl_loss", None),
                )
                if value is not None
            ])
        ]
        val_loss_tail = [
            sum(values)
            for metric in tail
            if (values := [
                float(value)
                for value in (
                    getattr(metric, "val_box_loss", None),
                    getattr(metric, "val_seg_loss", None),
                    getattr(metric, "val_cls_loss", None),
                    getattr(metric, "val_dfl_loss", None),
                )
                if value is not None
            ])
        ]

        map_slope = _slope(map_tail)
        train_loss_slope = _slope(train_loss_tail)
        val_loss_slope = _slope(val_loss_tail)
        best_map = (
            float(getattr(best_metric, primary_map_field))
            if best_metric and getattr(best_metric, primary_map_field, None) is not None
            else None
        )
        final_map = _number(final, primary_map_field)
        decline_ratio = (
            (best_map - final_map) / best_map
            if best_map and final_map is not None and best_map > 0
            else 0.0
        )
        possible_overfitting = (
            len(tail) >= 5
            and train_loss_slope < 0
            and val_loss_slope > 0
            and decline_ratio >= 0.03
        )
        converged = len(map_tail) >= 5 and abs(map_slope) < 0.001
        still_improving = len(map_tail) >= 5 and map_slope >= 0.002

        precision_field = "mask_precision" if is_segmentation else "precision"
        recall_field = "mask_recall" if is_segmentation else "recall"
        precision = _number(final, precision_field)
        recall = _number(final, recall_field)
        imbalance = None
        if precision is not None and recall is not None and abs(precision - recall) >= 0.1:
            imbalance = "recall_low" if precision > recall else "precision_low"

        evidence = []
        if best_metric and best_map is not None:
            evidence.append(
                f"{primary_metric_name}在第{best_metric.epoch}轮达到最佳值{best_map:.4f}"
            )
        if final_map is not None:
            evidence.append(f"最终第{final.epoch}轮{primary_metric_name}为{final_map:.4f}")
        if possible_overfitting:
            evidence.append("最近轮次训练损失下降、验证损失上升，并且最终mAP低于峰值")
        if still_improving:
            evidence.append(f"最近轮次{primary_metric_name}仍保持上升趋势")
        if imbalance == "recall_low":
            evidence.append("最终precision明显高于recall，模型可能存在较多漏检")
        elif imbalance == "precision_low":
            evidence.append("最终recall明显高于precision，模型可能存在较多误检")

        recommendations = []
        if possible_overfitting and best_metric:
            recommendations.extend([
                {
                    "field": "epochs",
                    "suggested": max(best_metric.epoch + 10, 20),
                    "reason": "最佳指标较早出现，后续发生回落",
                },
                {"field": "patience", "suggested": 20, "reason": "缩短长期无提升时的等待"},
            ])
        elif still_improving:
            recommendations.append(
                {
                    "field": "epochs",
                    "suggested": "适当增加",
                    "reason": "训练结束时指标仍在改善",
                }
            )

        per_class_metrics = getattr(final, "per_class_metrics", None)
        limitations = []
        if not per_class_metrics:
            limitations.append("当前没有逐类别指标，无法定位具体类别的效果")
        if is_segmentation and _number(final, "mask_map50_95") is None:
            limitations.append("分割训练没有采集到Mask指标，请确认使用的是-seg分割模型")

        comparison_to_parent = None
        parent_train_task_id = getattr(task, "parent_train_task_id", None)
        if parent_train_task_id is not None and parent_metrics:
            parent_final = parent_metrics[-1]
            parent_final_map = _number(parent_final, primary_map_field)
            parent_precision = _number(parent_final, precision_field)
            parent_recall = _number(parent_final, recall_field)
            primary_metric_delta = (
                final_map - parent_final_map
                if final_map is not None and parent_final_map is not None
                else None
            )
            comparison_to_parent = {
                "parent_train_task_id": parent_train_task_id,
                "parent_final_map50_95": parent_final_map,
                "primary_metric_delta": primary_metric_delta,
                "precision_delta": (
                    precision - parent_precision
                    if precision is not None and parent_precision is not None
                    else None
                ),
                "recall_delta": (
                    recall - parent_recall
                    if recall is not None and parent_recall is not None
                    else None
                ),
                "improved": (
                    primary_metric_delta > 0.001
                    if primary_metric_delta is not None
                    else None
                ),
            }
            if primary_metric_delta is not None:
                direction = "提升" if primary_metric_delta > 0 else "下降"
                evidence.append(
                    f"相较来源训练任务#{parent_train_task_id}，"
                    f"{primary_metric_name}{direction}{abs(primary_metric_delta):.4f}"
                )
        elif parent_train_task_id is not None:
            limitations.append("来源训练任务没有可用于对比的轮次指标")

        return {
            "analyzer_version": self.VERSION,
            "task_id": task.id,
            "task_type": "segmentation" if is_segmentation else "detection",
            "primary_metric": primary_metric_name,
            "status": task.status,
            "stage": "final" if task.status == "FINISHED" else "in_progress",
            "summary": {
                "metric_count": len(metrics),
                "best_epoch": best_metric.epoch if best_metric else None,
                "best_map50_95": best_map,
                "final_map50_95": final_map,
                "final_map50": _number(final, primary_map50_field),
                "final_precision": precision,
                "final_recall": recall,
                "peak_decline_ratio": round(decline_ratio, 6),
                "final_box_precision": _number(final, "precision"),
                "final_box_recall": _number(final, "recall"),
                "final_box_map50": _number(final, "map50"),
                "final_box_map50_95": _number(final, "map50_95"),
                "final_mask_precision": _number(final, "mask_precision"),
                "final_mask_recall": _number(final, "mask_recall"),
                "final_mask_map50": _number(final, "mask_map50"),
                "final_mask_map50_95": _number(final, "mask_map50_95"),
                "final_fitness": _number(final, "fitness"),
            },
            "signals": {
                "converged": converged,
                "still_improving": still_improving,
                "possible_overfitting": possible_overfitting,
                "precision_recall_imbalance": imbalance,
                "recent_map_slope": round(map_slope, 8),
                "recent_train_loss_slope": round(train_loss_slope, 8),
                "recent_val_loss_slope": round(val_loss_slope, 8),
            },
            "evidence": evidence,
            "recommendations": recommendations,
            "comparison_to_parent": comparison_to_parent,
            "per_class_metrics": per_class_metrics,
            "limitations": limitations,
        }
