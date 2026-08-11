# AI Annotation Studio 标注接口

Base URL: `/api`

统一响应格式：
```json
{
  "success": true,
  "message": "成功",
  "data": ...,
  "code": 200
}
```

---

## Tasks 任务管理

> 任务以 `name` 作为唯一标识，所有查询/删除/更新均基于任务名称。

### POST `/api/tasks/create`
创建标注任务。`name` 必须唯一。

**Request Body:**
```json
{
  "name": "my_task",
  "detection_type": "segmentation",
  "description": "任务描述",
  "categories": [
    {"id": null, "name": "cat1", "supercategory": ""}
  ]
}
```

**Response data:** TaskModel.to_dict()
```json
{
  "id": 1,
  "name": "my_task",
  "detection_type": "segmentation",
  "description": "任务描述",
  "categories": [{"id": 1, "name": "cat1", "supercategory": ""}],
  "created_at": "...",
  "updated_at": "..."
}
```

### PUT `/api/tasks/update`
更新标注任务。`name` 为定位键（要更新哪个任务），不可改名。`categories` 为空时不更新类别，非空时覆盖替换。

**Request Body:** 同 create（不含 `id`）。

### DELETE `/api/tasks/delete`
逻辑删除标注任务（设置 `is_deleted=True`），任务及其关联数据不再出现在查询结果中，但数据库记录保留。

**Query Params:** `name: str`

### GET `/api/tasks/list`
获取所有任务列表。

**Response data:** `[TaskModel.to_dict(), ...]`

### GET `/api/tasks/task`
获取单个任务详情。

**Query Params:** `name: str`

---

## Image 图片管理

> 图片相关接口均使用 `task_name` 定位任务，不再使用 task_id。

### POST `/api/image/upload`
上传图片到 RustFS 并在数据库创建记录（含初始 COCO JSONB），返回预签名访问URL。

**Request:** multipart/form-data
- `task_name: str` (Form)
- `files: list[UploadFile]` (File)

**Response data:**
```json
{
  "count": 2,
  "files": [
    {
      "id": 1,
      "task_id": 1,
      "file_name": "a3f1b2c4d5e6f7a.jpg",
      "original_name": "photo.jpg",
      "s3_key": "annotation/my_task/a3f1b2c4d5e6f7a.jpg",
      "url": "http://172.16.0.110:9000/ai-cmm/annotation/my_task/a3f1b2c4d5e6f7a.jpg?X-Amz-Algorithm=...&X-Amz-Expires=3600&...",
      "width": 1920,
      "height": 1080,
      "file_size": 245760,
      "detection_type": "segmentation",
      "is_annotated": false,
      "annotation_jsonb": { "info": ..., "categories": ..., "images": ..., "annotations": [] },
      "created_at": "...",
      "updated_at": "..."
    },
    ...
  ]
}
```

`url` 为 RustFS 预签名链接，默认有效期 1 小时（可通过 `S3_URL_EXPIRES` 环境变量配置）。前端直接用此 URL 访问图片，无需后端代理。
`s3_key` 路径格式为 `annotation/{task_name}/{file_name}`，`file_name` 为随机生成的十六进制字符串（UUID），避免删除后编号不连续的问题。

### GET `/api/image/get/{image_id}`
获取单张图片信息（含 RustFS 预签名访问 URL）。

**Path Params:** `image_id: int`

**Response data:** 同上单个图片对象（含 `url` 字段）

### GET `/api/image/list/{task_name}`
获取任务下的图片列表（每项含预签名 URL），支持分页。

**Path Params:** `task_name: str`

**Query Params（可选）:**
- `page: int`
- `page_size: int`

不带分页参数时返回全量列表，带分页参数时返回：

```json
{
  "list": [图片对象 + url, ...],
  "page": 1,
  "page_size": 20,
  "total": 50,
  "annotated_count": 15,
  "total_pages": 3
}
```

### DELETE `/api/image/delete/{image_id}`
逻辑删除单张图片（设置 `is_deleted=True`），该图片不再出现在查询结果中，但数据库记录保留。

**Path Params:** `image_id: int`

---

## Annotation 标注管理

### GET `/api/annotation/get_by_image`
根据图片 ID 获取该图片的完整 COCO 标注数据（JSONB）。

**Query Params:** `image_id: int`

**Response data:** annotation_jsonb（完整的 COCO JSON 结构）
```json
{
  "info": {...},
  "licenses": [...],
  "categories": [...],
  "images": [...],
  "annotations": [...]
}
```

### POST `/api/annotation/update`
覆盖更新某图片的标注数据。保留原有的 info/categories/images 结构，只替换 annotations 列表。

**Request Body:**
```json
{
  "image_id": 1,
  "cocoAnnotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 1,
      "bbox": [100, 200, 50, 80],
      "segmentation": [[100, 200, 150, 200, 150, 280]],
      "iscrowd": 0,
      "area": 4000
    }
  ]
}
```

**Response data:** 更新后的图片对象（含 `url`）

---

## SAM3 交互式分割（WebSocket）

> 通过 WebSocket 进行 SAM3 模型交互式分割。同一图片只需初始化一次，后续反复点击即可增量分割。
> 支持返回 mask 多边形，也支持返回 mask 外接 bbox。

### WebSocket 地址

`ws://<host>:8811/ws/sam3`

### 消息格式（JSON）

**初始化/切换图片：**
```json
{
  "action": "init",
  "s3_key": "annotation/my_task/a3f1b2c4d5e6f7a.jpg"
}
```

**初始化响应：**
先返回加载中状态：
```json
{
  "status": "loading",
  "message": "正在加载图片..."
}
```

加载完成后返回：
```json
{
  "success": true,
  "status": "ready",
  "action": "init",
  "s3_key": "annotation/my_task/a3f1b2c4d5e6f7a.jpg",
  "message": "图片已就绪，可以开始标注"
}
```

**添加交互点（前景/背景）：**
```json
{
  "action": "point",
  "x": 100,
  "y": 200,
  "label": 1
}
```
- `label`: `1` = 前景（目标区域），`0` = 背景（排除区域）

**点分割响应：**
先返回推理中状态：
```json
{
  "status": "predicting",
  "message": "正在推理..."
}
```

推理完成后返回：
```json
{
  "success": true,
  "status": "predicted",
  "action": "point",
  "point_count": 2,
  "masks": [
    {
      "contours": [[100.0, 200.0, 150.0, 200.0, 150.0, 280.0]],
      "area": 4000.0
    }
  ]
}
```
- `contours`: COCO 格式多边形坐标（扁平列表 `[x1,y1,x2,y2,...]`），可直接用于标注数据
- `area`: mask 像素面积

**添加交互点并返回 bbox：**
```json
{
  "action": "bbox",
  "x": 100,
  "y": 200,
  "label": 1
}
```

也可以使用别名：
```json
{
  "action": "box",
  "x": 100,
  "y": 200,
  "label": 1
}
```

**bbox 响应：**
先返回推理中状态：
```json
{
  "status": "predicting",
  "message": "正在推理..."
}
```

推理完成后返回：
```json
{
  "success": true,
  "status": "predicted",
  "action": "bbox",
  "point_count": 2,
  "bboxes": [
    {
      "bbox": [100.0, 200.0, 50.0, 80.0],
      "points": [
        [100.0, 200.0],
        [150.0, 200.0],
        [150.0, 280.0],
        [100.0, 280.0]
      ],
      "area": 4000.0
    }
  ]
}
```
- `bbox`: COCO bbox 格式 `[x, y, width, height]`，基于 mask 外接框向四周扩展 10%，并自动限制在图片边界内
- `points`: bbox 四个角点，顺序为左上、右上、右下、左下
- `area`: bbox 面积

**重置交互点：**
```json
{
  "action": "reset"
}
```

**重置响应：**
```json
{
  "success": true,
  "status": "ready",
  "action": "reset",
  "message": "交互点已重置，可以继续标注"
}
```

### 使用流程

1. 连接 WebSocket
2. 发送 `init` + 图片 s3_key，加载图片并创建会话
3. 反复发送 `point` 添加前景/背景点，每次自动返回分割结果
4. 需要框选结果时发送 `bbox` 或 `box`，请求参数与 `point` 相同，返回 bbox 和四角点
5. 需要重新标注时发送 `reset` 清空点，重新点击
6. 切换图片时再次发送 `init` + 新 s3_key
7. 断开连接时自动释放会话资源

