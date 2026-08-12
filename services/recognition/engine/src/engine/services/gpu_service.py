import gc

import torch

from engine.services.base_service import BaseRecognitionService


class GpuRecognitionService(BaseRecognitionService):
    """需要 GPU 的识别服务基类。"""

    def release_resources(self) -> None:
        self._release_model_resources()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
