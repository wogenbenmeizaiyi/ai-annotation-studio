"""SAM3 分割服务 - 管理图片状态和交互式分割"""

import gc
import io
import logging
import numpy as np
from typing import List, Optional, Dict, Any

import cv2
import torch
from PIL import Image
from ultralytics import SAM

from app.core.config import settings
from app.core.s3.s3_client import s3
from app.core.sam3.sam3_registry import SAM3Registry

logger = logging.getLogger(__name__)

S3_BUCKET = settings.S3_BUCKET_NAME


class SAM3Session:
    """单个图片的 SAM3 交互会话"""

    def __init__(self, model: SAM, device: str, image: np.ndarray):
        self.model = model
        self.device = device
        self.image = image
        self.points: List[List[int]] = []
        self.labels: List[int] = []
        self.results: Optional[Any] = None

    def add_point(self, x: int, y: int, label: int = 1) -> Dict[str, Any]:
        """添加交互点并立即执行分割

        Args:
            x: x坐标
            y: y坐标
            label: 1=前景, 0=背景

        Returns:
            分割结果字典
        """
        self.points.append([x, y])
        self.labels.append(label)
        return self._predict()

    def add_bbox_point(self, x: int, y: int, label: int = 1) -> Dict[str, Any]:
        """添加交互点并返回分割区域外接框"""
        self.points.append([x, y])
        self.labels.append(label)
        return self._predict_bboxes()

    def reset(self) -> None:
        """重置交互点"""
        self.points = []
        self.labels = []
        self.results = None
        self._release_cache()

    def close(self) -> None:
        """释放当前会话持有的图片和推理结果"""
        self.points = []
        self.labels = []
        self.results = None
        self.image = None
        self.model = None
        self._release_cache()

    def _predict(self) -> Dict[str, Any]:
        """执行 SAM3 推理"""
        if len(self.points) == 0:
            return {"success": False, "message": "没有交互点"}

        try:
            results = self.model.predict(
                source=self.image,
                points=self.points,
                labels=self.labels,
                device=self.device,
                verbose=False,
            )
            self.results = results

            masks_data = []
            for result in results:
                if result.masks is not None:
                    for i, mask in enumerate(result.masks):
                        mask_array = mask.data.cpu().numpy()
                        contours = self._mask_to_contours(mask_array)
                        if not contours:
                            continue
                        masks_data.append(
                            {
                                "contours": contours,
                                "area": float(np.sum(mask_array)),
                            }
                        )

            return {
                "success": True,
                "point_count": len(self.points),
                "masks": masks_data,
            }
        except Exception as e:
            logger.error(f"SAM3 推理失败: {str(e)}")
            return {"success": False, "message": f"推理失败: {str(e)}"}

    def _predict_bboxes(self) -> Dict[str, Any]:
        """执行 SAM3 推理并返回 mask 外接框"""
        if len(self.points) == 0:
            return {"success": False, "message": "没有交互点"}

        try:
            results = self.model.predict(
                source=self.image,
                points=self.points,
                labels=self.labels,
                device=self.device,
                verbose=False,
            )
            self.results = results

            bboxes_data = []
            for result in results:
                if result.masks is not None:
                    for mask in result.masks:
                        mask_array = mask.data.cpu().numpy()
                        bbox = self._mask_to_bbox(mask_array)
                        if bbox is None:
                            continue

                        x, y, w, h = bbox
                        bboxes_data.append(
                            {
                                "bbox": bbox,
                                "points": [
                                    [x, y],
                                    [x + w, y],
                                    [x + w, y + h],
                                    [x, y + h],
                                ],
                                "area": float(w * h),
                            }
                        )

            return {
                "success": True,
                "point_count": len(self.points),
                "bboxes": bboxes_data,
            }
        except Exception as e:
            logger.error(f"SAM3 bbox 推理失败: {str(e)}")
            return {"success": False, "message": f"推理失败: {str(e)}"}

    def _mask_to_contours(self, mask: np.ndarray) -> List[List[List[float]]]:
        """将 mask 转为 COCO 格式多边形：只取最大外轮廓，并用 Douglas-Peucker 简化点数"""
        mask_uint8 = (mask[0] * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return []

        largest = max(contours, key=cv2.contourArea)

        if len(largest) < 3:
            return []

        epsilon = 0.005 * cv2.arcLength(largest, True)
        simplified = cv2.approxPolyDP(largest, epsilon, True)

        if len(simplified) < 3:
            return []

        return [simplified.flatten().tolist()]

    def _mask_to_bbox(self, mask: np.ndarray) -> Optional[List[float]]:
        """将 mask 转为扩展后的 COCO bbox 格式：[x, y, width, height]"""
        mask_uint8 = (mask[0] > 0).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) <= 0:
            return None

        x, y, w, h = cv2.boundingRect(largest)
        return self._expand_bbox(float(x), float(y), float(w), float(h), 0.1)

    def _expand_bbox(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        ratio: float,
    ) -> List[float]:
        """按比例向四周扩展 bbox，并限制在图片边界内"""
        image_height, image_width = self.image.shape[:2]
        expand_w = w * ratio / 2
        expand_h = h * ratio / 2

        x1 = max(0.0, x - expand_w)
        y1 = max(0.0, y - expand_h)
        x2 = min(float(image_width), x + w + expand_w)
        y2 = min(float(image_height), y + h + expand_h)

        return [x1, y1, x2 - x1, y2 - y1]

    def _release_cache(self) -> None:
        """释放 Python 和 CUDA 缓存"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class SAM3Service:
    """SAM3 服务 - 管理所有会话"""

    def __init__(self):
        self.registry = SAM3Registry()
        self.sessions: Dict[str, SAM3Session] = {}

    def create_session(self, s3_key: str) -> SAM3Session:
        """根据 s3_key 创建新会话，从 S3 下载图片并初始化"""
        image_bytes = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)["Body"].read()

        pil_image = Image.open(io.BytesIO(image_bytes))
        image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        model = self.registry.get_model()
        device = self.registry.get_device()
        session = SAM3Session(model, device, image)
        self.sessions[s3_key] = session
        logger.info(f"SAM3 会话创建: {s3_key}")
        return session

    def get_session(self, s3_key: str) -> Optional[SAM3Session]:
        """获取已有会话"""
        return self.sessions.get(s3_key)

    def remove_session(self, s3_key: str) -> None:
        """移除会话释放内存"""
        session = self.sessions.pop(s3_key, None)
        if session is not None:
            session.close()
            logger.info(f"SAM3 会话移除: {s3_key}")
        if not self.sessions:
            self.registry.unload_model()
