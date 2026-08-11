import asyncio
import re
from typing import List


class InMemoryTaskRepo:
    def __init__(self):
        self.tasks = {}
        # 存储每轮的详细指标（与数据库同步，用于 SSE 快速推送）
        self.epoch_metrics: dict[int, list[dict]] = {}
        # SSE 订阅者：task_id -> list of asyncio.Queue
        self._subscribers: dict[int, list[asyncio.Queue]] = {}

    def set_pid(self, task_id: int, pid: int):
        self._ensure(task_id)
        self.tasks[task_id]["pid"] = pid

    def set_status(self, task_id: int, status: str):
        self._ensure(task_id)
        self.tasks[task_id]["status"] = status

    def update_progress(self, task_id: int, current_epoch: int, total_epoch: int, progress: int):
        self._ensure(task_id)
        self.tasks[task_id].update({
            "current_epoch": current_epoch,
            "total_epoch": total_epoch,
            "progress": progress
        })

    def set_error(self, task_id: int, error: str):
        self._ensure(task_id)
        self.tasks[task_id]["error"] = error

    def set_output_path(self, task_id: int, output_path: str):
        self._ensure(task_id)
        self.tasks[task_id]["output_path"] = output_path

    def set_log_path(self, task_id: int, log_path: str):
        self._ensure(task_id)
        self.tasks[task_id]["log_path"] = log_path

    # ------------------------ # 每轮指标存储
    def add_epoch_metric(self, task_id: int, metric: dict):
        """存储单轮训练指标"""
        if task_id not in self.epoch_metrics:
            self.epoch_metrics[task_id] = []
        self.epoch_metrics[task_id].append(metric)

    def get_epoch_metrics(self, task_id: int) -> list[dict]:
        """获取某任务的所有轮次指标"""
        return self.epoch_metrics.get(task_id, [])

    # ------------------------ # SSE 订阅者管理
    def subscribe(self, task_id: int) -> asyncio.Queue:
        """注册一个 SSE 订阅者，返回 queue 用于推送"""
        self._ensure(task_id)
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].append(q)
        return q

    def unsubscribe(self, task_id: int, queue: asyncio.Queue):
        """移除 SSE 订阅者"""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
            except ValueError:
                pass

    async def broadcast(self, task_id: int, data: dict):
        """向某任务的所有订阅者推送数据"""
        if task_id not in self._subscribers:
            return
        dead_queues = []
        for q in self._subscribers[task_id]:
            try:
                await q.put(data)
            except Exception:
                dead_queues.append(q)
        for q in dead_queues:
            try:
                self._subscribers[task_id].remove(q)
            except ValueError:
                pass

    def cleanup(self, task_id: int):
        """清理任务的内存数据（训练结束后调用）"""
        if task_id in self._subscribers:
            self._subscribers.pop(task_id, None)

    def _ensure(self, task_id: int):
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
