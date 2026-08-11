import logging
import math
import os
import re
import base64
import uuid
from io import BytesIO
from typing import Any
import requests

from PIL import Image, ImageDraw, ImageFont

from core.schemas.recognition import (
    RawDetection,
    RecognitionRequest,
    RecognitionResponse,
    RecognitionMethod,
)
from engine.services.base_service import BaseRecognitionService

logger = logging.getLogger(__name__)

MAX_IMAGE_DIM = 1024
RESPONSE_FORMAT_PROMPT = """
请根据用户的提示词(对象/目标名称)，识别图片中对应的目标，**只返回用户指定的物体的结果**；如果用户未指定，则不返回任何内容。
注意：严格按照以下 JSON 格式返回结果，不要输出其他内容：
```json
{
  "description": "对图片的整体描述",
  "objects": [
    {
      "name": "对象/目标名称(与提示词一致)",
      "confidence": 0.9,
      "bbox": {"x1": 左上 x, "y1": 左上 y, "x2": 右下 x, "y2": 右下 y},
      "description": "该物体的其他描述"
    }
  ]
}
```
坐标说明：x1/y1 是左上角坐标，x2/y2 是右下角坐标。请根据你实际看到的图片尺寸返回像素坐标。
如果没有检测到任何目标，objects 返回空数组 []。
"""


class MultimodalService(BaseRecognitionService):
    method = RecognitionMethod.MULTIMODAL

    def __init__(self, endpoint: str | None = None) -> None:
        super().__init__("multimodal")
        self._endpoint = (
            endpoint
            or "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        )
        self._model_env_map: dict[str, str] = {"qwen-vl-plus": "QWEN_API_KEY"}

    def _get_api_key(self, model_name: str) -> str:
        env_var = self._model_env_map.get(model_name, "")
        if not env_var:
            raise ValueError(f"Unsupported multimodal model: '{model_name}'")
        key = os.getenv(env_var, "")
        if not key:
            raise ValueError(f"Environment variable '{env_var}' not configured")
        return key

    def _resize_for_api(self, image: Image.Image) -> tuple[Image.Image, int, int]:
        orig_w, orig_h = image.size
        if max(orig_w, orig_h) <= MAX_IMAGE_DIM:
            return image, orig_w, orig_h
        ratio = MAX_IMAGE_DIM / max(orig_w, orig_h)
        resized = image.resize(
            (int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.LANCZOS
        )
        return resized, orig_w, orig_h

    def _scale_coords(
        self, coords: dict[str, float], from_w: int, from_h: int, to_w: int, to_h: int
    ) -> dict[str, float]:
        sx = to_w / from_w if from_w > 0 else 1.0
        sy = to_h / from_h if from_h > 0 else 1.0
        return {
            "x1": round(coords.get("x1", 0) * sx, 1),
            "y1": round(coords.get("y1", 0) * sy, 1),
            "x2": round(coords.get("x2", 0) * sx, 1),
            "y2": round(coords.get("y2", 0) * sy, 1),
        }

    def _parse_json_from_response(self, text: str) -> dict[str, Any]:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            import json

            return json.loads(json_match.group())
        raise ValueError(f"无法从响应中解析 JSON: {text[:200]}")

    def _extract_objects_and_scale(
        self,
        parsed: dict[str, Any],
        resized_w: int,
        resized_h: int,
        orig_w: int,
        orig_h: int,
    ) -> list[RawDetection]:
        result: list[RawDetection] = []
        for obj in parsed.get("objects", []):
            confidence = obj.get("confidence", 0.0)
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                logger.warning("Skipping multimodal object with invalid confidence")
                continue

            if not math.isfinite(confidence) or confidence <= 0:
                logger.info("Skipping multimodal object with non-positive confidence")
                continue

            raw_bbox = obj.get("bbox", {})
            if isinstance(raw_bbox, list) and len(raw_bbox) >= 4:
                bbox_dict = {
                    "x1": raw_bbox[0],
                    "y1": raw_bbox[1],
                    "x2": raw_bbox[2],
                    "y2": raw_bbox[3],
                }
            elif isinstance(raw_bbox, dict):
                bbox_dict = raw_bbox
            else:
                logger.warning("Skipping multimodal object with invalid bbox format")
                continue

            try:
                bbox_dict = {
                    key: float(bbox_dict[key]) for key in ("x1", "y1", "x2", "y2")
                }
            except (KeyError, TypeError, ValueError):
                logger.warning("Skipping multimodal object with incomplete bbox")
                continue

            scaled_bbox = self._scale_coords(
                bbox_dict, resized_w, resized_h, orig_w, orig_h
            )
            if (
                not all(math.isfinite(value) for value in scaled_bbox.values())
                or scaled_bbox["x2"] <= scaled_bbox["x1"]
                or scaled_bbox["y2"] <= scaled_bbox["y1"]
            ):
                logger.warning("Skipping multimodal object with invalid bbox bounds")
                continue

            result.append(
                RawDetection(
                    bbox=[
                        scaled_bbox["x1"],
                        scaled_bbox["y1"],
                        scaled_bbox["x2"] - scaled_bbox["x1"],
                        scaled_bbox["y2"] - scaled_bbox["y1"],
                    ],
                    score=confidence,
                )
            )
        return result

    @staticmethod
    def _image_to_base64(img: Image.Image) -> str:
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _draw_boxes_on_image(
        self, image: Image.Image, objects: list[dict[str, Any]], prompt: str
    ) -> Image.Image:
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        max_dim = max(image.size)
        scale = (
            2.0
            if max_dim > 2048
            else 1.0
            if max_dim > 1024
            else 0.5
            if max_dim > 512
            else 0.25
        )
        line_width = max(1, int(6 * scale))
        font_size = max(10, int(36 * scale))
        padding = max(1, int(4 * scale))
        offset = max(10, int(50 * scale))
        font: Any = None
        try:
            font = ImageFont.truetype("msyh.ttc", size=font_size)
        except OSError:
            font = ImageFont.load_default()
        color = "#FF0000"
        for obj in objects:
            x1, y1, bw, bh = obj["bbox"]
            draw.rectangle([x1, y1, x1 + bw, y1 + bh], outline=color, width=line_width)
            label = f"{prompt} {obj['confidence']:.2f}"
            text_bbox = draw.textbbox((x1, y1 - offset), label, font=font)
            draw.rectangle(
                [
                    text_bbox[0] - padding,
                    text_bbox[1] - padding,
                    text_bbox[2] + padding,
                    text_bbox[3] + padding,
                ],
                fill=color,
            )
            draw.text((x1, y1 - offset), label, fill="white", font=font)
        return img_copy

    async def recognize(self, request: RecognitionRequest) -> RecognitionResponse:
        params = self._parse_params(request.detection_type)
        model_name = params.get("model", "qwen-vl-plus")
        prompt = params.get("prompt", "")

        api_key = self._get_api_key(model_name)

        if request.image_path:
            image = Image.open(request.image_path).convert("RGB")
        elif request.image_data:
            image = Image.open(BytesIO(request.image_data)).convert("RGB")
        else:
            raise ValueError("No image provided")
        image_id = str(uuid.uuid4())
        ext = request.extra.get("image_ext", "jpg")

        resized_img, orig_w, orig_h = self._resize_for_api(image)
        resized_w, resized_h = resized_img.size
        full_prompt = f"{prompt}\n{RESPONSE_FORMAT_PROMPT}".strip()
        resized_base64 = self._image_to_base64(resized_img)

        raw_response = self._call_qwen_vl(
            model_name, api_key, resized_base64, full_prompt
        )
        logger.info("API response: %s", raw_response[:200])

        try:
            parsed = self._parse_json_from_response(raw_response)
        except (ValueError, Exception) as e:
            logger.warning("JSON parse failed: %s", e)
            return self.build_coco_response(
                request,
                image,
                [],
                image_id,
                ext,
                self.name,
            )

        objects = self._extract_objects_and_scale(
            parsed, resized_w, resized_h, orig_w, orig_h
        )

        logger.info("Parsed %d objects", len(objects))
        return self.build_coco_response(
            request,
            image,
            objects,
            image_id,
            ext,
            self.name,
        )

    def _call_qwen_vl(
        self, model_id: str, api_key: str, image_b64: str, prompt: str
    ) -> str:
        logger.info("Qwen-VL API call (model: %s)", model_id)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        response = requests.post(
            self._endpoint, headers=headers, json=payload, timeout=120
        )
        response.raise_for_status()
        result = response.json()
        choices = result.get("choices", [])
        if not choices:
            logger.warning("Empty choices: %s", result)
            return '{"description": "API returned empty", "objects": []}'
        return choices[0].get("message", {}).get("content", "")

    @staticmethod
    def _parse_params(detection_type: str) -> dict[str, str]:
        parts = detection_type.split("|", 1)
        if len(parts) == 2:
            return {"model": parts[0].strip(), "prompt": parts[1].strip()}
        return {"model": "qwen-vl-plus", "prompt": detection_type}
