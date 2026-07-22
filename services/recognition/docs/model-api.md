# 内部模型管理接口

## 基础信息

- 服务地址：`http://{host}:7987`
- 业务前缀：`/api/models`
- JSON 响应统一为 `{"code": number, "message": string, "data": any}`。

模型字段：

| 字段 | 说明 |
| --- | --- |
| `uuid` | 模型唯一标识 |
| `name` | 前端展示名称 |
| `detection_type` | 识别类型：`1` YOLO 检测、`2` YOLO 分割、`3` SAM、`4` 多模态 |
| `prompt` | SAM 或多模态提示词，可为空 |
| `model_file` | 缓存使用的模型文件名；远端多模态可为空 |
| `storage_key` | S3 对象 Key；远端多模态可为空 |
| `project_name` | 所属项目，默认 `通用` |
| `is_deleted` | 是否逻辑删除 |
| `description` | 模型说明 |

## 新增模型配置

```http
POST /api/models
Content-Type: application/json
```

适用于模型文件已由其他平台上传到 S3，只需要登记其配置与 `storage_key`。

```json
{
  "name": "安全帽检测模型",
  "detection_type": 1,
  "model_file": "628f211c-7183-4937-bf9f-91287931de91.pt",
  "storage_key": "平台/yolo/model/628f211c-7183-4937-bf9f-91287931de91.pt",
  "project_name": "通用",
  "description": "安全帽识别"
}
```

`uuid` 可选；不传时由服务生成。成功后 `data` 返回完整模型对象。

当 `detection_type` 为 `3`（SAM）时，服务会自动固定为共享模型文件 `sam3.pt` 和共享 S3 Key `平台/sam/model/sam3.pt`，请求中的 `model_file`、`storage_key` 不生效。

## 分页查询模型

```http
GET /api/models?page=1&pageSize=10&detection_type=1&includeDeleted=false
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码，从 `1` 开始，默认 `1` |
| `pageSize` | 否 | 每页数量，默认 `10` |
| `detection_type` | 否 | 按识别类型筛选 |
| `includeDeleted` | 否 | 是否包含已删除模型，默认 `false` |

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "page": 1,
    "pageSize": 10,
    "totalPages": 1,
    "total": 1,
    "items": [
      {
        "id": 1,
        "uuid": "628f211c-7183-4937-bf9f-91287931de91",
        "name": "安全帽检测模型",
        "detection_type": 1,
        "prompt": null,
        "model_file": "628f211c-7183-4937-bf9f-91287931de91.pt",
        "storage_key": "平台/yolo/model/628f211c-7183-4937-bf9f-91287931de91.pt",
        "project_name": "通用",
        "is_deleted": false,
        "description": "安全帽识别",
        "created_at": "2026-07-10T10:00:00+08:00",
        "updated_at": "2026-07-10T10:00:00+08:00"
      }
    ]
  }
}
```

## 查询单个模型

```http
GET /api/models/{model_uuid}
```

成功时 `data` 为完整模型对象，字段同分页查询中的 `items` 元素。

## 修改模型

```http
PUT /api/models/{model_uuid}
Content-Type: application/json
```

请求体中的字段均可选，仅更新传入字段：

```json
{
  "name": "安全帽检测模型 V2",
  "storage_key": "平台/yolo/model/helmet-v2.pt",
  "description": "替换为新版模型"
}
```

成功时 `data` 返回更新后的完整模型对象。

## 删除模型

```http
DELETE /api/models/{model_uuid}
```

这是逻辑删除，不会删除 S3 中的模型文件。

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted": true,
    "uuid": "628f211c-7183-4937-bf9f-91287931de91"
  }
}
```

## 上传模型文件并创建配置

```http
POST /api/models/upload
Content-Type: multipart/form-data
```

| 表单字段 | 必填 | 说明 |
| --- | --- | --- |
| `file` | 是 | 模型文件 |
| `name` | 是 | 前端展示名称 |
| `detection_type` | 是 | 识别类型 |
| `prompt` | 否 | SAM 或多模态提示词 |
| `project_name` | 否 | 默认 `通用` |
| `description` | 否 | 模型说明 |
| `storage_key` | 否 | 指定 S3 Key；不传则服务按识别类型生成 |

成功后，服务会上传文件到 S3、创建模型记录，并在 `data` 返回完整模型对象。

上传 SAM 文件时也固定上传到 `平台/sam/model/sam3.pt`，用于覆盖唯一共享的 SAM3 模型；不会生成 UUID 文件副本。
