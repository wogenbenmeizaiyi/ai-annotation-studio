import os
import subprocess
import sys
from pathlib import Path


def test_multimodal_worker_import_does_not_load_gpu_libraries() -> None:
    service_root = Path(__file__).resolve().parents[1]
    source_roots = [
        service_root / "api" / "src",
        service_root / "worker" / "src",
        service_root / "consumer" / "src",
        service_root / "core" / "src",
        service_root / "engine" / "src",
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_roots)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import worker_server_multimodal; "
                "blocked = {'torch', 'ultralytics', 'cv2', 'numpy'} & sys.modules.keys(); "
                "assert not blocked, blocked"
            ),
        ],
        cwd=service_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
