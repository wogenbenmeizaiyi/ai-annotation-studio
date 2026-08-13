import ctypes
import gc
import logging

import torch

logger = logging.getLogger(__name__)


def release_process_memory() -> None:
    """释放进程内存：GC + glibc trim + CUDA 缓存清理。

    模型权重从 Python 引用中移除后，进程 RSS 不会自动归还给操作系统
    （glibc 会保留空闲堆块），需要显式调用 malloc_trim(0) 让 glibc
    归还堆顶空闲内存。该函数仅对 Linux 生效，其他平台安全跳过。
    """
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
    except (OSError, AttributeError):
        logger.debug("malloc_trim 不可用，跳过进程内存归还")
