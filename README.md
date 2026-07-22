# AI Annotation Studio

AI Annotation Studio monorepo，包含前端、标注/训练服务和识别服务。业务应用可在本机通过 pnpm/uv 原生运行；Docker 仅用于本地基础设施和 GitLab 镜像构建。

## 目录

```text
apps/web/                 Vue 3 标注与识别前端
services/annotation/      FastAPI 标注、YOLO 训练与 SAM3 服务
services/recognition/     FastAPI、Celery Worker 与结果 Consumer
infra/local/              本地 PostgreSQL、RabbitMQ、Redis、MinIO
scripts/                  本地启动、基础设施和检查脚本
```

仓库由以下 `deploy` 快照初始化：

| 项目 | 原提交 |
| --- | --- |
| ai-annotation-studio-web | `e07b3f0dca09bed43b5f16dc60ee8bf5a1796794` |
| ai-annotation-studio-service | `099e2efb79e453606698e13ad7d3a9c1bff27ed3` |
| image_detection_service（原目录 `rabbitMQ_test`） | `d034bd0a44dc01acfbe8b663ecfdca3c2469f301` |

原仓库历史没有合入；上表用于追溯迁移基线。

## 环境要求

- Windows PowerShell 7
- Node.js `^20.19.0 || >=22.12.0` 与 Corepack
- Python 3.12 和 `uv`
- Docker Desktop（仅在使用本地基础设施时需要）
- NVIDIA/CUDA 环境（运行 YOLO/SAM 推理或训练时需要）

首次使用外部服务时，分别创建配置文件：

```powershell
Copy-Item apps\web\.env.example apps\web\.env.local
Copy-Item services\annotation\.env.example services\annotation\.env
Copy-Item services\recognition\.env.example services\recognition\.env
```

`.env`、`.env.local`、`.local/` 均不会进入 Git。

## 原生本地开发

```powershell
# 默认：启动全部业务进程，自动选择外部或本地基础设施
.\scripts\dev.ps1

# 只启动前端
.\scripts\dev.ps1 -Profile web

# 启动两个 FastAPI，不启动 Worker、Consumer 和前端
.\scripts\dev.ps1 -Profile api

# 强制使用本地或外部基础设施
.\scripts\dev.ps1 -Profile full -Infra local
.\scripts\dev.ps1 -Profile full -Infra external
```

原生端口：

| 进程 | 地址 |
| --- | --- |
| Web | `http://127.0.0.1:5173` |
| Annotation API | `http://127.0.0.1:8811/docs` |
| Recognition API | `http://127.0.0.1:7987/docs` |

`-Infra auto` 会对两个 PostgreSQL、RabbitMQ、Redis 和两个 S3 配置执行带认证的协议检查。只有全部可用且两个服务使用不同数据库时才连接外部环境；否则整套切换到本地基础设施。选择结果在启动时输出，运行期间不会自动切换。

启动 API 前会显示两个数据库的当前/目标 Alembic revision，并自动执行 `upgrade head`。这包括外部开发/测试数据库；不要用本地启动脚本连接生产数据库。

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

## 独立启动

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
