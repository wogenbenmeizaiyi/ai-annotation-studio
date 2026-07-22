"""SAM3 模型注册单例 - 启动时预加载模型"""

import gc
import logging
import os
import torch

from app.core.config import settings

logger = logging.getLogger(__name__)


class SAM3Registry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SAM3Registry, cls).__new__(cls)
        return cls._instance

    def load_model(self):
        """预加载 SAM3 模型，应在服务启动时调用"""
        if hasattr(self, "_model") and self._model is not None:
            return

        from ultralytics import SAM

        model_path = settings.SAM3_MODEL_PATH
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"SAM3 模型文件不存在: {model_path}")

        logger.info(f"正在预加载 SAM3 模型: {model_path}")
        self._model = SAM(model_path)
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"SAM3 模型加载完成, 设备: {self._device}")

    def get_model(self):
        if not hasattr(self, "_model") or self._model is None:
            self.load_model()
        return self._model

    def get_device(self) -> str:
        if not hasattr(self, "_device"):
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        return self._device

    def unload_model(self) -> None:
        """卸载 SAM3 模型并释放 CUDA 缓存"""
        if not hasattr(self, "_model") or self._model is None:
            return

        if hasattr(self._model, "predictor"):
            self._model.predictor = None
        self._model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        logger.info("SAM3 模型已卸载，CUDA 缓存已释放")
