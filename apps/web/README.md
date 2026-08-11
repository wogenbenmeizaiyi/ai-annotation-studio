# AI Annotation Studio Web

AI Annotation Studio Web 是一个面向图像识别任务的前端标注平台，主要用于管理图片数据集、完成目标检测和图像分割标注，并配合后端服务发起模型训练、查看训练指标和下载训练结果。

它不是单纯的图片管理页面，而是覆盖“创建任务 -> 上传图片 -> 标注图片 -> 配置训练 -> 查看训练结果”的完整前端工作流。项目基于 Vue 3、TypeScript、Vite 和 Vuetify 开发，生产环境通过 Docker 构建静态资源，并由 Nginx 对外提供访问。

## 项目定位

这个项目负责 AI 标注和训练流程中的前端交互部分，后端负责图片存储、标注数据保存、训练任务执行和模型文件管理。

前端主要承担：

- 给用户提供任务、图片、标注和训练页面。
- 调用后端接口读取任务、图片和标注数据。
- 将用户绘制的检测框或分割多边形保存到后端。
- 发起训练配置并展示训练过程中的关键指标。
- 提供模型下载入口，方便拿到训练完成后的模型文件。

## 核心功能

### 任务管理

首页展示所有标注任务。每个任务对应一个数据集和一种标注类型，用户可以在这里创建任务、查看任务状态、进入图片列表或删除任务。

任务卡片会展示任务名称、类型、图片数量、已标注数量和未标注数量，方便快速判断当前数据集的完成情况。

### 图片列表

进入任务后，可以查看该任务下的全部图片。页面支持图片上传、图片删除、分页查看和标注状态展示。

图片列表会根据页面可用高度自动调整每页展示数量，尽量填满当前屏幕，同时避免页面出现不必要的纵向滚动条。

### 检测标注

检测任务用于标注目标的位置框。用户进入图片后，可以在画布上绘制矩形框，并为每个框选择或填写类别。

右侧标注信息区会展示当前图片的标注列表和坐标信息。坐标以整数形式展示，避免小数位影响阅读。

### 分割标注

分割任务用于标注目标轮廓。用户可以通过手动绘制多边形的方式圈出目标区域，并为多边形设置类别。

分割标注页面支持鼠标坐标提示、画布交互和标注信息展示，界面颜色会跟随当前主题，避免深色主题下出现突兀的白色背景。

### 训练配置

任务完成标注后，可以进入训练页面配置训练参数。页面会展示主要训练参数，并用中文说明参数用途，同时保留原始参数名，方便非专业用户和研发人员共同查看。

### 训练监控

训练监控页面通过图表展示训练过程中的关键指标，例如损失、精度等。页面提供指标说明气泡，包含面向普通用户的简化判断标准和面向专业用户的解释。

### 模型下载

训练完成后，页面提供模型下载按钮。用户可以直接下载后端生成的模型文件，用于后续部署或测试。

## 典型使用流程

1. 在任务列表创建一个检测或分割任务。
2. 进入任务，上传待标注图片。
3. 点击图片进入标注页面。
4. 完成检测框或分割多边形标注。
5. 回到任务页面，进入训练配置。
6. 提交训练任务并查看训练监控。
7. 训练完成后下载模型。

## 技术栈

- Vue 3
- TypeScript
- Vite
- Vuetify
- Vue Router
- Pinia
- Axios
- ECharts / vue-echarts
- pnpm
- Docker
- Nginx

## 环境要求

本地开发需要：

- Node.js `^20.19.0 || >=22.12.0`
- pnpm

如果使用 Docker 部署，本机或服务器需要：

- Docker
- Docker Compose

## 环境变量

项目使用 Vite 环境变量。先复制模板文件：

```bash
cp .env.example .env
```

`.env.example` 默认内容：

```bash
VITE_API_BASE_URL=/api/annotation
VITE_AI_SERVICE_BASE_URL=/api/ai
VITE_APP_BASE_PATH=/web/
```

两套地址均使用同域相对路径，由 Caddy 转发：标注与训练服务使用
`VITE_API_BASE_URL`，检测服务管理使用 `VITE_AI_SERVICE_BASE_URL`。两项未配置时分别默认
使用同源的 `/api/annotation` 与 `/api/ai`。WebSocket 智能标注
使用当前站点的 `/ws/sam3`。

生产构建默认部署在 `/web/` 路径下，可通过 `VITE_APP_BASE_PATH` 覆盖。Caddy 应将 `/web/*`
反向代理到前端容器的 `7280` 端口，并保留 `/api/*` 和 `/ws/sam3` 的独立转发。

前端接口地址统一封装在：

```text
src/config/env.ts
```

注意：Vite 暴露给前端的环境变量必须以 `VITE_` 开头。

## 本地开发

安装依赖：

```bash
pnpm install
```

启动开发服务：

```bash
pnpm dev
```

常用命令：

```bash
pnpm build        # 类型检查 + 生产构建
pnpm build-only   # 只执行 Vite 构建
pnpm type-check   # TypeScript 类型检查
pnpm preview      # 本地预览生产构建结果
pnpm format       # 格式化 src 目录
```

## 目录说明

```text
deploy/                 Docker 和 Nginx 部署配置
docs/                   项目文档
public/                 静态资源，包含 favicon
src/api/                后端接口封装
src/components/         通用组件和业务组件
src/config/             前端配置封装
src/router/             路由配置
src/views/              页面视图
```

## 部署

部署相关文件集中在 `deploy/` 目录：

```text
deploy/Dockerfile
deploy/docker-compose.yml
deploy/nginx.conf
```

当前 Docker Compose 服务端口映射：

```yaml
ports:
  - '7280:80'
```

也就是浏览器访问服务器的 `7280` 端口，容器内部由 Nginx 监听 `80` 端口。

手动构建镜像：

```bash
docker build -f deploy/Dockerfile -t ai-annotation-studio-web:latest .
```

手动启动服务：

```bash
docker compose -f deploy/docker-compose.yml up -d --no-build --force-recreate
```

停止服务：

```bash
docker compose -f deploy/docker-compose.yml down
```

## CI 部署

`.gitlab-ci.yml` 只在 `deploy` 分支触发部署。

CI 流程：

1. 使用 `DEPLOY_KEY` 通过 SSH 连接目标服务器。
2. 进入服务器项目目录 `/home/weiyn/projects/ai-annotation-studio-web`。
3. 拉取并重置到 `origin/deploy`。
4. 在目标服务器执行 Docker 镜像构建。
5. 使用 `deploy/docker-compose.yml` 重启服务。

当前 CI 配置中的目标服务器：

```text
172.16.0.72:22
```

生产访问端口：

```text
7280
```

## Nginx

Nginx 配置在：

```text
deploy/nginx.conf
```

它负责：

- 托管 Vite 构建后的静态文件
- 支持前端 history 路由回退到 `index.html`
- 对 favicon 等图标资源设置缓存策略

如果新增前端路由，一般不需要额外修改 Nginx；只要保持 history fallback 即可。

## 浏览器图标

favicon 文件位于 `public/`：

```text
public/favicon.ico
public/favicon-16.png
public/favicon-32.png
public/favicon-48.png
public/apple-touch-icon.png
public/icon-192.png
public/icon-512.png
public/favicon-source.png
```

入口文件引用在：

```text
index.html
```

浏览器会强缓存 favicon。更换图标后，建议同步更新 `index.html` 中 favicon 地址的版本号，例如：

```html
<link rel="icon" href="/favicon.ico?v=20260506" />
```

如果部署后图标没有立刻变化，可以直接访问：

```text
http://服务器地址:7280/favicon.ico?v=版本号
```

也可以使用无痕窗口验证，避免浏览器缓存干扰。

## API 文档

后端接口文档已按功能拆分：

```text
docs/annotation/annotation-api.md
docs/annotation/training-api.md
```

## 开发约定

- 接口地址不要在业务代码中硬编码，统一走 `VITE_API_BASE_URL`。
- 部署配置统一放在 `deploy/` 目录。
- 静态图标资源放在 `public/` 目录。
- 修改标注、训练等核心页面后，优先检查检测标注、分割标注、训练页面三条主流程。
