# Project 对外图片识别接口文档

## 基础信息

- Base URL: `http://{host}:7987`
- Swagger UI: `http://{host}:7987/docs`
- 请求和响应编码: `UTF-8`
- 请求格式: `application/json`
- 响应格式: `{"code": number, "message": string, "data": any}`

本文件只提供给 Project 调用方。返回 COCO 标准数据的分页接口不会暴露 `image_index`、服务名称、S3 Key、入库时间等内部字段。

## 标准响应结构

所有业务接口统一返回以下结构:

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

成功时 `code` 为 HTTP 成功状态码，通常是 `200`，业务数据放在 `data`。失败时 `code` 为 HTTP 错误状态码，`message` 为错误原因，`data` 为 `null`。

## 查询任务组合

```http
GET /api/project/combination?uuid={combination_uuid}
```

该接口查询一个综合检测配置及其模型子任务。返回的 `model_uuid` 可直接用于创建 Project 识别任务，不返回模型文件、S3 Key、提示词等内部信息。

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "combination": {
      "uuid": "7985d2f7-e7f1-4b69-a827-0d8114d654fc",
      "name": "路面病害",
      "project_name": "通用",
      "description": "路面常见病害综合检测"
    },
    "sub_tasks": [
      {
        "model_uuid": "628f211c-7183-4937-bf9f-91287931de91",
        "model_name": "裂缝分割模型",
        "detection_type": 3,
        "description": "用于识别路面裂缝"
      },
      {
        "model_uuid": "b0e88be1-1c5e-4b64-a311-796d468d7afb",
        "model_name": "坑槽识别模型",
        "detection_type": 4,
        "description": "用于识别路面坑槽"
      }
    ]
  }
}
```

## 创建 Project 识别任务

```http
POST /api/project/recognize
```

该接口面向 Project 业务使用。调用方传入模型表 UUID 列表，服务会先校验所有模型均存在、未删除且配置完整，再为每个模型创建一个异步识别子任务；不会等待模型识别完成。

YOLO 和 SAM 模型会在创建任何子任务前检查共享本地缓存。缓存不存在时服务会依据模型表 `storage_key` 从 S3 下载；任意模型下载失败均返回 `503`，不会向 MQ 投递子任务。

该接口只返回模型与 `sub_task_id` 的对应关系，不返回任务状态或 `progress`。调用方需要查看进度时，使用返回的单个 `sub_task_id` 调用单任务状态查询接口。

### 请求字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `model_ids` | string[] | 是 | - | 模型表 UUID 列表；每个模型创建一个子任务，不能重复 |
| `images` | string[] | 是 | - | 图片 URL 列表 |
| `project_name` | string | 否 | `通用` | 项目名称 |

### 请求体

```json
{
  "model_ids": [
    "628f211c-7183-4937-bf9f-91287931de91",
    "sam3-model-uuid"
  ],
  "images": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ],
  "project_name": "通用"
}
```

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "model_uuid": "628f211c-7183-4937-bf9f-91287931de91",
        "model_name": "安全帽检测模型",
        "sub_task_id": "31ac1f77-11c5-486f-859e-dbff26bc3a27"
      },
      {
        "model_uuid": "sam3-model-uuid",
        "model_name": "SAM 裂缝分割模型",
        "sub_task_id": "701bf987-7db2-4590-aebc-37050b68a523"
      }
    ]
  }
}
```

### 失败响应

`images` 为空时返回:

```json
{
  "code": 400,
  "message": "图片列表不能为空",
  "data": null
}
```

## 查询单任务状态

```http
GET /api/recognition/result?task_id={task_id}
```

该接口用于查询单个异步识别任务的当前状态，不提供 Project 下多个任务的聚合进度。

### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `task_id` | string | 是 | - | 任务 ID |

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "31ac1f77-11c5-486f-859e-dbff26bc3a27",
    "status": "processing",
    "progress": {
      "processed": 1,
      "total": 2,
      "percent": 50
    }
  }
}
```

### 状态说明

| status | 说明 |
| --- | --- |
| `pending` | 任务已提交，等待处理 |
| `processing` | 正在识别 |
| `success` | 识别任务已完成 |
| `failed` | 识别任务失败 |

## 分页查询任务列表

```http
GET /api/recognition/tasks
```

该接口用于分页查询已提交的识别任务。接口只查询数据库，不进入 RabbitMQ。

### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | integer | 否 | `1` | 当前页码，从 `1` 开始 |
| `pageSize` | integer | 否 | `10` | 每页数量 |
| `status` | string | 否 | - | 按任务状态过滤，例如 `pending`、`processing`、`success`、`failed` |
| `createdAtStart` | string | 否 | - | 创建时间起点，ISO 8601，例如 `2026-07-01T00:00:00+08:00` |
| `createdAtEnd` | string | 否 | - | 创建时间终点，ISO 8601，例如 `2026-07-14T23:59:59+08:00` |
| `detectionType` | integer | 否 | - | 按识别类型精确过滤：`1` YOLO 检测、`2` YOLO 分割、`3` SAM、`4` 多模态 |
| `projectName` | string | 否 | - | 按项目名称模糊查询，不区分大小写 |

### 响应示例

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
        "detection_type": 4,
        "text": "穿着绿色反光衣的人",
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

## 分页查询任务 COCO 结果

```http
GET /api/recognition/tasks/coco
```

该接口用于分页查询某个任务已入库的识别结果。每个 `item[]` 元素对应一张图片结果，返回原始图片 `url` 和该图片的 `images`、`annotations`、`categories`，不会返回 S3 Key 或入库时间。

### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `task_id` | string | 是 | - | 任务 ID |
| `page` | integer | 否 | `1` | 当前页码，从 `1` 开始 |
| `pageSize` | integer | 否 | `10` | 每页数量 |

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "page": 1,
    "pageSize": 10,
    "totalPages": 10,
    "total": 100,
    "item": [
      {
        "url": "https://example.com/image1.jpg",
        "images": [
          {
            "id": 1,
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
          }
        ],
        "categories": [
          {
            "id": 1,
            "name": "穿着绿色反光衣的人",
            "supercategory": "穿着绿色反光衣的人"
          }
        ]
      },
      {
        "url": "https://example.com/image2.jpg",
        "images": [
          {
            "id": 1,
            "width": 1280,
            "height": 720
          }
        ],
        "annotations": [
          {
            "id": 1,
            "image_id": 1,
            "category_id": 1,
            "bbox": [67.43, 34.33, 202.73, 246.0],
            "score": 0.8784,
            "segmentation": [
              [
                70.0,
                36.0,
                250.0,
                38.0,
                268.0,
                260.0,
                66.0,
                278.0
              ]
            ]
          }
        ],
        "categories": [
          {
            "id": 1,
            "name": "crack",
            "supercategory": "sam"
          }
        ]
      }
    ]
  }
}
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `page` | integer | 当前页码 |
| `pageSize` | integer | 每页数量 |
| `totalPages` | integer | 总页数 |
| `total` | integer | 当前任务已入库的单图结果总数 |
| `item` | array | 当前页的单图 COCO 结果数组 |

## 单图 COCO 结构

每个 `item[]` 元素是一张图片的一份 COCO 结果。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `url` | string | 原始图片 URL |
| `images` | array | 图片元信息 |
| `annotations` | array | 检测框或分割结果 |
| `categories` | array | 类别信息 |

`annotations[]` 字段:

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 标注 ID |
| `image_id` | integer | 图片 ID |
| `category_id` | integer | 类别 ID |
| `bbox` | number[] | `[x, y, width, height]` |
| `score` | number | 置信度，范围 `0-1` |
| `segmentation` | number[][] | 分割多边形坐标。外层数组表示多个多边形，内层数组为一条多边形的扁平坐标序列 `[x1, y1, x2, y2, ...]`；目标检测和多模态识别通常为空数组 |
