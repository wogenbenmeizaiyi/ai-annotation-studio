import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.schemas.train_task import YoloTrainConfig
from app.services.YOLO.train_task_service import _TrainingEpochGuard
from app.services.YOLO.yolo_dataset_builder import (
    DatasetImageRecord,
    YoloDatasetBuilder,
    _dataset_fingerprint,
    _split_records,
)
from app.services.agent.config_policy import validate_training_config
from app.services.agent.auto_analysis_service import AutoTrainingAnalysisService
from app.services.agent.training_analyzer import TrainingAnalyzer


class ConfigPolicyTests(unittest.TestCase):
    @patch("app.services.agent.config_policy.available_models", return_value=["yolo26n.pt"])
    def test_accepts_valid_config_and_auto_batch(self, _):
        config, warnings = validate_training_config(
            {
                "model": "yolo26n.pt",
                "epochs": 100,
                "patience": 30,
                "batch": -1,
                "imgsz": 640,
                "classes": [0, 1],
                "val_split": 0.2,
            },
            [0, 1],
        )
        self.assertEqual(config.batch, -1)
        self.assertEqual(warnings, [])

    def test_training_kwargs_always_save_checkpoint(self):
        kwargs = YoloTrainConfig().to_train_kwargs(
            data_path="data.yaml",
            project="outputs",
            name="task_1",
            exist_ok=False,
            workers=1,
            supported_args=None,
        )
        self.assertTrue(kwargs["save"])

    def test_final_validation_callback_is_not_counted_as_extra_epoch(self):
        guard = _TrainingEpochGuard()
        guard.start()
        self.assertEqual(guard.consume(raw_epoch=99, total_epochs=100), 100)
        self.assertIsNone(guard.consume(raw_epoch=100, total_epochs=100))

        guard.start()
        self.assertEqual(guard.consume(raw_epoch=150, total_epochs=150), 150)

    @patch("app.services.agent.config_policy.available_models", return_value=["yolo26n.pt"])
    def test_rejects_unlisted_model_and_invalid_cross_field_values(self, _):
        with self.assertRaisesRegex(ValueError, "model必须来自服务端模型白名单"):
            validate_training_config(
                {
                    "model": "other.pt",
                    "epochs": 10,
                    "patience": 20,
                    "close_mosaic": 30,
                },
                [0],
            )


class DatasetSnapshotTests(unittest.TestCase):
    @staticmethod
    def _records():
        return [
            DatasetImageRecord(
                image_id=index,
                file_name=f"image-{index}.jpg",
                s3_key=f"task/image-{index}.jpg",
                width=640,
                height=480,
                yolo_lines=(f"0 0.5 0.5 0.{index} 0.{index}",),
            )
            for index in range(1, 11)
        ]

    def test_same_dataset_and_ratio_have_identical_split(self):
        records = self._records()
        first = _split_records(records, task_id=7, val_split=0.2)
        second = _split_records(list(reversed(records)), task_id=7, val_split=0.2)

        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 8)
        self.assertEqual(len(first[1]), 2)
        self.assertTrue(first[0].isdisjoint(first[1]))

    def test_fingerprint_is_order_independent_and_tracks_data_changes(self):
        records = self._records()
        categories = [{"id": 1, "yolo_id": 0, "name": "defect"}]
        first = _dataset_fingerprint(7, 0.2, categories, records)
        reordered = _dataset_fingerprint(7, 0.2, categories, list(reversed(records)))
        changed_ratio = _dataset_fingerprint(7, 0.25, categories, records)
        changed_records = list(records)
        changed_records[0] = DatasetImageRecord(
            **{
                **changed_records[0].__dict__,
                "yolo_lines": ("0 0.4 0.4 0.2 0.2",),
            }
        )
        changed_label = _dataset_fingerprint(7, 0.2, categories, changed_records)

        self.assertEqual(first, reordered)
        self.assertNotEqual(first, changed_ratio)
        self.assertNotEqual(first, changed_label)

    @patch("app.services.YOLO.yolo_dataset_builder.s3")
    def test_snapshot_is_reused_only_when_all_files_exist(self, s3_mock):
        records = self._records()[:4]
        train_ids, val_ids = _split_records(records, task_id=7, val_split=0.25)
        fingerprint = "a" * 64
        categories = [{"id": 1, "yolo_id": 0, "name": "defect"}]
        s3_mock.get_object.side_effect = lambda **_: {"Body": BytesIO(b"image")}

        with TemporaryDirectory() as directory:
            root = Path(directory)
            temporary_snapshot = root / "temporary"
            published_snapshot = root / fingerprint
            YoloDatasetBuilder._write_snapshot(
                temporary_snapshot,
                published_snapshot,
                task_id=7,
                val_split=0.25,
                fingerprint=fingerprint,
                records=records,
                train_ids=train_ids,
                val_ids=val_ids,
                categories=categories,
            )
            temporary_snapshot.replace(published_snapshot)

            manifest = YoloDatasetBuilder._read_complete_manifest(
                published_snapshot / "manifest.json",
                published_snapshot / "data.yaml",
                fingerprint,
            )
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest["train_count"], 3)
            self.assertEqual(manifest["val_count"], 1)
            self.assertIn(
                str(published_snapshot.resolve()),
                (published_snapshot / "data.yaml").read_text(encoding="utf-8"),
            )

            first_train = manifest["train"][0]["snapshot_file_name"]
            (published_snapshot / "images" / "train" / first_train).unlink()
            self.assertIsNone(
                YoloDatasetBuilder._read_complete_manifest(
                    published_snapshot / "manifest.json",
                    published_snapshot / "data.yaml",
                    fingerprint,
                )
            )


class AnalyzerTests(unittest.TestCase):
    def test_detects_combined_overfitting_signal(self):
        metrics = []
        for epoch in range(1, 11):
            map_value = 0.7 + epoch * 0.01 if epoch <= 5 else 0.75 - (epoch - 5) * 0.01
            metrics.append(
                SimpleNamespace(
                    epoch=epoch,
                    map50_95=map_value,
                    map50=map_value + 0.1,
                    precision=0.9,
                    recall=0.7,
                    train_box_loss=1.2 - epoch * 0.05,
                    train_cls_loss=0.8 - epoch * 0.03,
                    train_dfl_loss=0.5 - epoch * 0.02,
                    val_box_loss=0.8 + epoch * 0.04,
                    val_cls_loss=0.5 + epoch * 0.03,
                    val_dfl_loss=0.3 + epoch * 0.02,
                )
            )
        result = TrainingAnalyzer()._build(
            SimpleNamespace(id=1, status="FINISHED"),
            metrics,
        )
        self.assertTrue(result["signals"]["possible_overfitting"])
        self.assertEqual(result["signals"]["precision_recall_imbalance"], "recall_low")
        self.assertEqual(result["summary"]["best_epoch"], 5)

    def test_segmentation_uses_mask_metrics_and_per_class_results(self):
        metrics = []
        for epoch in range(1, 6):
            metrics.append(
                SimpleNamespace(
                    epoch=epoch,
                    map50=0.6,
                    map50_95=0.4,
                    precision=0.7,
                    recall=0.65,
                    mask_map50=0.5 + epoch * 0.01,
                    mask_map50_95=0.3 + epoch * 0.01,
                    mask_precision=0.62,
                    mask_recall=0.58,
                    train_box_loss=0.8,
                    train_seg_loss=0.7 - epoch * 0.02,
                    train_cls_loss=0.5,
                    train_dfl_loss=0.4,
                    val_box_loss=0.7,
                    val_seg_loss=0.65 - epoch * 0.01,
                    val_cls_loss=0.45,
                    val_dfl_loss=0.35,
                    fitness=0.5,
                    per_class_metrics=[{"Class": "crack", "Mask-mAP50-95": 0.35}],
                )
            )

        result = TrainingAnalyzer()._build(
            SimpleNamespace(
                id=2,
                status="FINISHED",
                task=SimpleNamespace(detection_type="segmentation"),
            ),
            metrics,
        )

        self.assertEqual(result["task_type"], "segmentation")
        self.assertEqual(result["primary_metric"], "Mask mAP50-95")
        self.assertAlmostEqual(result["summary"]["final_map50_95"], 0.35)
        self.assertEqual(result["limitations"], [])
        self.assertEqual(result["per_class_metrics"][0]["Class"], "crack")

    def test_compares_optimized_run_with_parent(self):
        def metric(epoch, map_value, precision, recall):
            return SimpleNamespace(
                epoch=epoch,
                map50_95=map_value,
                map50=map_value + 0.2,
                precision=precision,
                recall=recall,
                train_box_loss=0.5,
                train_cls_loss=0.4,
                train_dfl_loss=0.3,
                val_box_loss=0.5,
                val_cls_loss=0.4,
                val_dfl_loss=0.3,
                per_class_metrics=[{"Class": "defect", "mAP50-95": map_value}],
            )

        result = TrainingAnalyzer()._build(
            SimpleNamespace(id=11, status="FINISHED", parent_train_task_id=10),
            [metric(1, 0.56, 0.84, 0.78)],
            [metric(1, 0.51, 0.87, 0.73)],
        )

        comparison = result["comparison_to_parent"]
        self.assertEqual(comparison["parent_train_task_id"], 10)
        self.assertAlmostEqual(comparison["primary_metric_delta"], 0.05)
        self.assertAlmostEqual(comparison["recall_delta"], 0.05)
        self.assertTrue(comparison["improved"])
        self.assertTrue(any("来源训练任务#10" in item for item in result["evidence"]))

    def test_auto_analysis_without_metrics_does_not_call_model(self):
        service = AutoTrainingAnalysisService()
        with patch.object(service.model, "complete") as complete:
            result = service._generate_summary({"summary": {"metric_count": 0}})
        complete.assert_not_called()
        self.assertIn("没有采集到", result.reply)
        self.assertFalse(result.ready_to_apply)

    def test_auto_analysis_requests_complete_iterative_report(self):
        service = AutoTrainingAnalysisService()
        response = (
            '{"reply":"完整报告","config_patch":{},"changes":[],"questions":[],'
            '"warnings":[],"ready_to_apply":false}'
        )
        with patch.object(
            service.model,
            "complete",
            new=AsyncMock(return_value=response),
        ) as complete:
            result = service._generate_summary({"summary": {"metric_count": 1}})

        prompt = complete.await_args.args[0]
        self.assertIn("完整Markdown报告", prompt)
        self.assertIn("验收标准", prompt)
        self.assertIn("comparison_to_parent", prompt)
        self.assertEqual(result.reply, "完整报告")


class SkillTests(unittest.TestCase):
    def test_skill_requires_explicit_confirmation(self):
        path = (
            Path(__file__).parents[1]
            / "app/services/agent/skills/yolo-training-assistant/SKILL.md"
        )
        content = path.read_text(encoding="utf-8")
        self.assertIn("Explicitly ask the user to confirm", content)
        self.assertIn("single-use confirmation token", content)
        self.assertIn("Do not silently change or start", content)
        self.assertIn("persisted full configuration as the baseline", content)


if __name__ == "__main__":
    unittest.main()
