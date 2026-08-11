# 内部综合检测配置接口

## 基础信息

- 服务地址：`http://{host}:7987`
- 业务前缀：`/api/combinations`
- JSON 响应统一为 `{"code": number, "message": string, "data": any}`。

综合检测配置是一组可复用的模型组合。例如“路面病害”可组合裂缝、坑洞和路面抛洒物三个模型。一个组合可包含多个模型，一个模型也可以被多个组合复用。

当前接口只维护组合配置，不会提交或执行识别任务。

## 创建综合检测配置

```http
POST /api/combinations
Content-Type: application/json
```

```json
{
  "name": "路面病害",
  "model_uuids": [
    "裂缝模型 UUID",
    "坑洞模型 UUID",
    "抛洒物模型 UUID"
  ],
  "project_name": "通用",
  "description": "路面常见病害综合检测"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 综合检测配置名称 |
| `model_uuids` | string[] | 是 | 模型 UUID 列表，至少一个，不能重复；顺序会保留 |
| `project_name` | string | 否 | 所属项目，默认 `通用` |
| `description` | string | 否 | 配置说明 |

后端会校验所有模型存在且未删除；成功后返回完整组合配置。

## 分页查询综合检测配置

```http
GET /api/combinations?page=1&pageSize=10&projectName=通用&includeDeleted=false
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `page` | 否 | 页码，从 `1` 开始，默认 `1` |
| `pageSize` | 否 | 每页数量，默认 `10` |
| `projectName` | 否 | 按项目名称筛选 |
| `includeDeleted` | 否 | 是否包含逻辑删除的配置，默认 `false` |

## 查询组合明细

```http
GET /api/combinations/detail?uuid={combination_uuid}
```

组合 UUID 使用查询参数传递，不放入路径。返回示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "uuid": "7985d2f7-e7f1-4b69-a827-0d8114d654fc",
    "name": "路面病害",
    "project_name": "通用",
    "description": "路面常见病害综合检测",
    "is_deleted": false,
    "models": [
      {
        "uuid": "裂缝模型 UUID",
        "name": "裂缝",
        "detection_type": 3,
        "prompt": "crack",
        "model_file": "sam3.pt",
        "storage_key": "平台/sam/model/sam3.pt",
        "project_name": "通用",
        "description": "SAM 裂缝分割模型"
      }
    ],
    "created_at": "2026-07-10T10:00:00+08:00",
    "updated_at": "2026-07-10T10:00:00+08:00"
  }
}
```

分页查询中的每个 `items` 元素使用相同结构。

## 修改综合检测配置

```http
PUT /api/combinations?uuid={combination_uuid}
Content-Type: application/json
```

请求体字段都可选。传入 `model_uuids` 时，它代表完整的模型列表，后端会在同一事务内替换原有关联：

```json
{
  "name": "路面病害 V2",
  "model_uuids": ["裂缝模型 UUID", "坑洞模型 UUID"],
  "description": "移除抛洒物检测"
}
```

可更新字段：`name`、`model_uuids`、`project_name`、`description`、`is_deleted`。

## 删除综合检测配置

```http
DELETE /api/combinations?uuid={combination_uuid}
```

删除为逻辑删除，不会删除模型配置或 S3 中的模型文件：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted": true,
    "uuid": "7985d2f7-e7f1-4b69-a827-0d8114d654fc"
  }
}
```
