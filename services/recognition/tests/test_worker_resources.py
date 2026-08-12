import pytest

from tasks import resources
from tasks import gpu_resources


@pytest.mark.asyncio
async def test_multimodal_resource_wait_does_not_check_gpu(monkeypatch) -> None:
    monkeypatch.setattr(resources.config, "RESOURCE_CHECK_ENABLED", True)
    monkeypatch.setattr(
        resources,
        "available_system_memory_mb",
        lambda: resources.config.RESOURCE_MIN_SYSTEM_MEMORY_MB,
    )

    await resources.wait_for_system_resources("task-123", 1)


def test_gpu_resources_are_not_ready_without_cuda(monkeypatch) -> None:
    monkeypatch.setattr(gpu_resources, "available_system_memory_mb", lambda: 4096)
    monkeypatch.setattr(gpu_resources, "available_gpu_memory_mb", lambda: None)

    ready, system_free_mb, gpu_free_mb = gpu_resources.gpu_resources_ready()

    assert ready is False
    assert system_free_mb == 4096
    assert gpu_free_mb is None
