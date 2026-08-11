# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

Python 3.12+, `uv` package manager. FastAPI REST API (port 7987) + Celery worker via RabbitMQ.
4 recognition services inheriting from `BaseRecognitionService` (YOLO, SAM, Qwen-VL).

## Commands

### Package Management
```bash
uv sync                         # Install all deps (incl. dev)
uv add <package>                # Add runtime dep
uv add --dev <package>          # Add dev dep
uv run <script>                 # Run Python with project env
```

### Running the App
```bash
# API server
PYTHONPATH=api/src:worker/src:consumer/src:core/src:engine/src uv run uvicorn api_server:app --host 0.0.0.0 --port 7987 --reload

# Celery worker (Windows: solo pool is auto-configured in worker/src/worker_server.py)
PYTHONPATH=api/src:worker/src:consumer/src:core/src:engine/src uv run celery -A worker_server.celery_app worker --loglevel=info --pool=solo

# Flower monitoring
PYTHONPATH=api/src:worker/src:consumer/src:core/src:engine/src uv run celery -A worker_server.celery_app flower

# Quick start scripts
.\start.ps1                     # PowerShell — starts API + worker via .venv directly
bash start.sh start             # Linux — background daemon with start|stop|status
```

### Testing
```bash
uv run pytest                                    # Run all tests (currently no test files)
uv run pytest path/to/file.py::TestClass::test_method  # Single test
uv run pytest -k keyword                         # Keyword match
uv run pytest -x                                 # Stop on first failure
uv run pytest -v                                 # Verbose output

# Result queue consumer (manual test script)
uv run python tests/consume_result_queue.py
```
- `pytest` config: `asyncio_mode = "auto"` (in `pyproject.toml`)
- The `tests/` directory currently only contains `consume_result_queue.py`

### Linting/Formatting
```bash
uv run ruff check .                # Lint
uv run ruff check --fix .          # Auto-fix lint issues
uv run ruff format .               # Format (in place)
uv run ruff format --check .       # Format check only
uv run mypy api/ worker/ consumer/ core/ engine/ tests/  # Type check
```

## Code Style

### Imports
- Order: stdlib → third-party → local; separate groups with blank lines
- Cross-module absolute imports use `from core...` and `from engine...`; process-local code may import local `routes`, `services`, or `tasks`
- Multi-line imports use parentheses with trailing commas
- Re-export public API via `__init__.py` where a package is consumed by another module

### Formatting
- 4-space indent, max line length **88** (ruff/Black default)
- `target-version = "py312"` in ruff config
- Trailing commas on multi-line dicts, lists, function signatures

### Naming
| Element | Convention | Example |
|---|---|---|
| Classes | PascalCase | `Config`, `RabbitMQConnection` |
| Functions/Variables | snake_case | `load_model`, `queue_name` |
| Constants | UPPER_SNAKE_CASE | `RABBITMQ_HOST`, `S3_BUCKET` |
| Modules/files | snake_case, lowercase | `base_service.py` |
| Private members | Leading underscore | `_model_cache`, `_publish_to_queue` |
| Celery tasks | snake_case | `recognize_image` |

### Types
- Python 3.12 syntax: `X | Y` unions (not `typing.Union`/`Optional`)
- Built-in generics: `list[str]`, `dict[str, int]` (not `typing.List`)
- Type hints on all function signatures with explicit return types (`-> None`, `-> str`, etc.)
- `BaseRecognitionService` is an ABC with `@abstractmethod`
- Use dataclasses for model structs (`RecognitionRequest`, `RecognitionResponse`, etc.)

### Error Handling
- Use specific exception types; wrap external calls in try/except
- Log via `logger = logging.getLogger(__name__)` with `%-formatting` (e.g., `logger.info("Task %s: ...", task_id)`)
- Celery tasks: `raise self.retry(exc=e)` for retries (max 3, 30s delay)
- Use `logger.exception()` for error-level logging with traceback
- Graceful degradation on external service failures
- Comments in Chinese are acceptable

## Architecture Patterns

- Import recognition engine services from `engine.services`:
  ```python
  from engine.services import YoloDetectionService, RecognitionRequest
  ```
- Config singleton: `from core.config import config`
- S3 singleton: `from core.s3.s3_client import s3`
- RabbitMQ singleton: `from core.mq.rabbitmq import RabbitMQConnection`
- Adding a new recognition service requires registration in two places inside `worker/src/tasks/recognize.py`:
  1. `SERVICE_MAP` — maps `RecognitionMethod` enum to service instance
  2. `DETECTION_TYPE_MAP` — maps integer API values (`1`–`4`) to `RecognitionMethod`

## API Routes

Routers are mounted in `api/src/api_server.py`:

| Prefix | Router | Endpoints |
|---|---|---|
| `/api/recognition` | `api/src/routes/recognition.py` | `POST /recognize`, `GET /result/{task_id}` |
| `/api/dict` | `api/src/routes/dict.py` | `GET /services`, `GET /models/yolo` |

- `/api/dict/services` returns the 4 recognition service types with IDs and descriptions
- `/api/dict/models/yolo` scans `models/yolo/{detection,segmentation}/` and returns available `.pt` stems

## Service Architecture

| Service | `detection_type` | Output |
|---|---|---|
| `YoloDetectionService` | Model name (e.g. `"安全帽"`) | COCO annotations + annotated image |
| `YoloSegmentationService` | Model name (e.g. `"龟裂"`) | COCO annotations with segmentation |
| `SamSegmentationService` | `"prompt"` or `"model\|prompt"` | Mask overlays |
| `MultimodalService` | `"prompt"` or `"model\|prompt"` | Qwen-VL via DashScope API |

- `detection_type` in the REST API accepts both integers (`1`–`4`) and strings (enum names like `"yolo_detection"`).
- For SAM and Multimodal, `text` supports a pipe-separated format `"model\|prompt"` to override the default model.

## Model File Locations

`.pt` model files are loaded from the `models/` directory at repo root:

| Service | Path |
|---|---|
| YOLO Detection | `models/yolo/detection/{model_name}.pt` |
| YOLO Segmentation | `models/yolo/segmentation/{model_name}.pt` |
| SAM | `models/sam/sam3.pt` (or similar) |

## Celery Task System

- **Broker:** RabbitMQ (`amqp://...` from `.env`)
- **Backend:** Redis (`redis://...` from `.env`)
- **Queue:** `tasks.image.disease_detection`
- **Result exchange:** `events.image.disease_detected` (fanout)
- **Entry:** `worker/src/worker_server.py`; Tasks: `worker/src/tasks/recognize.py`

The worker uses **two result channels**:
1. Celery result backend (Redis) — polled by `GET /result/{task_id}`
2. Pika direct publish to a RabbitMQ fanout exchange (`RESULT_EXCHANGE`) — consumed by downstream services

## Configuration

- Secrets in `.env` (gitignored) — **never commit**
- PyTorch sources: CUDA 12.6 index (auto-selected by platform)

## Pre-Commit Checklist

1. `uv run ruff check --fix .` — auto-fix lint issues
2. `uv run ruff format .` — format code
3. `uv run pytest` — ensure all tests pass
4. Never commit `.env` or secrets

## Known Issues

- `test_image_disease_worker.py` imports from deleted `app.messaging.handlers.image_disease_worker` (migrated to Celery)
- The `tests/` directory currently only contains `consume_result_queue.py`; previous test files (`test_recognition_services.py`, `test_e2e.py`, etc.) referenced in older docs are not present
