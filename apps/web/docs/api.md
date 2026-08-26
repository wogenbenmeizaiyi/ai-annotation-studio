# AI Annotation Studio Service API

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

## Train YOLO训练

> **概念区分：**
> - **标注任务**（TaskModel）：通过 `/api/tasks/*` 管理，以 `name`（如 `"铁锈"`）标识，包含图片和标注数据。
> - **训练任务**（TrainTaskModel）：通过本组接口管理，以 `id`（自增整数）标识。同一个标注任务可以发起多次训练，每次生成一条独立的训练记录。
>
> **本组所有接口中的 `{task_id}` 均指训练任务ID**（`TrainTaskModel.id`），不是标注任务ID。

### 接口速查

| 接口 | 说明 |
|---|---|
| `POST /api/train/create` | 创建训练任务（传入标注任务名） |
| `GET /api/train/list` | 查询训练任务列表（可按标注任务名过滤） |
| `GET /api/train/{task_id}` | 查询单个训练任务状态 |
| `GET /api/train/{task_id}/stream` | SSE 实时推送每轮训练指标 |
| `GET /api/train/{task_id}/metrics` | 查询某训练任务的所有轮次历史指标 |
| `GET /api/train/{task_id}/model/download` | 获取模型 S3 预签名下载链接 |
| `DELETE /api/train/{task_id}` | 逻辑删除训练任务及其每轮指标 |
| `POST /api/train/{task_id}/retry` | 重新启动失败或等待中的训练任务 |

### POST `/api/train/create`
创建YOLO训练任务并写入PostgreSQL持久化队列。接口返回时状态为`QUEUED`；
全局唯一GPU Worker领取后才构建数据集并开始训练。

> `config` 可不传；不传时使用后端默认 YOLO26 训练配置。`model` 用于加载本地模型权重，`data` 由服务根据标注任务自动生成，前端不需要传 `data`。
> 接口只开放影响模型效果、训练策略和数据增强的参数；保存目录、日志、缓存、worker、设备、profile、compile、seed、deterministic、time、max_det 等运行/输出/复现/评估上限类参数由后端统一管理。
> `workers` 由后端环境变量 `YOLO_WORKERS` 控制，默认 `4`，不会作为接口参数开放。

**Request Body:**
```json
{
  "task_name": "my_task",
  "priority": 0,
  "config": {
    "model": "yolo26n.pt",
    "epochs": 100,
    "batch": 16,
    "imgsz": 640,
    "optimizer": "auto",
    "lr0": 0.01,
    "patience": 100,
    "mosaic": 1.0,
    "val_split": 0.2
  }
}
```

`priority`范围为`-100`到`100`，默认`0`。数值越大越先执行；优先级相同时按进入队列时间和任务ID先进先出。

**最小 Request Body:**
```json
{
  "task_name": "my_task"
}
```

**Config 字段说明:** `extra = "forbid"`，前端多传字段会直接报错。所有字段都有默认值；传入字段会覆盖默认值，未传字段使用默认值。
后端会按当前安装的 Ultralytics 版本过滤训练参数；若某个配置项在当前版本不支持，会忽略该参数并写入 warning 日志，避免训练任务直接失败。

**基础训练参数:**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---:|---|
| `model` | `str` | `"yolo26n.pt"` | 本地模型文件名或路径 |
| `epochs` | `int` | `100` | 训练轮数 |
| `patience` | `int` | `100` | Early stopping 等待轮数 |
| `batch` | `int \| float` | `16` | batch 大小；可传自动 batch 相关值 |
| `imgsz` | `int \| int[]` | `640` | 输入尺寸 |
| `pretrained` | `bool \| str` | `true` | 是否使用预训练权重或指定权重路径 |
| `single_cls` | `bool` | `false` | 是否把所有类别当成单类训练 |
| `classes` | `int[] \| null` | `null` | 只训练指定类别 |
| `rect` | `bool` | `false` | 是否启用 rectangular training |
| `multi_scale` | `float` | `0.0` | 多尺度训练范围 |
| `cos_lr` | `bool` | `false` | 是否使用 cosine LR |
| `close_mosaic` | `int` | `10` | 最后 N 轮关闭 mosaic |
| `fraction` | `float` | `1.0` | 使用训练数据比例 |
| `freeze` | `int \| int[] \| null` | `null` | 冻结层 |
| `val` | `bool` | `true` | 训练中是否验证 |
| `val_split` | `float` | `0.2` | 本服务构建数据集时验证集占比 |

**优化器和损失参数:**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---:|---|
| `optimizer` | `str` | `"auto"` | 优化器，如 `auto`、`SGD`、`AdamW` |
| `lr0` | `float` | `0.01` | 初始学习率 |
| `lrf` | `float` | `0.01` | 最终学习率系数 |
| `momentum` | `float` | `0.937` | SGD momentum / Adam beta1 |
| `weight_decay` | `float` | `0.0005` | 权重衰减 |
| `warmup_epochs` | `float` | `3.0` | warmup 轮数 |
| `warmup_momentum` | `float` | `0.8` | warmup 初始 momentum |
| `warmup_bias_lr` | `float` | `0.1` | warmup bias 学习率 |
| `box` | `float` | `7.5` | box loss 权重 |
| `cls` | `float` | `0.5` | class loss 权重 |
| `cls_pw` | `float` | `0.0` | YOLO26 分类正样本权重 |
| `dfl` | `float` | `1.5` | DFL loss 权重 |
| `pose` | `float` | `12.0` | pose loss 权重 |
| `kobj` | `float` | `1.0` | keypoint objectness loss 权重 |
| `rle` | `float` | `1.0` | RLE loss 权重 |
| `angle` | `float` | `1.0` | angle/OBB loss 权重 |
| `nbs` | `int` | `64` | nominal batch size |
| `overlap_mask` | `bool` | `true` | 训练分割时是否允许 mask 重叠 |
| `mask_ratio` | `int` | `4` | mask 下采样比例 |
| `dropout` | `float` | `0.0` | dropout 比例 |

**数据增强参数:**

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---:|---|
| `hsv_h` | `float` | `0.015` | 色相增强 |
| `hsv_s` | `float` | `0.7` | 饱和度增强 |
| `hsv_v` | `float` | `0.4` | 明度增强 |
| `degrees` | `float` | `0.0` | 旋转角度 |
| `translate` | `float` | `0.1` | 平移比例 |
| `scale` | `float` | `0.5` | 缩放比例 |
| `shear` | `float` | `0.0` | 剪切角度 |
| `perspective` | `float` | `0.0` | 透视变换比例 |
| `flipud` | `float` | `0.0` | 上下翻转概率 |
| `fliplr` | `float` | `0.5` | 左右翻转概率 |
| `bgr` | `float` | `0.0` | BGR 通道交换概率 |
| `mosaic` | `float` | `1.0` | mosaic 概率 |
| `mixup` | `float` | `0.0` | mixup 概率 |
| `cutmix` | `float` | `0.0` | cutmix 概率 |
| `copy_paste` | `float` | `0.0` | copy-paste 概率 |
| `copy_paste_mode` | `str` | `"flip"` | copy-paste 模式 |
| `auto_augment` | `str` | `"randaugment"` | 自动增强策略 |
| `erasing` | `float` | `0.4` | random erasing 概率 |
| `augmentations` | `object[] \| null` | `null` | Ultralytics 自定义增强配置 |

**Response data:** 训练任务创建结果
```json
{
  "success": true,
  "message": "训练任务已进入队列",
  "data": {
    "task_id": 1
  },
  "code": 200
}
```
> 创建成功不代表GPU已经开始训练。前端应通过任务列表或SSE观察`QUEUED → CLAIMED → RUNNING`状态变化。

训练状态：

- `QUEUED`：已持久化，等待唯一GPU Worker；
- `CLAIMED`：Worker已经原子领取任务；
- `RECOVERING`：发现持久化`last.pt`，正在准备断点恢复；
- `RUNNING`：正在占用GPU训练；
- `FINISHED`：训练和模型产出完成；
- `ERROR`：训练失败，可重新入队；
- `CANCELLED`：排队期间被删除。

服务使用PostgreSQL advisory lock和行锁保证全局最多一个训练任务运行。Worker定期写入心跳；
服务异常退出后，心跳过期的任务会重新入队。若存在`weights/last.pt`，则通过YOLO
`resume=True`从断点继续；否则从头开始并清理旧轮次指标。

### GET `/api/train/list`
查询训练任务列表。支持按标注任务名过滤，返回该任务下的所有训练记录（同一任务可训练多次）。

**Query Params（可选）:**
- `task_name: str` — 标注任务名称。不传则返回全部训练任务。

**Response data:** `TrainTaskModel.to_dict()` 列表，按创建时间倒序排列。
```json
{
  "success": true,
  "message": "成功",
  "data": [
    {
      "id": 3,
      "task_id": 1,
      "model_name": "yolo26n.pt",
      "status": "FINISHED",
      "progress": 100,
      "current_epoch": 100,
      "total_epochs": 100,
      "output_path": "yolo_models/3/best.pt",
      "created_at": "...",
      "updated_at": "..."
    },
    {
      "id": 2,
      "task_id": 1,
      "model_name": "yolo26n.pt",
      "status": "FINISHED",
      "progress": 100,
      "current_epoch": 50,
      "total_epochs": 50,
      "output_path": "yolo_models/2/best.pt",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "code": 200
}
```

### GET `/api/train/{task_id}/stream`
**SSE 流式推送** — 实时推送每轮训练指标。连接可随时建立，训练结束后自动关闭。

**Event Source:** `text/event-stream`

**推送格式（data 字段为 JSON）：**

训练中每轮推送：
```json
{
  "status": "RUNNING",
  "epoch": 3,
  "total_epochs": 100,
  "progress": 3,
  "metrics": [
    {
      "epoch": 1,
      "train_box_loss": 2.55,
      "train_cls_loss": 6.68,
      "train_dfl_loss": 0.011,
      "val_box_loss": 2.65,
      "val_cls_loss": 7.67,
      "val_dfl_loss": 0.014,
      "precision": 0,
      "recall": 0,
      "map50": 0,
      "map50_95": 0,
      "lr_pg0": 0.0001,
      "lr_pg1": 0.0001,
      "lr_pg2": 0.0991,
      ...
    },
    {
      "epoch": 2,
      ...
    },
    {
      "epoch": 3,
      ...
    }
  ]
}
```

训练结束时推送：
```json
{
  "status": "FINISHED",
  "s3_model_url": "yolo_models/42/best.pt",
  "metrics": [
    ... 完整历史指标列表
  ]
}
```

**连接规则：**
- 训练中连接：先推送已有指标 → 持续监听新轮次 → 结束时推送 `FINISHED` 并关闭
- 训练后连接：直接推送完整结果 → 关闭
- 心跳：30 秒无新数据发送 `: heartbeat`
- 错误：`status = "ERROR"`

**JavaScript 示例：**
```js
const es = new EventSource(`/api/train/${taskId}/stream`);
es.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.status === "FINISHED") {
    console.log("训练完成", data.s3_model_url);
    es.close();
  } else {
    console.log(`Epoch ${data.epoch}/${data.total_epochs}`);
    // data.metrics 包含从第1轮到当前轮的完整列表
  }
};
es.onerror = () => es.close();
```

### GET `/api/train/{task_id}/metrics`
查询某训练任务的所有轮次指标（从数据库读取）。训练完成后仍可用此接口查看历史数据。

**Response data:**
```json
{
  "success": true,
  "message": "成功",
  "data": {
    "task": {
      "id": 1,
      "task_id": 1,
      "model_name": "yolo26n.pt",
      "status": "FINISHED",
      "progress": 100,
      "current_epoch": 100,
      "total_epochs": 100,
      "output_path": "yolo_models/1/best.pt",
      "created_at": "...",
      "updated_at": "..."
    },
    "metrics": [
      {
        "id": 1,
        "train_task_id": 1,
        "epoch": 1,
        "time_cost": 12.34,
        "train_box_loss": 2.55,
        "train_cls_loss": 6.68,
        "train_dfl_loss": 0.011,
        "val_box_loss": 2.65,
        "val_cls_loss": 7.67,
        "val_dfl_loss": 0.014,
        "precision": 0,
        "recall": 0,
        "map50": 0,
        "map50_95": 0,
        "lr_pg0": 0.0001,
        "lr_pg1": 0.0001,
        "lr_pg2": 0.0991,
        "is_best": false,
        "created_at": "..."
      },
      ...
    ]
  },
  "code": 200
}
```

### GET `/api/train/{task_id}`
查询单个训练任务状态。

**Response data:** `TrainTaskModel.to_dict()`
```json
{
  "id": 1,
  "task_id": 1,
  "model_name": "yolo26n.pt",
  "status": "FINISHED",
  "pid": null,
  "progress": 100,
  "current_epoch": 100,
  "total_epochs": 100,
  "error_message": null,
  "config": { ... },
  "log_path": "storage/train_data/my_task/logs/train.log",
  "output_path": "yolo_models/1/best.pt",
  "created_at": "...",
  "updated_at": "..."
}
```

### GET `/api/train/{task_id}/model/download`
获取训练模型的 S3 预签名下载链接，有效期 1 小时。前端拿到链接后可直接从 S3/RustFS 下载模型文件。

**Path Params:** `task_id: int`

**Response data:**
```json
{
  "success": true,
  "message": "成功",
  "data": {
    "download_url": "http://172.16.0.110:9000/ai-cmm/yolo_models/3/best.pt?X-Amz-Algorithm=...&X-Amz-Expires=3600&...",
    "expires_in": 3600,
    "model_name": "yolo26n.pt",
    "filename": "best_3.pt"
  },
  "code": 200
}
```

> 若任务尚未完成或模型未上传，返回 404。

### DELETE `/api/train/{task_id}`
逻辑删除训练任务及其关联的每轮训练指标。模型文件保留在 S3 上，仍可下载。

**Path Params:** `task_id: int`

**Response data:**
```json
{
  "success": true,
  "message": "删除成功",
  "data": null,
  "code": 200
}
```

> 删除后该训练任务及其指标不再出现在列表和查询结果中，但数据库记录保留。

### POST `/api/train/{task_id}/retry`
将`ERROR`任务重新放入队列。已完成、已排队或正在运行的任务不能重复入队。

**Path Params:** `task_id: int`

**Response data:**
```json
{
  "success": true,
  "message": "训练任务已重新进入队列",
  "data": {
    "task_id": 1
  },
  "code": 200
}
```

---

## YOLO Training Agent

Agent 与现有标注、训练接口运行在同一个 FastAPI 服务中。API Key 只通过服务端环境变量配置，网页不接触模型密钥。

环境变量：

```dotenv
AGENT_API_KEY=
AGENT_MODEL=qwen3.7-plus
AGENT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AGENT_TIMEOUT_SECONDS=180
AGENT_MAX_OUTPUT_TOKENS=2000
AGENT_FORCE_IPV4=true
AGENT_LOG_FILE=agent.log
AGENT_LOG_MAX_BYTES=10485760
AGENT_LOG_BACKUP_COUNT=10
```

Agent运行日志会单独写入`AGENT_LOG_FILE`，默认采用10 MiB轮转并保留10个历史文件；
同时也会输出到控制台和主日志`app.log`。日志不会记录API Key、确认令牌、用户对话正文或完整训练参数。
内网服务器默认通过`AGENT_FORCE_IPV4=true`强制Agent模型请求使用IPv4，避免IPv6出口不完整导致TLS握手超时。
Agent固定使用`enable_thinking=false`：`qwen3.7-plus`默认开启思考模式，但百炼的JSON结构化输出要求关闭思考模式，且参数助手需要较低响应延迟。

### POST `/api/train/agent/chat`

生成训练参数草案，或在传入 `train_task_id` 时解释训练质量。此接口不会启动训练。

```json
{
  "session_id": null,
  "task_name": "my_task",
  "message": "小目标较多，希望准确率优先",
  "current_config": {
    "model": "yolo26n.pt",
    "epochs": 100,
    "batch": 16,
    "imgsz": 640
  },
  "train_task_id": null
}
```

返回的 `proposal_id` 对应后端校验并保存的参数草案；`config` 可填入训练页面。

### GET `/api/train/agent/context/{task_name}`

返回图片数量、标注数量、类别分布、目标尺寸分布和可用模型等数据集画像。

### GET `/api/train/agent/analysis/{train_task_id}`

使用确定性规则返回最佳轮次、收敛趋势、疑似过拟合、precision/recall 平衡和下一轮建议。该接口不依赖大模型，模型不可用时仍可调用。

### GET `/api/train/agent/analysis/{train_task_id}/auto`

训练状态变为`FINISHED`后，服务会在独立后台线程中自动调用一次大模型分析，并持久化结果。
同一个`train_task_id`在`agent_training_analyses`表中具有唯一记录，不会因重复训练结束回调而重复调用。

返回状态包括：

- `PENDING`：已经登记，等待分析；
- `RUNNING`：正在生成分析；
- `COMPLETED`：`analysis`为确定性指标分析，`model_result.reply`为大模型质量总结；
- `FAILED`：自动分析失败，训练任务本身仍保持`FINISHED`。

服务重启会恢复`PENDING`或`RUNNING`状态的分析。该接口只读取已保存结果，不会再次调用大模型。
确定性分析会先于模型总结保存，因此即使模型请求失败，`analysis`仍可用于页面展示。
模型响应读取超时会自动重试一次；连接超时、鉴权错误、额度不足和限流不会自动重试。
数据库表结构由Alembic管理；CI部署会在停止旧容器后自动执行`alembic upgrade head`。

### POST `/api/train/agent/analysis/{train_task_id}/auto/retry`

仅允许重新生成状态为`FAILED`的自动分析。接口会原子地将记录重置为`PENDING`并启动后台生成；其他状态会返回`409`，避免重复调用模型。

### 训练队列环境变量

```dotenv
TRAIN_QUEUE_POLL_SECONDS=2
TRAIN_WORKER_HEARTBEAT_SECONDS=15
TRAIN_WORKER_STALE_SECONDS=120
```

`TRAIN_WORKER_STALE_SECONDS`必须明显大于心跳间隔，避免正常训练被误判为失联。

### 数据库迁移

```bash
# 创建迁移
uv run alembic revision --autogenerate -m "describe change"

# 本地应用迁移
uv run alembic upgrade head
```

CI会基于新构建的应用镜像执行相同升级命令；迁移失败时不会启动新服务。

### POST `/api/train/agent/proposals/{proposal_id}/confirm`

必须由训练页面的明确确认操作调用。`expected_config` 必须与 Agent 草案完全一致；成功后签发五分钟内、单次有效的 `confirmation_token`。

```json
{
  "expected_config": {
    "model": "yolo26n.pt",
    "epochs": 150,
    "batch": 8,
    "imgsz": 960
  }
}
```

### POST `/api/train/agent/proposals/{proposal_id}/start`

校验一次性确认令牌、草案状态和配置哈希后，创建训练任务并放入持久化队列。

```json
{
  "confirmation_token": "confirm接口返回的一次性令牌"
}
```

令牌不能复用；参数变化、令牌过期或草案已经入队时均会拒绝请求。

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
