import asyncio
import gc
import logging
import time

import torch

from core.config import config
from tasks.resources import available_system_memory_mb

logger = logging.getLogger(__name__)


def available_gpu_memory_mb() -> int | None:
    if not torch.cuda.is_available():
        return None
    free_bytes, _total_bytes = torch.cuda.mem_get_info()
    return free_bytes // 1024 // 1024


def gpu_resources_ready() -> tuple[bool, int | None, int | None]:
    system_free_mb = available_system_memory_mb()
    gpu_free_mb = available_gpu_memory_mb()
    system_ready = (
        system_free_mb is None
        or system_free_mb >= config.RESOURCE_MIN_SYSTEM_MEMORY_MB
    )
    gpu_ready = (
        gpu_free_mb is not None and gpu_free_mb >= config.RESOURCE_MIN_GPU_MEMORY_MB
    )
    return system_ready and gpu_ready, system_free_mb, gpu_free_mb


async def wait_for_gpu_resources(task_id: str, image_index: int) -> None:
    """同时等待系统内存与 GPU 显存达到阈值。"""
    if not config.RESOURCE_CHECK_ENABLED:
        return

    started_at = time.monotonic()
    interval = max(config.RESOURCE_CHECK_INTERVAL_SECONDS, 1)
    timeout = max(config.RESOURCE_WAIT_TIMEOUT_SECONDS, 0)
    while True:
        ready, system_free_mb, gpu_free_mb = gpu_resources_ready()
        if ready:
            return
        elapsed = time.monotonic() - started_at
        if timeout and elapsed >= timeout:
            raise TimeoutError(
                "resource wait timeout: "
                f"system_free_mb={system_free_mb}, gpu_free_mb={gpu_free_mb}"
            )
        logger.info(
            "Task %s: waiting for GPU resources before image %d "
            "system_free_mb=%s min_system_mb=%s gpu_free_mb=%s min_gpu_mb=%s",
            task_id,
            image_index,
            system_free_mb,
            config.RESOURCE_MIN_SYSTEM_MEMORY_MB,
            gpu_free_mb,
            config.RESOURCE_MIN_GPU_MEMORY_MB,
        )
        await asyncio.sleep(interval)


def release_gpu_cache() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
