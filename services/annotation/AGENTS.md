# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

FastAPI-based AI image annotation service with COCO format support, YOLO training integration, SAM3 interactive segmentation (WebSocket), PostgreSQL persistence, and S3 (MinIO/RustFS) storage.

## Tech Stack

- **Python 3.12** managed by `uv` (not pip/conda)
- **FastAPI** + uvicorn on port 8811
- **Pydantic** for API request/response validation
- **dataclasses** for domain models; `CocoAnnotation`/`CocoDataset` use plain `__init__`
- **SQLAlchemy** (legacy `Column()` style, not `Mapped[]`) + PostgreSQL via psycopg2-binary
- **JSONB** columns for COCO annotation data storage
- **torch** (CUDA 12.6, from pytorch-cu126 index) + **ultralytics** for YOLO training via subprocess CLI
- **boto3** for S3/RustFS storage, **PIL/Pillow** for images, **SAM3** via WebSocket

## Commands

### Dependency Management
```bash
uv sync                          # Install all dependencies
uv add <package>                 # Add a new dependency
uv add --dev <package>           # Add a dev dependency
```

### Running the Server
```bash
uv run python run.py             # Development (port 8811, reload enabled)
./start.sh                       # Alternative development (uv run, debug logs, reload)
./start_bg.sh                    # Background production (nohup, logs/uvicorn.log)
./stop_bg.sh                     # Stop background server (SIGTERM then SIGKILL)
uv run python init_db.py         # Create database tables + column comments (first-time setup)
```

### Testing
No formal test framework configured. To add pytest:
```bash
uv add --dev pytest pytest-asyncio httpx
uv run pytest                              # Run all tests
uv run pytest tests/test_foo.py            # Run a single test file
uv run pytest tests/test_foo.py::test_bar  # Run a single test function
uv run pytest -k test_name                 # Run tests matching a keyword
uv run pytest -x                           # Stop on first failure
uv run pytest -v                           # Verbose output
```
Manual testing: `test/` contains Jupyter notebooks for SAM interaction.

### Linting / Formatting
No linter/formatter configured. If adding, prefer ruff:
```bash
uv add --dev ruff
uv run ruff check .                        # Check all files
uv run ruff check --fix .                  # Check and fix issues
uv run ruff format .                       # Format all files
uv run ruff check app/api/foo.py           # Check a single file
```

## High-Level Architecture

### Data Flow: Tasks -> Images -> COCO Annotations

A `Task` is a labeling project with categories. Images are uploaded to a task, stored in S3/RustFS, and referenced in PostgreSQL via `ImageModel`. Each image's COCO annotations (categories, image metadata, bounding boxes, segmentations) are stored as a single JSONB blob in `ImageModel.annotation_jsonb`. The `CocoDataset` domain model handles serialization/deserialization of this JSONB structure.

### YOLO Training Pipeline

`TrainTaskService.start_training()` orchestrates the full flow:
1. `YoloDatasetBuilder.build(task_name)` queries the DB for annotated images, downloads them from S3, converts COCO annotations to YOLO format (bbox or segmentation), splits 80/20 train/val, and writes `data.yaml`.
2. `TrainTaskService` spawns `subprocess.Popen(["yolo", "train", ...])` using the ultralytics CLI (not Python API).
3. A background thread watches stdout, parses `current/total` epoch progress via regex, writes to a log file, and updates `InMemoryTaskRepo` — an in-memory dict store (not persisted to DB) that tracks PID, status, progress, and errors.
4. The `train_task` API endpoints query `InMemoryTaskRepo` for live status.

### SAM3 Interactive Segmentation

The SAM3 model is preloaded at app startup in `main.py` via `SAM3Registry().load_model()`. The WebSocket endpoint `/ws/sam3` (no `/api` prefix) manages per-image sessions:
- `SAM3Service` holds `SAM3Session` instances keyed by `s3_key`
- Each session downloads the image from S3, runs `SAM.predict()` with user-provided points/labels, and returns mask contours simplified with Douglas-Peucker via OpenCV
- Blocking calls (`create_session`, `add_point`) are wrapped in `asyncio.to_thread()`

## Project Structure

```
app/
  api/                    # Route handlers (annotation, image, tasks, train_task, sam3, health)
  core/                   # Infrastructure (config.py, s3/s3_client.py, sam3/sam3_service.py + sam3_registry.py)
  db/                     # SQLAlchemy engine, SessionLocal, Base, get_db (database.py)
  models/                 # Data models (annotation, api_response, image, task, train_task)
  schemas/                # Pydantic request schemas (annotation, task, train_task)
  services/               # Business logic (image_store, task_store, YOLO/)
    YOLO/                 # YOLO training (train_task_service, InMemoryTaskRepo, yolo_dataset_builder)
  crud/                   # Empty placeholder dir (unused)
  main.py                 # FastAPI app factory, logging, CORS, request-timing middleware
run.py                    # Uvicorn dev entry point
init_db.py                # Database schema creation + Chinese column/table comments
storage/                  # Runtime data directory (gitignored)
test/                     # Manual test notebooks (SAM interaction)
```

## Code Style Guidelines

### Imports & Formatting
- Group: stdlib -> third-party -> local, separated by blank lines
- Use explicit absolute imports with `app.` prefix: `from app.models.api_response import ApiResponse`
- Never use `import *`; avoid duplicate imports
- 4-space indentation, no tabs, max line length ~100 chars
- Type hints on all function signatures and class attributes
- Trailing commas in multi-line lists/args

### Naming Conventions
- **Classes**: PascalCase (`TaskStore`, `CocoDataset`, `ApiResponse`)
- **Functions/Methods**: snake_case (`save_dataset`, `get_by_task_id`)
- **Private helpers**: `_` prefix (`_compute_area`, `_ensure`)
- **Variables**: snake_case (`task_id`, `image_name`)
- **Constants**: UPPER_SNAKE_CASE (`S3_BUCKET`, `TRAIN_DATA_DIR`)
- **Module singletons**: snake_case (`task_store = TaskStore()`, `router = APIRouter(...)`)
- **Pydantic request models**: PascalCase ending with `Request` (`TaskCreateRequest`)
- **SQLAlchemy ORM models**: PascalCase ending with `Model` (`TaskModel`, `CategoryModel`)
- **Serialization**: `to_dict`/`from_dict` or `to_coco_dict`/`from_coco_dict` pairs

### Types
- `@dataclass` for domain models with `to_dict()`/`from_dict()` serialization
- `pydantic.BaseModel` for API validation schemas
- `Generic[T]` + `TypeVar('T')` for typed response wrapper (`ApiResponse[T]`)
- Prefer `Optional[T]` over `T | None`; prefer `List/Dict` from `typing` over builtin
- `field(default_factory=list)` for mutable default dataclass fields
- Pydantic `Field()` for validation: `epochs: int = Field(default=100, ge=1)`
- Pydantic `Config` inner class: `extra = "forbid"` to reject unexpected fields

### SQLAlchemy Models
- Legacy `Column()` style (not `Mapped[]`/`mapped_column()`)
- Add `comment=` on every column (Chinese descriptions)
- `__table_args__ = {"comment": "表描述"}` for table-level comments
- `relationship()` with string forward refs: `"CategoryModel"`
- `cascade="all, delete-orphan"` and `ondelete="CASCADE"` on ForeignKey
- Every ORM model has `to_dict()` for manual serialization
- Lambda defaults for datetime: `default=lambda: datetime.now(timezone.utc)`
- JSONB columns for annotation data (PostgreSQL-specific)

### Error Handling & API Response Pattern
All endpoints return `ApiResponse` dataclass (not Pydantic):
```python
ApiResponse.success_response(data=..., message="成功")
ApiResponse.error_response(message="...", code=400)
```
Default success message is Chinese: `"成功"`. Always use `message=` kwarg explicitly.
- `HTTPException` for HTTP-level errors in API layer
- `ApiResponse.error_response()` for business-level errors in services
- Wrap service logic in `try/except` returning `ApiResponse` on failure
- Use `logging.getLogger(__name__)`; never `print()` in production code
- Status codes: 404 (not found), 409 (conflict/duplicate), 500 (server error)

### SQLAlchemy Session Pattern (Manual, not DI)
Services create sessions manually - follow existing pattern:
```python
db: Session = SessionLocal()
try:
    db.commit()
    return ApiResponse.success_response(...)
except Exception as e:
    db.rollback()
    return ApiResponse.error_response(message=f"...: {str(e)}", code=500)
finally:
    db.close()
```
`Depends(get_db)` exists but is unused. Do not introduce DI without discussion.

### Router & Service Organization
- Module-level instantiation: `task_store = TaskStore()`, `router = APIRouter(prefix="/tasks", tags=["Tasks"])`
- Routers registered in `main.py` with `/api` prefix (except SAM3 WebSocket at root `/ws/sam3`)
- CRUD sections separated by comment dividers: `# ------------------------ # Create`
- Store classes handle CRUD per domain (`TaskStore`, `ImageStore`)
- `S3Client` uses `__new__` singleton pattern

### Config & Logging
- `app/core/config.py` — `Settings` class from `.env` via `os.getenv()` (preferred for new code)
- Logging setup in `main.py`: `RotatingFileHandler` (`app.log`, 10MB, 5 backups) + `StreamHandler(stdout)`
- Format: `[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s`
- Request middleware logs: method, path, status, cost in ms
- Get logger via `logging.getLogger(__name__)`

### Docstrings & Comments
- API endpoint docstrings: Chinese
- Inline comments: Chinese
- Section dividers: `# ------------------------`

## SAM3 WebSocket Protocol

Endpoint: `/ws/sam3` (no `/api` prefix). All responses include `status` field.

**Status flow**: `loading` -> `ready` -> `predicting` -> `predicted` -> (loop) / `error`

- **init**: `{"action":"init","s3_key":"..."}` — loads image, responds `loading` then `ready`
- **point**: `{"action":"point","x":100,"y":200,"label":1}` — label 1=前景/0=背景, responds `predicting` then `predicted` with masks
- **reset**: `{"action":"reset"}` — resets interaction points, responds `ready`

`create_session` and `add_point` are blocking calls wrapped with `asyncio.to_thread()` to avoid blocking the WebSocket coroutine. Status messages are sent before blocking work begins.

## Key Inconsistencies (Do Not Replicate)

- `ApiResponse.success_response("训练任务创建成功")` passes string as `data` — use `message=` kwarg
- `s3_client.py` uses `print()` for init log — use `logger`
- `InMemoryTaskRepo.py` uses PascalCase filename — use snake_case
- `CocoAnnotation` uses plain class `__init__` instead of `@dataclass`
- Mixed `Optional[T]` vs `T | None` and `List[T]` vs `list[T]` — prefer `typing` module forms
- `CocoAnnotationSchema` in schemas doesn't follow `Request` suffix convention

## Environment

- `.env` required for PostgreSQL/S3 config (see `app/core/config.py` for vars)
- Port 8811, host 0.0.0.0, reload enabled in dev run modes
- No `.cursorrules` or `.github/copilot-instructions.md` found
- No linter/formatter/type-checker configured
