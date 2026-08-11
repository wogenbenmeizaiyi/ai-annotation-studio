import logging
import base64
import uuid
from io import BytesIO
from pathlib import Path
import numpy as np

from PIL import Image
from ultralytics import YOLO

from core.config import config
from core.schemas.recognition import (
    RawDetection,
    RecognitionRequest,
    RecognitionResponse,
    RecognitionMethod,
)
from engine.services.base_service import BaseRecognitionService

logger = logging.getLogger(__name__)


def _image_to_base64(img: Image.Image) -> str:
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class YoloSegmentationService(BaseRecognitionService):
    method = RecognitionMethod.YOLO_SEGMENTATION

    def __init__(self, models_dir: Path | None = None) -> None:
        super().__init__("yolo_segmentation")
        self._models_dir = (
            models_dir or Path(config.MODELS_DIR).resolve() / "yolo" / "segmentation"
        )
        self._model_cache: dict[str, YOLO] = {}

    def load_model(self, model_name: str) -> YOLO:
        if model_name in self._model_cache:
            return self._model_cache[model_name]
        pt_file = self._models_dir / f"{model_name}.pt"
        if not pt_file.exists():
            raise FileNotFoundError(f"YOLO segmentation model not found: {pt_file}")
        model = YOLO(str(pt_file))
        self._model_cache[model_name] = model
        return model

    def _release_model_resources(self) -> None:
        self._model_cache.clear()

    async def recognize(self, request: RecognitionRequest) -> RecognitionResponse:
        model = self.load_model(request.detection_type)

        if request.image_path:
            image = Image.open(request.image_path).convert("RGB")
        elif request.image_data:
            image = Image.open(BytesIO(request.image_data)).convert("RGB")
        else:
            raise ValueError("No image provided")
        results = model.predict(
            source=image, conf=request.confidence, save=False, verbose=False
        )

        detections: list[RawDetection] = []

        for result in results:
            masks = result.masks
            boxes = result.boxes
            if masks is None or boxes is None:
                continue
            for i in range(len(masks)):
                conf = float(boxes.conf[i].item())
                x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i]]

                mask_array = masks[i].data.cpu().numpy()[0]
                ys, xs = np.where(mask_array > 0)
                segmentation = []
                if len(ys) > 0:
                    segmentation = (
                        np.column_stack([xs.astype(float), ys.astype(float)])
                        .flatten()
                        .tolist()
                    )

                detections.append(
                    RawDetection(
                        bbox=[x1, y1, x2 - x1, y2 - y1],
                        score=conf,
                        segmentation=[segmentation],
                    )
                )

        image_id = str(uuid.uuid4())
        ext = request.extra.get("image_ext", "jpg")

        logger.info(
            "YOLO segmentation: model=%s, count=%d",
            request.detection_type,
            len(detections),
        )
        return self.build_coco_response(
            request,
            image,
            detections,
            image_id,
            ext,
            self.name,
        )
