# 内部识别任务接口

本文件仅面向内部中控、运维和管理前端。接口可查看任务、图片序号、服务类型及 S3 存储 Key 等内部字段，不应提供给项目调用方。

## 基础信息

- 服务地址：`http://{host}:7987`
- 业务前缀：`/api/recognition`
- JSON 响应统一为 `{"code": number, "message": string, "data": any}`。

识别类型：`1` YOLO 目标检测、`2` YOLO 实例分割、`3` SAM 分割、`4` 多模态识别。

## 提交异步识别任务

```http
POST /api/recognition/recognize
Content-Type: application/json
```

```json
{
  "detection_type": 1,
  "text": "安全帽",
  "images": ["https://example.com/image1.jpg"],
  "project_name": "通用"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `detection_type` | integer | 是 | 识别类型，取值 `1` 至 `4` |
| `text` | string | 否 | YOLO 为模型名称；SAM、多模态为提示词 |
| `images` | string[] | 是 | 图片 URL 列表 |
| `project_name` | string | 否 | 项目名称，默认 `通用` |

成功时 `data` 返回 `{ "task_id": "...", "status": "pending" }`。

### 固定类型提交

以下接口请求体均为上方结构去掉 `detection_type` 后的内容：

| 接口 | 固定类型 |
| --- | --- |
| `POST /api/recognition/recognize/yolo-detection` | `1` |
| `POST /api/recognition/recognize/yolo-segmentation` | `2` |
| `POST /api/recognition/recognize/sam-segmentation` | `3` |
| `POST /api/recognition/recognize/multimodal` | `4` |

## 分页查询识别任务

```http
GET /api/recognition/tasks?page=1&pageSize=10&status=success&detectionType=3&projectName=路面
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码，从 `1` 开始，默认 `1` |
| `pageSize` | 否 | 每页数量，默认 `10` |
| `status` | 否 | `pending`、`processing`、`success` 或 `failed` |
| `createdAtStart` | 否 | 创建时间起点，ISO 8601，例如 `2026-07-01T00:00:00+08:00` |
| `createdAtEnd` | 否 | 创建时间终点，ISO 8601，例如 `2026-07-14T23:59:59+08:00` |
| `detectionType` | 否 | 识别类型：`1` YOLO 检测、`2` YOLO 分割、`3` SAM、`4` 多模态 |
| `projectName` | 否 | 项目名称模糊查询，不区分大小写 |

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "page": 1,
    "pageSize": 10,
    "totalPages": 3,
    "total": 24,
    "items": [
      {
        "task_id": "31ac1f77-11c5-486f-859e-dbff26bc3a27",
        "status": "success",
        "detection_type": 1,
        "text": "安全帽",
        "project_name": "通用",
        "image_count": 100,
        "completed_at": "2026-06-25T17:21:00+08:00",
        "created_at": "2026-06-25T17:18:00+08:00",
        "updated_at": "2026-06-25T17:21:00+08:00"
      }
    ]
  }
}
```

## 分页查询单任务完整结果

```http
GET /api/recognition/tasks/results?task_id={task_id}&page=1&pageSize=10
```

这是内部结果查询接口。它返回图片序号、服务、S3 Key、入库时间和完整 COCO 结果；项目调用方不应使用此接口。

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `task_id` | 是 | 任务 ID |
| `page` | 否 | 页码，从 `1` 开始，默认 `1` |
| `pageSize` | 否 | 每页数量，默认 `10` |

```json
{
  "code": 200,
  "message": "success",
  "data": {
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
        "image_key": "通用/安全帽/image/0e3316be.jpg",
        "coco_key": "通用/安全帽/json/0e3316be.json",
        "images": [
          {"id": 1, "file_name": "0e3316be.jpg", "width": 957, "height": 534}
        ],
        "annotations": [
          {
            "id": 1,
            "image_id": 1,
            "category_id": 1,
            "bbox": [607.2, 3.36, 349.8, 380.06],
            "score": 0.9063,
            "segmentation": []
          }
        ],
        "categories": [
          {"id": 1, "name": "佩戴安全帽", "supercategory": "安全帽"}
        ],
        "created_at": "2026-06-25T17:21:00+08:00"
      }
    ]
  }
}
```

`bbox` 是 `[x, y, width, height]`；`score` 为 `0` 至 `1` 的置信度；`segmentation` 为多边形数组，内层使用扁平坐标 `[x1, y1, x2, y2, ...]`。

## 直接识别单张图片

### 按模型 UUID 识别

```http
POST /api/recognition/recognize/direct
Content-Type: multipart/form-data
```

该接口根据模型表配置自动选择 YOLO、SAM 或多模态服务。它不创建任务、不进入 MQ、不写入任务和任务结果表；一次仅支持上传一张图片。

YOLO 和 SAM 的模型文件会先检查共享本地缓存；缓存缺失时，服务会按模型表 `storage_key` 从 S3 下载。下载失败时返回 `503`，不会开始识别。

按模型 UUID 调用 SAM 时，模型表 `name` 会写入 COCO 的 `categories[].name` 和 `categories[].supercategory`；模型表 `prompt` 只用于 SAM 推理。

| 表单字段 | 必填 | 说明 |
| --- | --- | --- |
| `model_uuid` | 是 | 模型表中的 UUID |
| `file` | 是 | 待识别图片 |
| `confidence` | 否 | 置信度，默认 `0.5` |

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "model": {
      "uuid": "628f211c-7183-4937-bf9f-91287931de91",
      "name": "安全帽检测模型",
      "detection_type": 1
    },
    "result": {
      "service": "yolo_detection",
      "detection_type": "628f211c-7183-4937-bf9f-91287931de91",
      "count": 1,
      "url": "image.jpg",
      "images": [],
      "annotations": [],
      "categories": []
    }
  }
}
```

### 旧固定类型接口

以下接口保留兼容，仅供内部调试使用；新接入优先使用上方按模型 UUID 识别的接口。

| 接口 | 固定类型 |
| --- | --- |
| `POST /api/recognition/recognize/direct/yolo-detection` | YOLO 目标检测 |
| `POST /api/recognition/recognize/direct/yolo-segmentation` | YOLO 实例分割 |
| `POST /api/recognition/recognize/direct/sam-segmentation` | SAM 分割 |
| `POST /api/recognition/recognize/direct/multimodal` | 多模态识别 |

表单字段：`file`（必填）、`text`（必填）、`project_name`（可选，默认 `通用`）、`confidence`（可选，默认 `0.5`）。

## 内部字典接口

```http
GET /api/dict/services
GET /api/dict/models/yolo
```

前者返回识别类型字典；后者扫描本地模型目录并返回 YOLO 检测与分割模型名称。
