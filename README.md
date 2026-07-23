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

脚本会自动生成凭据，启动 PostgreSQL、RabbitMQ、Redis、MinIO，创建三个数据库和
`ai-cmm` bucket，执行迁移，然后原生启动前端、认证 API、两个业务 API、Worker 和 Consumer。

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
| 认证 API 文档 | `http://127.0.0.1:8787/docs` |
| 标注 API 文档 | `http://127.0.0.1:8811/docs` |
| 识别 API 文档 | `http://127.0.0.1:7987/docs` |
| RabbitMQ 管理界面 | `http://127.0.0.1:15674` |
| MinIO 管理界面 | `http://127.0.0.1:19001` |

### 首次创建超级管理员

首次启动的认证数据库没有默认账号。普通注册只能创建待审批的普通用户，首个超级管理员必须
通过交互式 CLI 创建。平台超级管理员与 PostgreSQL 用户是两套完全不同的账号。

本地基础设施模式下，保持 `dev.ps1` 运行，另开一个 PowerShell，在仓库根目录执行：

```powershell
$env:APP_ENV_FILE = (Resolve-Path .local\env\auth.env).Path
Push-Location services\auth
uv run python -m scripts.create_super_admin
Pop-Location
```

外部基础设施模式使用认证服务自己的 `.env`：

```powershell
$env:APP_ENV_FILE = (Resolve-Path services\auth\.env).Path
Push-Location services\auth
uv run python -m scripts.create_super_admin
Pop-Location
```

按提示输入用户名、显示名称和至少 12 位的密码，然后访问 `http://127.0.0.1:5173` 登录。
普通用户可在登录页申请注册，账号初始状态为“待审批”；超级管理员登录后从侧栏进入
“用户管理”批准账号。管理员重置密码后，用户下次登录必须先修改密码。

如果 CLI 提示表不存在，先运行对应模式的 `dev.ps1 -Profile api/full`。启动脚本会执行
`alembic upgrade head` 创建认证表，但不会自动创建外部 PostgreSQL 数据库，也不会自动创建
超级管理员。

RabbitMQ、MinIO 等本地登录凭据保存在 `.local/infra.env`。首次启动时 Torch/Ultralytics
加载可能较慢；如果页面暂时出现 500，请等三个 API 日志出现
`Application startup complete` 后刷新。

## `.env` 必填与可选参数

三个 Python 服务各自读取自己的 `.env`，不读取根目录 `.env`。本地模式下各类参数的
填写要求如下：

| 参数类别 | 是否需要填写 | 说明 |
| --- | --- | --- |
| `AGENT_API_KEY` | 使用标注服务 AI 训练分析时必填 | `AGENT_MODEL` 和 `AGENT_BASE_URL` 有默认值 |
| `QWEN_API_KEY` | 使用识别服务 Qwen 多模态识别时必填 | 可以和 `AGENT_API_KEY` 使用同一把 Key |
| `POSTGRES_*` | 不需要 | 脚本生成连接，并固定使用三个不同数据库 |
| `RABBITMQ_HOST/PORT/USER/PASS/VHOST` | 不需要 | 脚本连接本地 RabbitMQ 并生成凭据 |
| `REDIS_*` | 不需要 | 脚本连接本地 Redis 并生成密码 |
| `S3_*` | 不需要 | 脚本连接本地 MinIO、生成凭据并创建 `ai-cmm` bucket |
| RabbitMQ 队列、交换机和死信名称 | 可选 | 不填写时使用识别服务代码默认值；填写后本地模式会保留 |
| 模型路径、超时、重试和资源阈值 | 可选 | 不填写时使用代码默认值；模型文件本身仍需存在 |
| `apps/web/.env.local` | 可选 | 不创建时前端默认连接本机两个 API 和 SAM3 WebSocket |
| `services/auth/.env` | 本地模式不需要 | 本地脚本自动生成认证数据库、Redis 和签名密钥配置 |

### 认证参数说明

| 参数 | 所在服务 | 作用 |
| --- | --- | --- |
| `AUTH_ISSUER` | 三个服务 | JWT 签发者标识；三个服务必须完全一致 |
| `AUTH_AUDIENCE` | 三个服务 | JWT 使用方标识；三个服务必须完全一致 |
| `AUTH_PRIVATE_KEY_PATH` | 仅认证服务 | 签发登录令牌的私钥，不能提供给业务服务 |
| `AUTH_PUBLIC_KEY_PATH` | 三个服务 | 认证服务写入公钥，标注和识别服务用它验证登录令牌 |
| `AUTH_COOKIE_SECURE` | 认证服务 | 本地 HTTP 使用 `false`；正式 HTTPS 必须使用 `true` |
| `AUTH_ALLOWED_ORIGINS` | 认证、标注服务 | 允许携带平台 Cookie 的前端 Origin，不是用户/IP 白名单 |
| `PLATFORM_ALLOWED_ORIGINS` | 识别服务 | 识别管理页面的前端 Origin；匿名检测接口使用独立公开策略 |
| `AUTH_ACCESS_TOKEN_MINUTES` | 认证服务 | 短期访问令牌有效分钟数，默认 15 |
| `AUTH_REFRESH_TOKEN_DAYS` | 认证服务 | 可轮换刷新会话的有效天数，默认 7 |
| `AUTH_REDIS_*` / `REDIS_DB` | 三个服务 | 登录限流、用户状态和会话撤销信息；必须指向同一个 Redis DB |

Origin 的格式是“协议 + 主机/IP + 端口”，不包含接口路径。例如：

```dotenv
AUTH_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://server-host:7280
```

所有访问同一个前端地址的用户使用相同 Origin，不需要填写每个用户的客户端 IP。登录使用
Cookie，因此不能把平台认证来源配置成 `*`。正式部署推荐由 Nginx 在同一站点下转发
`/api/auth`、`/api/annotation` 和 `/api/recognition`。

使用 `-Infra local` 时，启动脚本先读取三个服务 `.env` 中的业务配置，再用
`.local/infra.env` 覆盖 PostgreSQL、RabbitMQ、Redis 和 S3 的连接地址及凭据。因此，即使
业务服务 `.env` 只填写了 Qwen Key，其余本地组件仍会自动启动和配置。三个本地数据库固定为
`annotation_studio_local`、`recognition_service_local` 和 `auth_service_local`，队列名称等业务参数不会被覆盖。

推荐仅配置 Key 时明确使用本地模式，避免探测模板里的外部示例地址：

```powershell
.\scripts\dev.ps1 -Profile full -Infra local
```

### 使用外部基础设施

使用 `-Infra external` 时，三个服务的 `.env` 都必须存在并填写完整的外部连接；它们可以
使用相同的 `POSTGRES_HOST`、`POSTGRES_PORT`、用户名和密码，但 `POSTGRES_DB` 必须互不相同。

先复制认证服务模板：

```powershell
Copy-Item services\auth\.env.example services\auth\.env
notepad services\auth\.env
```

| 服务 | 外部模式必填连接参数 | 可选参数 |
| --- | --- | --- |
| 标注服务 | `POSTGRES_HOST`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY` | `POSTGRES_PORT`、S3 region/signature/bucket 使用默认值时可省略 |
| 识别服务 | `POSTGRES_HOST`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`RABBITMQ_HOST`、`RABBITMQ_USER`、`RABBITMQ_PASS`、`REDIS_HOST`、`S3_ENDPOINT`、`S3_ACCESS_KEY`、`S3_SECRET_KEY` | 各端口、RabbitMQ vhost、Redis DB 和无密码 Redis 的 password 可省略 |
| 认证服务 | `POSTGRES_HOST`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`REDIS_HOST` | 各端口、无密码 Redis 的 password 可省略；开发环境可使用默认密钥路径，生产环境必须预先挂载 Ed25519 密钥 |

外部 PostgreSQL 数据库必须提前创建。数据库没有独立密码，连接密码属于 PostgreSQL Role。
例如使用数据库管理员执行：

```sql
CREATE DATABASE auth_service OWNER auth_service_user;
```

随后在 `services/auth/.env` 中填写 `auth_service_user` 的现有密码。不要把平台登录的
`super_admin` 与 PostgreSQL Role 混淆。

启动脚本会先检查三个外部数据库和其他依赖，再自动执行三个服务各自的 Alembic 迁移：

```powershell
.\scripts\dev.ps1 -Profile full -Infra external
```

外部模式会以 `services/auth/.env` 为认证配置来源，生成 Git 忽略的
`.local/env/external-*.env`，并自动把公钥、Issuer、Audience 和认证 Redis 同步给标注与
识别服务。因此不需要在三个 `.env` 中重复保存认证 Redis 密码。修改任何 `.env` 后都必须
按 `Ctrl+C` 完整停止并重新启动。

`-Infra auto` 不会根据 Qwen Key 自动配置外部基础设施。它会把三个 `.env` 当作候选外部
配置执行带认证的协议检查：只有三个服务的 `.env` 都存在、所有外部依赖都可用且三个数据库互不相同时才
使用外部环境；缺少连接参数或任意检查失败时，整套切换到本地 Docker 基础设施。若复制了
完整模板但只想填写 Key，使用 `-Infra local` 最明确。

`.env`、`.env.local`、`.local/` 均不会进入 Git。

## 常用启动命令

```powershell
# 完整本地启动
.\scripts\dev.ps1 -Profile full -Infra local

# 只启动前端
.\scripts\dev.ps1 -Profile web

# 启动认证、标注和识别三个 FastAPI，不启动 Worker、Consumer 和前端
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

- PostgreSQL `127.0.0.1:15432`，数据库为 `annotation_studio_local`、`recognition_service_local` 和 `auth_service_local`
- RabbitMQ `127.0.0.1:15673`，管理界面 `http://127.0.0.1:15674`
- Redis `127.0.0.1:16379`
- MinIO `http://127.0.0.1:19000`，控制台 `http://127.0.0.1:19001`
- 自动创建的 S3 bucket：`ai-cmm`

随机本地凭据保存在 `.local/infra.env`。`down` 保留数据；`reset` 要求输入 `RESET`，随后删除命名卷并创建空环境。

本地基础设施不提供 YOLO/SAM 模型和第三方大模型 API Key。模型文件仍需放入各服务约定目录；标注服务容器镜像也不再打包被 Git 忽略的 SAM 模型，后续服务器部署应把模型目录挂载到 `/app/models`。

## 项目说明

AI Annotation Studio 是一个 monorepo。本地开发时，前端和三个 Python 服务通过 pnpm/uv
原生运行，Docker 只运行本地基础设施。

```text
apps/web/                 Vue 3 标注、识别与用户管理前端
services/auth/            FastAPI 登录、会话和用户审批服务
services/annotation/      FastAPI 标注、YOLO 训练与 SAM3 服务
services/recognition/     FastAPI、Celery Worker 与结果 Consumer
infra/local/              本地 PostgreSQL、RabbitMQ、Redis、MinIO
scripts/                  本地启动、基础设施和检查脚本
```

三个 Python 服务可以连接同一个 PostgreSQL 实例，但必须使用不同数据库，因为它们拥有
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

三个 Python 服务支持 `APP_ENV_FILE` 指定环境文件；未设置时继续读取项目内 `.env`。Vite 代理支持：

- `VITE_ANNOTATION_PROXY_TARGET`
- `VITE_RECOGNITION_PROXY_TARGET`
- `VITE_AUTH_PROXY_TARGET`
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

脚本执行前端类型检查、Python 编译、Ruff、pytest、三个 Alembic heads、Compose 配置和 Git 敏感文件检查。

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
auth
recognition-api
recognition-worker
recognition-consumer
```

运行镜像同时具有不可变的 `$CI_COMMIT_SHA` 标签和浮动的 `deploy` 标签。三个 Python 依赖镜像使用构建输入哈希缓存；较旧流水线不会把 `deploy` 标签回退到旧提交。

### 离线导出 Linux 镜像

Windows 使用 `scripts/export-images.ps1`，Linux 使用 `scripts/export-images.sh`。两个脚本都
可以把镜像保存为 gzip 压缩包，并生成 SHA-256 校验文件。
加入认证服务后，业务运行镜像共 6 个：Web、标注、认证、识别 API、Worker 和 Consumer。

第一次打包或源码变化后，构建并导出 Linux AMD64 业务镜像：

```powershell
.\scripts\export-images.ps1 -ImageSet business -Tag offline -Build
```

业务镜像已经存在时，只导出、不重新构建：

```powershell
.\scripts\export-images.ps1 -ImageSet business -Tag offline
```

单独导出本地 PostgreSQL、RabbitMQ、Redis、MinIO 和 MinIO Client 镜像：

```powershell
.\scripts\export-images.ps1 -ImageSet infrastructure
```

同时导出业务和基础设施镜像：

```powershell
.\scripts\export-images.ps1 -ImageSet all -Tag offline -Build
```

Linux 上保留同样的流程。首次赋予脚本执行权限：

```bash
chmod +x scripts/export-images.sh
```

构建并导出业务镜像：

```bash
./scripts/export-images.sh --image-set business --tag offline --build
```

如果对应标签的业务镜像已经存在，只导出而不重新构建：

```bash
./scripts/export-images.sh --image-set business --tag offline
```

也可以导出基础设施或全部镜像：

```bash
./scripts/export-images.sh --image-set infrastructure
./scripts/export-images.sh --image-set all --tag offline --build
```

默认文件写入 `.local/exports/`。也可以使用
PowerShell 的 `-OutputPath D:\packages\ai-annotation-studio.tar.gz`，或 Linux 的
`--output /opt/packages/ai-annotation-studio.tar.gz` 指定位置。Linux 服务器校验并导入：

```bash
sha256sum -c ai-annotation-studio.tar.gz.sha256
docker load -i ai-annotation-studio.tar.gz
```

镜像包不包含 PostgreSQL/MinIO 数据卷、生产 `.env`、认证私钥或模型文件。完整部署仍需要
Compose、外部依赖连接、持久化目录、认证密钥和模型挂载。

## 认证与公开检测边界

- 标注、训练、Agent、模型库、综合配置和识别任务管理必须登录。
- 普通用户可以查看平台数据，只能修改自己创建的任务、模型和综合配置。
- 历史无归属数据只有超级管理员可以修改；响应中的 `can_manage` 决定前端是否显示操作按钮，后端仍会再次校验。
- `/api/recognition/recognize*`、`/api/project/recognize`、单任务 UUID 状态和 COCO 结果保持匿名开放。
- 匿名检测带 IP 限流、图片数量/体积限制和外部图片 URL 的 SSRF 防护。
- 公开接口文档位于识别服务 `/public/docs`；完整接口文档只允许超级管理员访问。

## Linux 单机源码部署

如果不使用 GitLab CI，可以在一台全新的 Linux 服务器上从 GitHub 拉取源码，然后直接在
服务器本机构建并运行整套系统。该方式使用 `infra/server/` 中的独立 Compose，不连接也不
迁移原有数据库。

服务器需要：

- Linux AMD64
- Docker Engine 和 Docker Compose 插件
- 可访问 Docker Hub、npm 镜像和 Python 包源
- 运行 GPU 推理/训练时安装 NVIDIA 驱动与 NVIDIA Container Toolkit
- 至少预留足够的磁盘空间；PyTorch CUDA 基础镜像和 6 个业务镜像体积较大

拉取源码后执行：

```bash
git clone git@github.com:wogenbenmeizaiyi/ai-annotation-studio.git
cd ai-annotation-studio
chmod +x scripts/server-local.sh scripts/export-images.sh

bash scripts/server-local.sh up --origin http://服务器IP:7280
```

首次运行会：

1. 在 `.local/server.env` 生成随机 PostgreSQL、RabbitMQ、Redis 和 MinIO 凭据。
2. 根据当前源码构建 Web、标注、认证、识别 API、Worker 和 Consumer 镜像。
3. 启动本机 PostgreSQL、RabbitMQ、Redis 和 MinIO。
4. 创建三个全新的空数据库以及 `ai-cmm` bucket。
5. 对空数据库执行 Alembic，创建当前版本表结构。
6. 生成并持久化认证 Ed25519 密钥。
7. 启动所有业务容器和 Nginx。

这里的 Alembic 只用于初始化新库表结构，不读取、不复制也不转换旧环境数据。三个数据库和
基础设施数据保存在 Compose 命名卷中，重复执行 `up` 会继续使用已有数据。

首次启动成功后创建平台超级管理员：

```bash
bash scripts/server-local.sh create-admin
```

常用操作：

```bash
# 查看状态和日志
bash scripts/server-local.sh status
bash scripts/server-local.sh logs

# git pull 后重新按当前源码构建并更新容器
bash scripts/server-local.sh up

# 镜像已经构建好时跳过构建
bash scripts/server-local.sh up --no-build

# 停止但保留所有数据
bash scripts/server-local.sh down

# 确认删除这套新部署的所有命名卷
bash scripts/server-local.sh reset --yes
```

脚本默认自动检测 NVIDIA Container Runtime；检测到时为标注 API、识别 API 和 Worker
启用 GPU。也可以使用 `--gpu` 或 `--cpu` 明确指定。模型文件不会从 Git 自动下载，需要放到：

```text
services/annotation/models/
services/recognition/models/
```

不使用域名时，Web `7280` 和预签名对象使用的 MinIO API `19000` 对外监听。PostgreSQL、
RabbitMQ、Redis 和 MinIO 控制台只绑定服务器的 `127.0.0.1`。浏览器、标注 API、认证 API、
公开检测 API 和 SAM3 WebSocket 都通过 Web/Nginx 同一入口访问。

### 使用域名和自动 HTTPS

先把域名的 DNS `A` 记录指向服务器公网 IP，并在安全组和系统防火墙开放 TCP `80`、`443`；
如需 HTTP/3，再开放 UDP `443`。随后执行：

```bash
bash scripts/server-local.sh up --no-build --cpu --domain wexura.cn
```

脚本会把域名配置保存到 Git 忽略的 `.local/server.env`，启用 Caddy 并自动申请 HTTPS
证书。域名模式下，Caddy 只连接 Web 容器；Web、MinIO API 和 MinIO 控制台的调试端口都只
绑定服务器 `127.0.0.1`，不对公网开放。

网页展示私有图片仍需要短时预签名 URL。它使用同一个平台域名下的 `/ai-cmm/*` 路径，
由 Web Nginx 在 Docker 内网转发到 MinIO；这不会公开 MinIO 管理界面、凭据或任意对象，
没有有效签名的请求仍会被 MinIO 拒绝。无需为 MinIO 配置额外域名或 DNS 记录。

部署配置保存在 `.local/server.env`。要填写 Qwen Key 或修改端口，编辑这个文件后重新执行
`bash scripts/server-local.sh up`。
