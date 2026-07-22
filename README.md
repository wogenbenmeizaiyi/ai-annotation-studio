# AI Annotation Studio

## 快速启动

运行前准备：启动 Docker Desktop，并安装 PowerShell 7、Node.js/Corepack、Python 3.12
和 `uv`。只有运行 YOLO/SAM 推理或训练时才需要 NVIDIA/CUDA 和对应模型文件。

```powershell
cd D:\project\ai\ai-annotation-studio
```

### 模式一：不配置 `.env`

只想先运行系统、不使用 Qwen 时，不需要创建任何 `.env`，直接执行：

```powershell
.\scripts\dev.ps1 -Profile full -Infra local
```

脚本会自动生成凭据，启动 PostgreSQL、RabbitMQ、Redis、MinIO，创建两个数据库和
`ai-cmm` bucket，执行迁移，然后原生启动前端、两个 API、Worker 和 Consumer。

这种模式下普通任务、标注和识别接口可以运行，但需要第三方大模型 Key 的 AI 训练分析和
Qwen 多模态功能不可用。

### 模式二：配置 `.env`，启用 Qwen

`.env.example` 只是模板，不会被应用直接读取。先复制成两个服务真正读取的 `.env`：

```powershell
Copy-Item services\annotation\.env.example services\annotation\.env
Copy-Item services\recognition\.env.example services\recognition\.env

notepad services\annotation\.env
notepad services\recognition\.env
```

标注服务至少填写：

```dotenv
# services/annotation/.env
AGENT_API_KEY=你的_qwen_key

# 以下两项有默认值，使用默认百炼接口时可以不改
AGENT_MODEL=qwen3.7-plus
AGENT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

识别服务至少填写：

```dotenv
# services/recognition/.env
QWEN_API_KEY=你的_qwen_key
```

两个服务可以填写同一把 Qwen Key。本地模式下，模板里的 PostgreSQL、RabbitMQ、Redis
和 S3 参数不需要填写，脚本会自动覆盖。保存后执行：

```powershell
.\scripts\dev.ps1 -Profile full -Infra local
```

修改 `.env` 后，需要按 `Ctrl+C` 停止当前进程并重新启动。

### 启动后访问

| 功能 | 地址 |
| --- | --- |
| Web | `http://127.0.0.1:5173` |
| 标注 API 文档 | `http://127.0.0.1:8811/docs` |
| 识别 API 文档 | `http://127.0.0.1:7987/docs` |
| RabbitMQ 管理界面 | `http://127.0.0.1:15674` |
| MinIO 管理界面 | `http://127.0.0.1:19001` |

RabbitMQ、MinIO 等本地登录凭据保存在 `.local/infra.env`。首次启动时 Torch/Ultralytics
加载可能较慢；如果页面暂时出现 500，请等两个 API 日志出现
`Application startup complete` 后刷新。

## `.env` 必填与可选参数

两个 Python 服务各自读取自己的 `.env`，不读取根目录 `.env`。本地模式下各类参数的
填写要求如下：

| 参数类别 | 是否需要填写 | 说明 |
| --- | --- | --- |
| `AGENT_API_KEY` | 使用标注服务 AI 训练分析时必填 | `AGENT_MODEL` 和 `AGENT_BASE_URL` 有默认值 |
| `QWEN_API_KEY` | 使用识别服务 Qwen 多模态识别时必填 | 可以和 `AGENT_API_KEY` 使用同一把 Key |
| `POSTGRES_*` | 不需要 | 脚本生成连接，并固定使用两个不同数据库 |
| `RABBITMQ_HOST/PORT/USER/PASS/VHOST` | 不需要 | 脚本连接本地 RabbitMQ 并生成凭据 |
| `REDIS_*` | 不需要 | 脚本连接本地 Redis 并生成密码 |
| `S3_*` | 不需要 | 脚本连接本地 MinIO、生成凭据并创建 `ai-cmm` bucket |
| RabbitMQ 队列、交换机和死信名称 | 可选 | 不填写时使用识别服务代码默认值；填写后本地模式会保留 |
| 模型路径、超时、重试和资源阈值 | 可选 | 不填写时使用代码默认值；模型文件本身仍需存在 |
| `apps/web/.env.local` | 可选 | 不创建时前端默认连接本机两个 API 和 SAM3 WebSocket |

使用 `-Infra local` 时，启动脚本先读取两个服务 `.env` 中的业务配置，再用
`.local/infra.env` 覆盖 PostgreSQL、RabbitMQ、Redis 和 S3 的连接地址及凭据。因此，即使
两个 `.env` 只填写了 Qwen Key，其余本地组件仍会自动启动和配置。两个本地数据库固定为
`annotation_studio_local` 和 `recognition_service_local`，队列名称等业务参数不会被覆盖。

推荐仅配置 Key 时明确使用本地模式，避免探测模板里的外部示例地址：

```powershell
.\scripts\dev.ps1 -Profile full -Infra local
```

### 使用外部基础设施

使用 `-Infra external` 时，两个服务的 `.env` 都必须存在并填写完整的外部连接；它们可以
使用相同的 `POSTGRES_HOST`、`POSTGRES_PORT`、用户名和密码，但 `POSTGRES_DB` 必须不同。

| 服务 | 外部模式必填连接参数 | 可选参数 |
| --- | --- | --- |
| 标注服务 | `POSTGRES_HOST`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY` | `POSTGRES_PORT`、S3 region/signature/bucket 使用默认值时可省略 |
| 识别服务 | `POSTGRES_HOST`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`RABBITMQ_HOST`、`RABBITMQ_USER`、`RABBITMQ_PASS`、`REDIS_HOST`、`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY` | 各端口、RabbitMQ vhost、Redis DB 和无密码 Redis 的 password 可省略 |

`-Infra auto` 不会根据 Qwen Key 自动配置外部基础设施。它会把两个 `.env` 当作候选外部
配置执行带认证的协议检查：只有两个文件都存在、所有外部依赖都可用且数据库不相同时才
使用外部环境；缺少连接参数或任意检查失败时，整套切换到本地 Docker 基础设施。若复制了
完整模板但只想填写 Key，使用 `-Infra local` 最明确。

`.env`、`.env.local`、`.local/` 均不会进入 Git。

## 常用启动命令

```powershell
# 完整本地启动
.\scripts\dev.ps1 -Profile full -Infra local

# 只启动前端
.\scripts\dev.ps1 -Profile web

# 启动两个 FastAPI，不启动 Worker、Consumer 和前端
.\scripts\dev.ps1 -Profile api -Infra local

# 使用外部基础设施
.\scripts\dev.ps1 -Profile full -Infra external

# 自动选择外部或本地基础设施
.\scripts\dev.ps1 -Profile full -Infra auto
```

Ctrl+C 会停止本次创建的原生业务进程，本地基础设施容器和命名卷会保留。

## 本地基础设施

```powershell
.\scripts\infra.ps1 -Action up
.\scripts\infra.ps1 -Action status
.\scripts\infra.ps1 -Action down
.\scripts\infra.ps1 -Action reset
```

本地环境包含：

- PostgreSQL `127.0.0.1:15432`，数据库为 `annotation_studio_local` 和 `recognition_service_local`
- RabbitMQ `127.0.0.1:15673`，管理界面 `http://127.0.0.1:15674`
- Redis `127.0.0.1:16379`
- MinIO `http://127.0.0.1:19000`，控制台 `http://127.0.0.1:19001`
- 自动创建的 S3 bucket：`ai-cmm`

随机本地凭据保存在 `.local/infra.env`。`down` 保留数据；`reset` 要求输入 `RESET`，随后删除命名卷并创建空环境。

本地基础设施不提供 YOLO/SAM 模型和第三方大模型 API Key。模型文件仍需放入各服务约定目录；标注服务容器镜像也不再打包被 Git 忽略的 SAM 模型，后续服务器部署应把模型目录挂载到 `/app/models`。

## 项目说明

AI Annotation Studio 是一个 monorepo。本地开发时，前端和两个 Python 服务通过 pnpm/uv
原生运行，Docker 只运行本地基础设施。

```text
apps/web/                 Vue 3 标注与识别前端
services/annotation/      FastAPI 标注、YOLO 训练与 SAM3 服务
services/recognition/     FastAPI、Celery Worker 与结果 Consumer
infra/local/              本地 PostgreSQL、RabbitMQ、Redis、MinIO
scripts/                  本地启动、基础设施和检查脚本
```

两个 Python 服务可以连接同一个 PostgreSQL 实例，但必须使用不同数据库，因为它们拥有
独立的 Alembic 迁移历史。识别服务的任务、结果和死信队列也由识别服务独立配置。

### 子项目独立启动

各子项目仍可独立运行：

```powershell
cd apps\web
corepack pnpm dev

cd services\annotation
uv run python run.py

cd services\recognition
.\start.ps1
```

两个 Python 服务支持 `APP_ENV_FILE` 指定环境文件；未设置时继续读取项目内 `.env`。Vite 代理支持：

- `VITE_ANNOTATION_PROXY_TARGET`
- `VITE_RECOGNITION_PROXY_TARGET`
- `VITE_SAM3_PROXY_TARGET`

默认目标是本机的 `8811`、`7987` 和 `8811/ws`。

### 迁移基线

仓库由以下 `deploy` 快照初始化，原仓库历史没有合入：

| 项目 | 原提交 |
| --- | --- |
| ai-annotation-studio-web | `e07b3f0dca09bed43b5f16dc60ee8bf5a1796794` |
| ai-annotation-studio-service | `099e2efb79e453606698e13ad7d3a9c1bff27ed3` |
| image_detection_service（原目录 `rabbitMQ_test`） | `d034bd0a44dc01acfbe8b663ecfdca3c2469f301` |

## 检查

```powershell
.\scripts\check.ps1
```

脚本执行前端类型检查/构建、Python 编译、Ruff、pytest、Alembic heads、Compose 配置和 Git 敏感文件检查。识别服务当前没有可收集的 pytest 用例时会给出提示而不是失败。

## GitLab 镜像流水线

在 GitLab 项目设置以下变量：

- `CONTAINER_REGISTRY`
- `CONTAINER_REGISTRY_NAMESPACE`
- `CONTAINER_REGISTRY_USERNAME`
- `CONTAINER_REGISTRY_PASSWORD`（masked、protected）

`deploy` 分支按变更目录构建并推送：

```text
web
annotation
recognition-api
recognition-worker
recognition-consumer
```

运行镜像同时具有不可变的 `$CI_COMMIT_SHA` 标签和浮动的 `deploy` 标签。两个 Python 依赖镜像使用构建输入哈希缓存；较旧流水线不会把 `deploy` 标签回退到旧提交。

本阶段不包含 SSH、服务器 Compose 文件交付、`docker pull` 或生产容器启动。
