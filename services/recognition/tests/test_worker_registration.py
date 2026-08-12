import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from celery.exceptions import Reject

from core.mq import GPU_TASK_NAME, MULTIMODAL_TASK_NAME


@pytest.mark.parametrize(
    ("worker_module", "expected_tasks", "blocked_modules"),
    [
        (
            "worker_server_gpu",
            {GPU_TASK_NAME, MULTIMODAL_TASK_NAME},
            set(),
        ),
        (
            "worker_server_multimodal",
            {GPU_TASK_NAME, MULTIMODAL_TASK_NAME},
            {"torch", "ultralytics", "cv2", "numpy"},
        ),
    ],
)
def test_each_worker_registers_guards_for_both_task_names(
    worker_module: str,
    expected_tasks: set[str],
    blocked_modules: set[str],
) -> None:
    service_root = Path(__file__).resolve().parents[1]
    source_roots = [
        service_root / "worker" / "src",
        service_root / "core" / "src",
        service_root / "engine" / "src",
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_roots)
    code = (
        f"import sys; import {worker_module} as worker; "
        "registered = {name for name in worker.celery_app.tasks "
        "if name.startswith('recognition.')}; "
        f"assert registered == {expected_tasks!r}, registered; "
        f"blocked = {blocked_modules!r} & sys.modules.keys(); "
        "assert not blocked, blocked"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=service_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_wrong_worker_guard_uses_celery_message_id(monkeypatch) -> None:
    import worker_server_multimodal
    from tasks import rejected

    mark_failed = Mock()
    monkeypatch.setattr(rejected, "mark_task_failed", mark_failed)
    task = worker_server_multimodal.celery_app.tasks[GPU_TASK_NAME]

    result = task.apply(
        kwargs={"detection_type": 1},
        task_id="celery-message-id",
        throw=True,
    )

    assert isinstance(result.result, Reject)
    assert result.result.requeue is False
    mark_failed.assert_called_once()
    assert mark_failed.call_args.args[0] == "celery-message-id"
