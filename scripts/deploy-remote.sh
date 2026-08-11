#!/usr/bin/env bash
# 在 GitLab CI 中运行（无容器镜像仓库 + 外部基础设施方案）：
#   SSH 到服务器 git pull 最新代码，把所有 GitLab 环境变量打包传过去，
#   服务器上 export 后本地构建 6 个业务镜像并用 infra/server/compose.yml 启动。
#   compose.yml 直接通过 ${VAR} 把环境变量注入容器，不再生成 .env 文件。
#
# 需要的前置（在 .gitlab-ci.yml 的 before_script 中准备 ~/.ssh/id_ed25519）：
#   DEPLOY_KEY                服务器 SSH 私钥
#   DEPLOY_HOST / DEPLOY_USER / DEPLOY_PATH / DEPLOY_BRANCH / DEPLOY_REPO_URL
#   以及全部业务连接变量（POSTGRES_*、REDIS_*、RABBITMQ_*、S3_*、AGENT_*、QWEN_API_KEY ...）

set -Eeuo pipefail

DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST 未设置}"
DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/ai-annotation-studio}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
DEPLOY_REPO_URL="${DEPLOY_REPO_URL:?DEPLOY_REPO_URL 未设置}"
IMAGE_TAG="${IMAGE_TAG:-local}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"

SSH_OPTS=(
    -i "${DEPLOY_KEY_FILE:-$HOME/.ssh/id_ed25519}"
    -p "$DEPLOY_PORT"
    -o IdentitiesOnly=yes
    -o StrictHostKeyChecking=accept-new
    -o UserKnownHostsFile="$HOME/.ssh/known_hosts"
    -o ConnectTimeout=20
)
SSH_DEST="$DEPLOY_USER@$DEPLOY_HOST"

# ---------- 收集要传给服务器的环境变量 ----------
# 只转发"部署需要的连接/业务变量"，避免把所有 CI 变量（含密钥文件路径等）泄给服务器。
# 需要新增变量时在此追加。
VAR_NAMES=(
    POSTGRES_HOST POSTGRES_PORT
    AUTH_POSTGRES_USER AUTH_POSTGRES_PASSWORD AUTH_POSTGRES_DB
    ANNOTATION_POSTGRES_USER ANNOTATION_POSTGRES_PASSWORD ANNOTATION_POSTGRES_DB
    RECOGNITION_POSTGRES_USER RECOGNITION_POSTGRES_PASSWORD RECOGNITION_POSTGRES_DB
    REDIS_HOST REDIS_PORT REDIS_PASSWORD AUTH_REDIS_DB RECOGNITION_REDIS_DB
    RABBITMQ_HOST RABBITMQ_PORT RABBITMQ_USER RABBITMQ_PASS RABBITMQ_VHOST
    S3_ENDPOINT S3_PUBLIC_ENDPOINT S3_ACCESS_KEY S3_SECRET_KEY S3_REGION S3_SIGNATURE_VERSION S3_BUCKET_NAME
    AGENT_API_KEY AGENT_MODEL AGENT_BASE_URL QWEN_API_KEY
    AUTH_ISSUER AUTH_AUDIENCE AUTH_COOKIE_SECURE AUTH_ALLOWED_ORIGINS AUTH_ACCESS_TOKEN_MINUTES AUTH_REFRESH_TOKEN_DAYS
    PUBLIC_SUBMIT_RATE PUBLIC_DIRECT_RATE PUBLIC_QUERY_RATE PUBLIC_MAX_IMAGES PUBLIC_MAX_UPLOAD_BYTES PUBLIC_IMAGE_URL_ALLOWLIST
    RESOURCE_CHECK_ENABLED RESOURCE_MIN_SYSTEM_MEMORY_MB RESOURCE_MIN_GPU_MEMORY_MB
)

ENV_EXPORT_LINES=""
for name in "${VAR_NAMES[@]}"; do
    value="${!name:-}"
    if [[ -n "$value" ]; then
        # 每个值单独 base64，避免特殊字符；服务器端逐行解码
        ENV_EXPORT_LINES+="${name}=$(printf '%s' "$value" | base64 -w0)"$'\n'
    fi
done

# ---------- 生成远程脚本（heredoc 内联，不传文件） ----------
REMOTE_SCRIPT="$(
cat <<'REMOTE_EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_PATH="$DEPLOY_PATH"
DEPLOY_ORIGIN="$DEPLOY_ORIGIN"
DEPLOY_BRANCH="$DEPLOY_BRANCH"
DEPLOY_REPO_URL="$DEPLOY_REPO_URL"
IMAGE_TAG="$IMAGE_TAG"
ENV_BUNDLE_B64="$ENV_EXPORT_B64"

# ---------- 还原并导出环境变量 ----------
echo "==> 还原环境变量"
ENV_EXPORT="$(printf '%s' "$ENV_EXPORT_B64" | base64 -d)"
unset ENV_EXPORT_B64
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    key="${line%%=*}"
    value="$(printf '%s' "${line#*=}" | base64 -d)"
    export "$key=$value"
done <<<"$ENV_EXPORT"

# ---------- 拉取最新代码 ----------
if [[ ! -d "$DEPLOY_PATH/.git" ]]; then
    echo "==> $DEPLOY_PATH 不是 git 仓库，首次部署自动 clone"
    mkdir -p "$(dirname "$DEPLOY_PATH")"
    git clone --branch "$DEPLOY_BRANCH" "$DEPLOY_REPO_URL" "$DEPLOY_PATH"
fi
cd "$DEPLOY_PATH"
echo "==> git pull $DEPLOY_BRANCH"
git fetch origin "$DEPLOY_BRANCH"
git checkout -f "$DEPLOY_BRANCH"
git reset --hard "origin/$DEPLOY_BRANCH"

# ---------- 本地构建镜像 ----------
echo "==> 服务器本地构建业务镜像"
export DOCKER_BUILDKIT=1
for base_image in \
    "node:22-alpine" \
    "nginx:alpine" \
    "python:3.12-slim" \
    "pytorch/pytorch:2.10.0-cuda13.0-cudnn9-runtime"; do
    echo "==> 拉取基础镜像 $base_image"
    docker pull --platform linux/amd64 "$base_image"
done

docker build --platform linux/amd64 --build-arg VITE_APP_BASE_PATH=/ \
    -f apps/web/deploy/Dockerfile -t "ai-studio-web:$IMAGE_TAG" apps/web

docker build --platform linux/amd64 -f services/annotation/Dockerfile.deps -t "ai-studio-annotation-deps:$IMAGE_TAG" services/annotation
docker build --platform linux/amd64 --build-arg "BASE_IMAGE=ai-studio-annotation-deps:$IMAGE_TAG" \
    -f services/annotation/Dockerfile -t "ai-studio-annotation:$IMAGE_TAG" services/annotation

docker build --platform linux/amd64 -f services/auth/Dockerfile.deps -t "ai-studio-auth-deps:$IMAGE_TAG" services/auth
docker build --platform linux/amd64 --build-arg "BASE_IMAGE=ai-studio-auth-deps:$IMAGE_TAG" \
    -f services/auth/Dockerfile -t "ai-studio-auth:$IMAGE_TAG" services/auth

docker build --platform linux/amd64 -f services/recognition/Dockerfile.deps -t "ai-studio-recognition-deps:$IMAGE_TAG" services/recognition
for target in api worker consumer; do
    docker build --platform linux/amd64 --build-arg "BASE_IMAGE=ai-studio-recognition-deps:$IMAGE_TAG" \
        -f "services/recognition/Dockerfile.$target" -t "ai-studio-recognition-$target:$IMAGE_TAG" services/recognition
done

# ---------- 检测 GPU ----------
GPU_ARGS=()
if docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q '"nvidia"'; then
    echo "==> 检测到 NVIDIA runtime，启用 GPU 配置"
    GPU_ARGS=(-f infra/server/compose.gpu.yml)
else
    echo "==> 未检测到 NVIDIA runtime，使用 CPU 配置"
fi

# ---------- 启动服务（连接外部基础设施） ----------
echo "==> docker compose up（外部基础设施）"
export BUSINESS_IMAGE_TAG="$IMAGE_TAG"
docker compose -f infra/server/compose.yml "${GPU_ARGS[@]}" up -d --remove-orphans
docker compose -f infra/server/compose.yml "${GPU_ARGS[@]}" ps

echo "==> 部署完成"
REMOTE_EOF
)"

# ---------- 打包环境变量并执行远程脚本 ----------
ENV_EXPORT_B64="$(printf '%s' "$ENV_EXPORT_LINES" | base64 -w0)"

echo "==> 在服务器执行部署"
ssh "${SSH_OPTS[@]}" "$SSH_DEST" \
    "DEPLOY_PATH='$DEPLOY_PATH' DEPLOY_ORIGIN='$DEPLOY_ORIGIN' DEPLOY_BRANCH='$DEPLOY_BRANCH' DEPLOY_REPO_URL='$DEPLOY_REPO_URL' IMAGE_TAG='$IMAGE_TAG' ENV_EXPORT_B64='$ENV_EXPORT_B64' bash -s" <<<"$REMOTE_SCRIPT"
