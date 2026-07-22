# AI Image Recognition API

基于 Celery + RabbitMQ 的异步图像识别服务，集成 YOLO 检测/分割、SAM 分割、多模态识别四种识别方式。

## 项目架构

```
rabbitMQ_test/
├── api/src/                                   # FastAPI 入口、路由、API 私有服务
├── worker/src/                                # Celery worker 入口和识别任务
├── consumer/src/                              # 结果消费和回调交付
├── core/src/core/                             # 配置、数据库、MQ、共享 schema、结果存储
├── engine/src/engine/                         # YOLO/SAM/多模态识别引擎
├── models/
│   ├── yolo/detection/                        # .pt 检测模型
│   ├── yolo/segmentation/                     # .pt 分割模型
│   └── sam/                                   # sam3.pt
├── tests/
│   └── consume_result_queue.py                # 结果队列手工测试脚本
├── pyproject.toml
├── .env                                       # 环境变量 (不提交)
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

编辑 `.env` 文件：

```env
RABBITMQ_HOST=172.16.0.72
RABBITMQ_USER=admin
RABBITMQ_PASS=password
RABBITMQ_QUEUE_NAME=tasks.image.disease_detection

S3_ENDPOINT=http://172.16.0.110:9000
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 启动服务

```bash
# FastAPI API 服务
PYTHONPATH=api/src:worker/src:consumer/src:core/src:engine/src \
uv run uvicorn api_server:app --host 0.0.0.0 --port 7987

# Celery Worker
PYTHONPATH=api/src:worker/src:consumer/src:core/src:engine/src \
uv run celery -A worker_server.celery_app worker --loglevel=info --pool=solo
```

## REST API

### 提交识别任务

```http
POST /api/recognition/recognize
Content-Type: application/json

{
  "task_id": "task_001",
  "detection_type": 1,
  "text": "安全帽",
  "image_urls": ["https://example.com/image.jpg"],
  "confidence": 0.5
}
```

#### 参数说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 否 | 任务标识符，用于链路追踪 |
| `detection_type` | int/string | **是** | 识别类型 (见下方枚举) |
| `text` | string | 条件必填 | YOLO 填模型名称；SAM/多模态填提示词 |
| `image_urls` | list[string] | **是** | 图片 HTTP URL 列表 |
| `confidence` | float | 否 | 置信度阈值，默认 `0.5`，仅 YOLO 有效 |

#### 识别类型枚举 (`detection_type`)

| 值 | 枚举名 | 对应服务 | `text` 填写 | 说明 |
|----|--------|----------|-------------|------|
| `1` | `YOLO_DETECTION` | YoloDetectionService | 模型名称 | YOLO 目标检测 |
| `2` | `YOLO_SEGMENTATION` | YoloSegmentationService | 模型名称 | YOLO 实例分割 |
| `3` | `SAM_SEGMENTATION` | SamSegmentationService | 提示词 | SAM 语义分割 (mask 遮罩) |
| `4` | `MULTIMODAL` | MultimodalService | 提示词 | Qwen-VL 多模态识别 |

> `detection_type` 支持整数或字符串 (如 `"yolo_detection"`)。

### `text` 字段填写指南

| 服务类型 | 填写内容 | 示例 |
|----------|----------|------|
| YOLO | `.pt` 模型名称 (不含后缀) | `"安全帽"` |
| SAM | 提示词，多个用逗号分隔 | `"安全帽,人"` |
| 多模态 | 提示词/问题 | `"描述图片中的安全帽"` |
| SAM/多模态 (指定模型) | `模型名|提示词` | `"sam3|安全帽"` |

### 查询任务结果

```http
GET /api/recognition/result/{task_id}
```

## 返回结果

### 成功响应

```json
{
  "task_id": "task_001",
  "status": "success",
  "result": {
    "task_id": "task_001",
    "detection_type": "yolo_detection",
    "text": "安全帽",
    "image_count": 1,
    "results": [
      {
        "service": "yolo_detection",
        "detection_type": "安全帽",
        "count": 2,
        "images": [
          {
            "id": 1,
            "file_name": "uuid.jpg",
            "width": 640,
            "height": 480
          }
        ],
        "annotations": [
          {
            "id": 1,
            "image_id": 1,
            "category_id": 1,
            "bbox": [100.0, 200.0, 150.0, 300.0],
            "area": 45000.0,
            "score": 0.95,
            "segmentation": []
          }
        ],
        "categories": [
          {
            "id": 1,
            "name": "person",
            "supercategory": "安全帽"
          }
        ]
      }
    ]
  }
}
```

### 返回字段说明

| 字段 | 说明 |
|------|------|
| `images[].file_name` | 文件名 (与 S3 中的图片名一致) |
| `annotations[].bbox` | `[x, y, width, height]` 格式 |
| `annotations[].segmentation` | 多边形坐标 (分割服务有值，检测服务为空数组) |
| `categories[].supercategory` | 父类别名称 |

### S3 存储结构

所有文件上传至 `ai-cmm` 桶，文件夹名称规则：

| 服务 | 文件夹名称 | 示例 |
|------|------------|------|
| YOLO 检测 | 模型名称 | `ai-cmm/安全帽/xxx.jpg` |
| YOLO 分割 | 模型名称 | `ai-cmm/龟裂/xxx.jpg` |
| SAM 分割 | 提示词 | `ai-cmm/安全帽/xxx.jpg` |
| 多模态 | 提示词 | `ai-cmm/描述图片/xxx.jpg` |


## 测试

```bash
# E2E 集成测试 (需 Worker 已启动)
uv run python tests/test_e2e.py

# 单元测试
uv run pytest tests/ -v

# 单个测试文件
uv run pytest tests/test_recognition_services.py -v
```

## 依赖

| 依赖 | 说明 |
|------|------|
| PyTorch (CUDA 12.6) | GPU 推理加速 |
| Ultralytics (YOLOv8) | 目标检测/分割 |
| SAM3 | 语义分割 |
| Qwen-VL | 多模态识别 (DashScope API) |
| boto3 | S3 客户端 |
| RabbitMQ + Celery | 异步任务队列 |
