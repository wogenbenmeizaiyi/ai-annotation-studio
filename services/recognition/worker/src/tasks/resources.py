import asyncio
import logging
import time
from pathlib import Path

from core.config import config

logger = logging.getLogger(__name__)


def available_system_memory_mb() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) // 1024
    return None


def system_resources_ready() -> tuple[bool, int | None]:
    system_free_mb = available_system_memory_mb()
    ready = (
        system_free_mb is None
        or system_free_mb >= config.RESOURCE_MIN_SYSTEM_MEMORY_MB
    )
    return ready, system_free_mb


async def wait_for_system_resources(task_id: str, image_index: int) -> None:
    """只等待系统内存，供不使用 GPU 的多模态 worker 调用。"""
    if not config.RESOURCE_CHECK_ENABLED:
        return
    started_at = time.monotonic()
    interval = max(config.RESOURCE_CHECK_INTERVAL_SECONDS, 1)
    timeout = max(config.RESOURCE_WAIT_TIMEOUT_SECONDS, 0)
    while True:
        ready, system_free_mb = system_resources_ready()
        if ready:
            return
        elapsed = time.monotonic() - started_at
        if timeout and elapsed >= timeout:
            raise TimeoutError(
                f"resource wait timeout: system_free_mb={system_free_mb}"
            )
        logger.info(
            "Task %s: waiting for system resources before image %d "
            "system_free_mb=%s min_system_mb=%s",
            task_id,
            image_index,
            system_free_mb,
            config.RESOURCE_MIN_SYSTEM_MEMORY_MB,
        )
        await asyncio.sleep(interval)


# 保留旧名称，其语义现在明确为仅检查系统内存。
wait_for_resources = wait_for_system_resources
