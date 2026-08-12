# AI 图片识别服务内部实现文档

## 服务组成

本项目当前拆成四个独立运行的进程:

| 服务 | 入口 | 作用 |
| --- | --- | --- |
| API 服务 | `api_server:app` | 接收外部 HTTP 请求，提交识别任务，写入任务记录 |
| GPU Worker | `worker_server_gpu.celery_app` | 串行消费 YOLO/SAM 队列，执行 GPU 推理 |
| 多模态 Worker | `worker_server_multimodal.celery_app` | 并发消费多模态队列，调用外部 API |
| Consumer | `result_consumer` | 消费识别结果，根据 `task_id` 找到回调地址并执行回调重试 |

Windows 下可用 `start.ps1` 同时启动这四个进程。

## 核心链路

```text
外部调用方
  -> POST /api/recognition/recognize
  -> API 入库 recognition_task_records(status=pending)
  -> API 根据 detection_type 选择 YOLO / SAM / multimodal 队列
  -> GPU Worker 串行执行 YOLO/SAM，或多模态 Worker 并发调用外部 API
  -> Worker 分批写入 recognition_image_results
  -> Worker 更新 recognition_task_records.result_payload
  -> API 通过分页接口查询任务和单图识别结果
```

## 关键配置

任务拓扑固定为三条 direct 队列：`tasks.image.recognition.yolo`（类型 1/2）、`tasks.image.recognition.sam`（类型 3）和 `tasks.image.recognition.multimodal`（类型 4）。GPU Worker 固定单并发，多模态 Worker 固定任务级线程并发 4；这些值不作为环境配置。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `RABBITMQ_RESULT_EXCHANGE` | `events.image.disease_detected` | Worker 发布识别结果的 fanout exchange |
| `RABBITMQ_RESULT_QUEUE` | `events.image.disease_detected` | Consumer 订阅的结果队列 |
| `RABBITMQ_RESULT_DLX` | `events.image.disease_detected.dlx` | 识别结果死信交换机 |
| `RABBITMQ_RESULT_DLQ` | `events.image.disease_detected.dlq` | 识别结果死信队列 |
| `RABBITMQ_RESULT_DLQ_ROUTING_KEY` | `events.image.disease_detected.dlq` | 识别结果进入死信队列时使用的 routing key |
| `CALLBACK_RETRY_INTERVAL_SECONDS` | `0` | 回调失败后的重试间隔 |
| `CALLBACK_RETRY_TIMEOUT_SECONDS` | `10` | 回调最多重试总时长 |
| `CALLBACK_REQUEST_TIMEOUT_SECONDS` | `10` | 单次回调 HTTP 请求超时时间 |
| `RESULT_DB_BATCH_SIZE` | `50` | Worker 检测结果每多少张图片批量写入一次数据库 |
| `MODELS_DIR` | `models` | 模型根目录；相对路径按服务启动工作目录解析 |
| `SAM_IMAGE_SIZE` | `1568` | SAM 推理输入边长；必须保持为模型 stride 14 的倍数 |
| `SAM_SEGMENTATION_EPSILON` | `4.0` | SAM 掩膜轮廓多边形近似误差（像素）；越大，返回点越少 |

注意：当前阶段 Worker 已暂停任务完成后的结果队列投递，Consumer 不会收到新的识别结果消息。结果队列和回调代码保留，后续需要回调时可重新打开 Worker 中的 `publish_result_queue` 开关。

## API 层

路由文件:

- `api/src/routes/recognition.py`

主要接口:

- `POST /api/recognition/recognize`: 提交任务，并把 `task_id`、原始任务参数写入数据库。
- `POST /api/recognition/recognize/yolo-detection`: 提交 YOLO 目标检测任务，并写入数据库。
- `POST /api/recognition/recognize/yolo-segmentation`: 提交 YOLO 实例分割任务，并写入数据库。
- `POST /api/recognition/recognize/sam-segmentation`: 提交 SAM 分割任务，并写入数据库。
- `POST /api/recognition/recognize/multimodal`: 提交多模态识别任务，并写入数据库。
- `GET /api/recognition/result/{task_id}`: 查询 Celery backend 中的任务状态。
- `GET /api/recognition/tasks`: 分页查询已入库任务，支持创建时间、状态、识别类型和项目名称筛选。
- `GET /api/recognition/tasks/results`: 分页查询单个任务的单图识别结果。

API 层只负责接收请求和返回响应，任务入库提交逻辑在:

- `api/src/recognition_submission.py`

### 内部分页查询单图识别记录

```http
GET /api/recognition/tasks/results
```

该接口用于中控平台分页查询某个任务已入库的单图识别记录。它会返回 `image_index`、原始图片 URL、服务类型、S3 Key、入库时间等内部字段。对外系统只需要 COCO 数据时，应使用 `GET /api/recognition/tasks/coco?task_id={task_id}`。

查询参数:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `task_id` | string | 是 | - | 任务 ID |
| `page` | integer | 否 | `1` | 当前页码，从 `1` 开始 |
| `pageSize` | integer | 否 | `10` | 每页数量，最大 `500` |

响应示例:

```json
{
  "page": 1,
  "pageSize": 10,
  "totalPages": 10,
  "total": 100,
  "items": [
    {
      "image_index": 0,
      "url": "https://example.com/image1.jpg",
      "service": "yolo_detection",
      "detection_type": "安全帽",
      "count": 2,
      "image_key": "ai-cmm/通用/安全帽/image/0e3316be-5394-4242-a18b-acacaa487b83.jpg",
      "coco_key": "ai-cmm/通用/安全帽/json/0e3316be-5394-4242-a18b-acacaa487b83.json",
      "images": [
        {
          "id": 1,
          "file_name": "0e3316be-5394-4242-a18b-acacaa487b83.jpg",
          "width": 957,
          "height": 534
        }
      ],
      "annotations": [
        {
          "id": 1,
          "image_id": 1,
          "category_id": 1,
          "bbox": [607.2, 3.36, 349.8, 380.06],
          "score": 0.9063,
          "segmentation": []
        },
        {
          "id": 2,
          "image_id": 1,
          "category_id": 2,
          "bbox": [67.43, 34.33, 202.73, 246.0],
          "score": 0.8784,
          "segmentation": []
        }
      ],
      "categories": [
        {
          "id": 1,
          "name": "佩戴安全帽",
          "supercategory": "安全帽"
        },
        {
          "id": 2,
          "name": "未佩戴安全帽",
          "supercategory": "安全帽"
        }
      ],
      "created_at": "2026-06-25T17:21:00+08:00"
    }
  ]
}
```

## 任务提交

核心任务提交方法:

- `core/src/core/mq/task_queue.py`
- `submit_recognition_task(payload: RecognitionTaskPayload)`

API 不直接 import worker task，而是通过 Celery 任务名投递:

```python
spec = get_task_queue_spec(payload.detection_type)
celery_app.send_task(
    spec.task_name,
    kwargs=payload.to_dict(),
    exchange=spec.exchange_name,
    queue=spec.queue_name,
    routing_key=spec.routing_key,
)
```

YOLO/SAM 使用任务名 `recognition.process_gpu`，多模态使用 `recognition.process_multimodal`。三条队列各自使用同名 direct exchange 和 routing key，并自动声明独立的 `.dlx`、`.dlq`。Worker 会校验消息 routing key 与 `detection_type`；错投消息不会占用错误的资源池，而是标记失败后进入来源队列的 DLQ。整体重试保持原 exchange、queue 和 routing key。

旧 `RABBITMQ_QUEUE_NAME` / `tasks.image.disease_detection` 不参与新任务投递或消费。部署切换不会迁移或删除旧队列中的遗留消息。

`RecognitionSubmitRequest` 和 `RecognitionRecordedSubmitRequest` 是 API 请求模型。

`RecognitionTaskPayload` 是提交给 worker 的核心任务模型。这样后续 API 增加回调、凭证等字段时，不会污染 worker 的任务参数。

## Worker 处理

任务文件和入口:

- `worker/src/tasks/gpu.py` / `worker_server_gpu.celery_app`
- `worker/src/tasks/multimodal.py` / `worker_server_multimodal.celery_app`

Worker 执行流程:

1. 入口校验 routing key 和 `detection_type` 是否属于当前资源池。
2. GPU Worker 按固定的 `solo + concurrency=1 + prefetch=1` 串行执行 YOLO/SAM；多模态 Worker 用固定 4 线程并发任务。
3. 下载图片并执行识别；每个多模态任务内部仍逐图串行。
4. 将模型响应序列化为单图结果结构。
5. 如果任务存在 `recognition_task_records` 记录，则按 `RESULT_DB_BATCH_SIZE` 分批写入 `recognition_image_results`。
6. 所有图片完成后更新 `recognition_task_records.result_payload` 为轻量汇总信息。
7. 当前暂停调用 `publish_result(result_summary)`，不发布轻量 `task_completed` 事件。
8. Celery backend 只保留任务进度，不保存完整识别结果。

GPU Worker 检查系统内存和 GPU 显存，并在任务结束后释放模型和 CUDA 缓存；多模态 Worker 不导入 GPU 推理栈，只检查系统内存。GPU Worker 只允许部署一个实例，当前没有跨进程 GPU 锁。

注意：结果队列发布逻辑仍保留在代码中，但当前被 `publish_result_queue = False` 关闭。

结果发布文件:

- `core/src/core/mq/result_bus.py`

发布时使用:

```python
json.dumps(payload, ensure_ascii=False).encode("utf-8")
```

这样 RabbitMQ 消息体和回调请求体都保留中文，不再显示为 `\uXXXX`。

## Consumer

入口:

- `consumer/src/result_consumer.py`

消费者内部服务:

- `consumer/src/recognition_result_handler.py`
- `consumer/src/callback_delivery.py`
- `core/src/core/storage/recognition_result_storage.py`

消费逻辑:

当前 Worker 不投递结果队列，以下逻辑是保留的回调消费链路，只有重新打开 `publish_result_queue` 后才会收到新消息。

1. 订阅 `config.RESULT_QUEUE`。
2. 收到 RabbitMQ 原始消息体 `body: bytes`。
3. 解码 JSON，读取 `task_id`。
4. 如果消息是 `event_type=task_completed`，根据 `task_id` 从数据库读取任务汇总和单图结果，重建回调 JSON。
5. 如果消息是旧格式完整结果，则兼容旧流程，先保存结果再回调。
6. 用结果 JSON 字符串 POST 到 `callback_url`。
7. HTTP `200` 只记录最后一次回调状态码。
8. 非 `200` 或请求异常则按间隔重试。
9. 超过 `CALLBACK_RETRY_TIMEOUT_SECONDS` 或 `CALLBACK_MAX_ATTEMPTS` 后记录回调错误，不改变任务状态，并将当前结果消息投递到结果死信队列。

保留回调流程下，MQ 只承载轻量完成事件，完整 COCO 结果从数据库重建后回调。

## 死信队列

识别任务队列和结果队列都声明了 dead-letter exchange。

- 识别任务：单张图片重试耗尽，或整任务 Celery 重试耗尽后，worker 使用 `Reject(requeue=False)`，消息进入 `RABBITMQ_TASK_DLQ`。
- 识别结果：结果消息格式错误、回调处理异常、回调最终放弃时，consumer 使用 `basic_nack(requeue=False)`，消息进入 `RABBITMQ_RESULT_DLQ`。

RabbitMQ 不允许给已存在队列直接追加 `x-dead-letter-exchange` 参数。首次部署该变更时，如果同名队列已存在，需要先删除旧队列或换一个新的队列名，再让服务重新声明队列。

## 数据库表

表名:

- `recognition_task_records`
- `recognition_image_results`
- `recognition_model_configs`
- `recognition_combinations`
- `recognition_combination_models`

字段:

| 字段 | 说明 |
| --- | --- |
| `id` | 自增主键 |
| `task_id` | Celery 任务 ID，唯一索引 |
| `status` | 任务状态 |
| `callback_url` | 外部回调地址；当前可为空字符串 |
| `request_payload` | 提交识别任务时的业务参数，JSONB |
| `result_payload` | Worker 写入的轻量识别汇总信息，JSONB |
| `callback_attempts` | 回调尝试次数 |
| `last_callback_status_code` | 最后一次回调 HTTP 状态码 |
| `last_callback_error` | 最后一次回调错误信息 |
| `callback_started_at` | 第一次开始回调时间 |
| `completed_at` | 识别结果入库完成时间 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### recognition_image_results

| 字段 | 说明 |
| --- | --- |
| `id` | 记录 ID |
| `task_id` | Celery 任务 ID，关联 `recognition_task_records.task_id` |
| `image_index` | 当前任务内的图片序号 |
| `source_url` | 原始图片 URL |
| `service` | 服务枚举，例如 `yolo_detection` |
| `detection_type` | 检测类型、模型名称或提示词 |
| `image_key` | 识别图片 S3 Key |
| `coco_key` | COCO 结果 JSON S3 Key |
| `annotation_count` | 当前图片识别结果数量 |
| `result_payload` | 单张图片 COCO 标注结果，JSONB，仅包含 `images`、`annotations`、`categories` |
| `created_at` | 创建时间 |

### recognition_model_configs

| 字段 | 说明 |
| --- | --- |
| `id` | 记录 ID |
| `uuid` | 对外模型或识别项 UUID；YOLO 模型文件名也使用该 UUID |
| `name` | 业务展示名称，可以重复 |
| `detection_type` | 识别类型：`1` YOLO 检测，`2` YOLO 分割，`3` SAM，`4` 多模态 |
| `prompt` | 提示词。SAM/多模态使用，YOLO 通常为空 |
| `model_file` | 模型文件名。远端多模态为空 |
| `storage_key` | 模型在 S3 或 MinIO 中的完整对象 Key。远端多模态为空 |
| `is_deleted` | 是否删除 |
| `project_name` | 项目名称 |
| `description` | 描述 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### 综合检测配置

`recognition_combinations` 保存可复用的综合检测配置，字段包括 `uuid`、`name`、`project_name`、`description`、`is_deleted` 和时间字段。`recognition_combination_models` 用 `combination_id`、`model_id` 关联模型配置，且同一组合不能重复关联同一模型；`sort_order` 保留调用方提交的模型顺序。

状态约定:

| status | 写入位置 | 说明 |
| --- | --- | --- |
| `pending` | API 服务 | 任务已提交并入库 |
| `processing` | Worker | Worker 已开始处理任务 |
| `success` | Worker | Worker 已完成任务，单图结果和任务汇总已入库 |
| `failed` | Worker | Worker 处理失败，保留已写入的部分单图结果用于排查 |

回调是否成功不再影响 `status`。回调失败只更新 `callback_attempts`、`last_callback_status_code`、`last_callback_error` 等回调字段。

## 数据库初始化和迁移

首次建表:

数据库迁移统一使用 Alembic:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run --managed-python --python 3.12 python -m alembic upgrade head
```

生成新的迁移文件:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run --managed-python --python 3.12 python -m alembic revision --autogenerate -m "message"
```

历史手写建表/迁移脚本只作为旧环境排查参考，新结构变更以 `alembic/versions` 为准。

初始化识别模型配置，并为 YOLO 模型复制 UUID 文件名副本:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run --managed-python --python 3.12 python scripts\seed_recognition_model_configs.py
```

## 模型管理接口

模型管理接口挂载在 `/api/models`，用于维护 `recognition_model_configs`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/models` | 新增模型配置 |
| `POST` | `/api/models/upload` | 上传模型文件到 S3/MinIO 并新增模型配置 |
| `GET` | `/api/models` | 分页查询模型配置 |
| `GET` | `/api/models/{uuid}` | 查询单个模型配置 |
| `PUT` | `/api/models/{uuid}` | 更新模型配置 |
| `DELETE` | `/api/models/{uuid}` | 删除模型配置 |

分页查询参数:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | integer | 否 | `1` | 当前页码 |
| `pageSize` | integer | 否 | `10` | 每页数量 |
| `detection_type` | integer | 否 | - | 识别类型过滤；不传查询全部 |
| `includeDeleted` | boolean | 否 | `false` | 是否包含已删除模型 |

已有模型文件在 S3/MinIO 时，直接使用 `POST /api/models` 或 `PUT /api/models/{uuid}`
登记 `model_file` 和 `storage_key`。

需要通过 API 上传模型文件时，使用 `POST /api/models/upload`，请求类型为
`multipart/form-data`:

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | file | 是 | 模型文件 |
| `name` | string | 是 | 展示名称 |
| `detection_type` | integer | 是 | 识别类型：`1` YOLO 检测，`2` YOLO 分割，`3` SAM，`4` 多模态 |
| `prompt` | string | 否 | SAM/多模态提示词 |
| `project_name` | string | 否 | 项目名称，默认 `通用` |
| `description` | string | 否 | 模型描述 |
| `storage_key` | string | 否 | 指定对象 Key；不传时按识别类型自动生成 |

这些脚本是一次性执行脚本，不应放到 API startup 中自动执行。

## 启动方式

Windows 一键启动:

```powershell
cd D:\project\ai\rabbitMQ_test
.\start.ps1
```

脚本会启动:

- FastAPI
- Celery Worker
- Consumer

日志文件:

- `logs/api.log`
- `logs/worker.log`
- `logs/consumer.log`

## 测试回调服务

测试回调接收服务:

- `tests/callback_server.py`

启动:

```powershell
cd D:\project\ai\rabbitMQ_test
$env:UV_CACHE_DIR='.uv-cache'
uv run --managed-python --python 3.12 python tests\callback_server.py
```

地址:

```text
http://127.0.0.1:9000/callback
```

该服务会打印收到的原始请求体，并返回 HTTP 200。

## 已知注意事项

Celery 日志中如果出现:

```text
Substantial drift ... Current drift is 28800 seconds
```

说明多个 Celery 节点的系统时间或时区差了 8 小时。立即任务通常还能执行，但 `retry`、`eta`、定时任务和监控事件可能异常。应统一所有 worker 所在机器或容器的系统时间和时区。

Worker 中不要手动执行:

```python
self.update_state(state="FAILURE", meta={...})
```

Celery 的 `FAILURE` 状态要求 result 是异常结构，普通 dict 会污染 backend，导致后续报 `Exception information must include the exception type`。
