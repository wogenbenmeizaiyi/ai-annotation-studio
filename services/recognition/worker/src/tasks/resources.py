import asyncio
import logging
import time
from pathlib import Path

import torch

from core.config import config

logger = logging.getLogger(__name__)


def _available_system_memory_mb() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None

    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) // 1024
    return None


def _available_gpu_memory_mb() -> int | None:
    if not torch.cuda.is_available():
        return None

    free_bytes, _total_bytes = torch.cuda.mem_get_info()
    return free_bytes // 1024 // 1024


def _resources_ready() -> tuple[bool, int | None, int | None]:
    system_free_mb = _available_system_memory_mb()
    gpu_free_mb = _available_gpu_memory_mb()

    system_ready = (
        system_free_mb is None
        or system_free_mb >= config.RESOURCE_MIN_SYSTEM_MEMORY_MB
    )
    gpu_ready = (
        gpu_free_mb is None or gpu_free_mb >= config.RESOURCE_MIN_GPU_MEMORY_MB
    )
    return system_ready and gpu_ready, system_free_mb, gpu_free_mb


async def wait_for_resources(task_id: str, image_index: int) -> None:
    """等待系统/GPU 空闲资源达到阈值后再开始识别。"""
    if not config.RESOURCE_CHECK_ENABLED:
        return

    started_at = time.monotonic()
    interval = max(config.RESOURCE_CHECK_INTERVAL_SECONDS, 1)
    timeout = max(config.RESOURCE_WAIT_TIMEOUT_SECONDS, 0)

    while True:
        ready, system_free_mb, gpu_free_mb = _resources_ready()
        if ready:
            return

        elapsed = time.monotonic() - started_at
        if timeout and elapsed >= timeout:
            raise TimeoutError(
                "resource wait timeout: "
                f"system_free_mb={system_free_mb}, gpu_free_mb={gpu_free_mb}"
            )

        logger.info(
            "Task %s: waiting for resources before image %d "
            "system_free_mb=%s min_system_mb=%s gpu_free_mb=%s min_gpu_mb=%s",
            task_id,
            image_index,
            system_free_mb,
            config.RESOURCE_MIN_SYSTEM_MEMORY_MB,
            gpu_free_mb,
            config.RESOURCE_MIN_GPU_MEMORY_MB,
        )
        await asyncio.sleep(interval)
