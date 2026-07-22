import logging
import uuid
from io import BytesIO
from abc import abstractmethod
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from ultralytics.models.sam import SAM3SemanticPredictor

from core.config import config
from core.schemas.recognition import (
    RawDetection,
    RecognitionRequest,
    RecognitionResponse,
)
from engine.services.base_service import BaseRecognitionService

logger = logging.getLogger(__name__)


class SamBaseService(BaseRecognitionService):
    def __init__(self, name: str, models_dir: Path | None = None) -> None:
        super().__init__(name)
        self._models_dir = models_dir or Path(config.MODELS_DIR).resolve() / "sam"
        self._predictor: SAM3SemanticPredictor | None = None

    def _get_predictor(self, model_name: str) -> SAM3SemanticPredictor:
        if self._predictor is None:
            pt_file = self._models_dir / f"{model_name}.pt"
            if not pt_file.exists():
                raise FileNotFoundError(f"SAM model not found: {pt_file}")
            self._predictor = SAM3SemanticPredictor(
                overrides={
                    "conf": 0.25,
                    "task": "segment",
                    "mode": "predict",
                    "model": str(pt_file),
                    "device": "cuda",  # 强制使用 GPU
                    "half": True,  # 开启半精度加速 (需配合 GPU)
                    "imgsz": config.SAM_IMAGE_SIZE,
                    "verbose": False,
                    "save": False,
                }
            )
        if self._predictor is None:
            raise RuntimeError("SAM-3 predictor initialization failed")
        return self._predictor

    def _release_model_resources(self) -> None:
        self._predictor = None

    def _run_segmentation(
        self, image: Image.Image, text_prompts: list[str], model_name: str
    ) -> tuple[list[RawDetection], np.ndarray | None]:
        predictor = self._get_predictor(model_name)
        predictor.set_image(image)
        results = predictor(text=text_prompts)

        items: list[RawDetection] = []
        result_img: np.ndarray | None = None

        if results and results[0].masks is not None and results[0].boxes is not None:
            masks_data = results[0].masks.data.cpu().numpy()
            boxes = results[0].boxes

            for i in range(len(masks_data)):
                x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i].cpu().numpy()]
                segmentation = self._simplify_mask(masks_data[i])

                items.append(
                    RawDetection(
                        bbox=[x1, y1, x2 - x1, y2 - y1],
                        score=(
                            float(boxes.conf[i].item())
                            if boxes.conf is not None
                            else 0.0
                        ),
                        segmentation=segmentation,
                    )
                )

            result_img = results[0].plot()

        return items, result_img

    @staticmethod
    def _simplify_mask(mask: np.ndarray) -> list[list[float]]:
        """将 SAM 的二值掩膜压缩为保留外轮廓的 COCO 多边形。"""
        binary_mask = (mask > 0).astype(np.uint8)
        contours, _ = cv2.findContours(
            binary_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        polygons: list[list[float]] = []
        for contour in contours:
            epsilon = max(config.SAM_SEGMENTATION_EPSILON, 0.0)
            simplified = cv2.approxPolyDP(contour, epsilon, True)
            if len(simplified) < 3:
                continue
            polygon = simplified.reshape(-1, 2).astype(float).flatten().tolist()
            if len(polygon) >= 6:
                polygons.append(polygon)
        return polygons

    @abstractmethod
    def _draw_annotated(
        self, image: Image.Image, items: list[dict], prompts: list[str]
    ) -> Image.Image: ...

    def _parse_prompts(self, detection_type: str) -> tuple[str, list[str]]:
        parts = detection_type.split("|", 1)
        if len(parts) == 2:
            return parts[0].strip(), [
                p.strip() for p in parts[1].split(",") if p.strip()
            ]
        return "sam3", [p.strip() for p in detection_type.split(",") if p.strip()]

    async def recognize(self, request: RecognitionRequest) -> RecognitionResponse:
        model_name, text_prompts = self._parse_prompts(request.detection_type)

        if not text_prompts:
            raise ValueError(f"{self._name} requires text prompts in detection_type")

        if request.image_path:
            image = Image.open(request.image_path).convert("RGB")
        elif request.image_data:
            image = Image.open(BytesIO(request.image_data)).convert("RGB")
        else:
            raise ValueError("No image provided")
        image_id = str(uuid.uuid4())
        ext = request.extra.get("image_ext", "jpg")
        detections, _ = self._run_segmentation(image, text_prompts, model_name)

        logger.info(
            "%s: prompts=%s, count=%d", self._name, text_prompts, len(detections)
        )
        return self.build_coco_response(
            request,
            image,
            detections,
            image_id,
            ext,
            self.name,
        )
