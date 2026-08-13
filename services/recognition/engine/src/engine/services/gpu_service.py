from core.memory import release_process_memory

from engine.services.base_service import BaseRecognitionService


class GpuRecognitionService(BaseRecognitionService):
    """需要 GPU 的识别服务基类。"""

    def release_resources(self) -> None:
        self._release_model_resources()
        release_process_memory()
