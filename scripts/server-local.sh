#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"
compose_file="$repo_root/infra/server/compose.yml"
gpu_compose_file="$repo_root/infra/server/compose.gpu.yml"

action="up"
env_file="$repo_root/.local/server.env"
origin_override=""
tag_override=""
gpu_mode="auto"
skip_build=false
confirm_reset=false

usage() {
    cat <<'EOF'
在一台 Linux 服务器上构建并运行完整的 AI Annotation Studio。

用法：
  ./scripts/server-local.sh <操作> [选项]

操作：
  init          生成独立部署环境文件，不启动容器
  build         根据当前源码构建 6 个业务镜像
  up            构建镜像并启动完整服务（默认）
  restart       重新构建并重建业务容器
  down          停止容器，保留数据库和对象存储数据
  status        查看容器状态
  logs          持续查看容器日志
  create-admin  交互式创建首个超级管理员
  config        展开并检查最终 Compose 配置
  reset         删除本部署的容器和命名卷，需要同时提供 --yes

选项：
  --origin <url>      浏览器访问地址，例如 http://192.168.1.20:7280
  --tag <tag>         本机构建的业务镜像标签，默认读取环境文件
  --env-file <path>   指定部署环境文件，默认 .local/server.env
  --gpu               强制启用 NVIDIA GPU Compose 配置
  --cpu               不请求 NVIDIA GPU，并关闭识别 GPU 资源检查
  --no-build          up/restart 时跳过业务镜像构建
  --yes               确认 reset 删除全新部署产生的命名卷
  -h, --help          显示帮助

首次启动：
  ./scripts/server-local.sh up --origin http://服务器IP:7280
  ./scripts/server-local.sh create-admin
EOF
}

if (($# > 0)) && [[ "$1" != --* ]]; then
    action="$1"
    shift
fi

require_value() {
    local option="$1"
    local value="${2:-}"
    if [[ -z "$value" || "$value" == --* ]]; then
        echo "参数 $option 缺少值。" >&2
        usage >&2
        exit 2
    fi
}

while (($# > 0)); do
    case "$1" in
        --origin)
            require_value "$1" "${2:-}"
            origin_override="$2"
            shift 2
            ;;
        --tag)
            require_value "$1" "${2:-}"
            tag_override="$2"
            shift 2
            ;;
        --env-file)
            require_value "$1" "${2:-}"
            env_file="$2"
            shift 2
            ;;
        --gpu)
            gpu_mode="gpu"
            shift
            ;;
        --cpu)
            gpu_mode="cpu"
            shift
            ;;
        --no-build)
            skip_build=true
            shift
            ;;
        --yes)
            confirm_reset=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "未知参数：$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$action" in
    init|build|up|restart|down|status|logs|create-admin|config|reset) ;;
    *)
        echo "未知操作：$action" >&2
        usage >&2
        exit 2
        ;;
esac

if [[ "$env_file" != /* ]]; then
    env_file="$repo_root/$env_file"
fi

random_hex() {
    od -An -N24 -tx1 /dev/urandom | tr -d ' \n'
}

detect_default_origin() {
    local detected_ip
    detected_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    if [[ -z "$detected_ip" ]]; then
        detected_ip="127.0.0.1"
    fi
    printf 'http://%s:7280' "$detected_ip"
}

origin_host() {
    local origin="$1"
    local authority="${origin#*://}"
    authority="${authority%%/*}"
    printf '%s' "${authority%%:*}"
}

initialize_environment() {
    if [[ -f "$env_file" ]]; then
        return
    fi

    local public_origin="${origin_override:-$(detect_default_origin)}"
    local public_host
    local cookie_secure=false
    public_host="$(origin_host "$public_origin")"
    if [[ "$public_origin" == https://* ]]; then
        cookie_secure=true
    fi

    mkdir -p -- "$(dirname -- "$env_file")"
    cat >"$env_file" <<EOF
# 由 scripts/server-local.sh 生成。包含真实凭据，不要提交到 Git。
BUSINESS_IMAGE_TAG=${tag_override:-local}

PUBLIC_ORIGIN=$public_origin
AUTH_ALLOWED_ORIGINS=$public_origin,http://localhost:7280,http://127.0.0.1:7280
AUTH_COOKIE_SECURE=$cookie_secure
S3_PUBLIC_ENDPOINT=http://$public_host:19000

WEB_PORT=7280
S3_PORT=19000
INFRA_BIND_ADDRESS=127.0.0.1
POSTGRES_PORT=15432
RABBITMQ_PORT=15673
RABBITMQ_MANAGEMENT_PORT=15674
REDIS_PORT=16379
MINIO_CONSOLE_PORT=19001

POSTGRES_USER=ai_studio
POSTGRES_PASSWORD=$(random_hex)
RABBITMQ_USER=ai_studio
RABBITMQ_PASSWORD=$(random_hex)
REDIS_PASSWORD=$(random_hex)
MINIO_USER=ai_studio
MINIO_PASSWORD=$(random_hex)

ANNOTATION_POSTGRES_DB=annotation_studio
RECOGNITION_POSTGRES_DB=recognition_service
AUTH_POSTGRES_DB=auth_service

AUTH_ISSUER=ai-annotation-studio-auth
AUTH_AUDIENCE=ai-annotation-studio
AUTH_REDIS_DB=3
AUTH_ACCESS_TOKEN_MINUTES=15
AUTH_REFRESH_TOKEN_DAYS=7

AGENT_API_KEY=${AGENT_API_KEY:-}
AGENT_MODEL=${AGENT_MODEL:-qwen3.7-plus}
AGENT_BASE_URL=${AGENT_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}
QWEN_API_KEY=${QWEN_API_KEY:-}

PUBLIC_SUBMIT_RATE=30
PUBLIC_DIRECT_RATE=10
PUBLIC_QUERY_RATE=120
PUBLIC_MAX_IMAGES=100
PUBLIC_MAX_UPLOAD_BYTES=20971520
PUBLIC_IMAGE_URL_ALLOWLIST=

RABBITMQ_QUEUE_NAME=tasks.image.disease_detection
RABBITMQ_RESULT_QUEUE=events.image.disease_detected
RABBITMQ_RESULT_EXCHANGE=events.image.disease_detected

RESOURCE_CHECK_ENABLED=true
RESOURCE_MIN_SYSTEM_MEMORY_MB=1024
RESOURCE_MIN_GPU_MEMORY_MB=2048
EOF
    chmod 600 "$env_file"
    echo "已生成独立部署配置：$env_file"
    echo "基础设施密码已随机生成，文件权限已设置为 600。"
}

read_env_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$env_file" | tail -n 1
}

require_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "未找到 docker，请先安装 Docker Engine 和 Compose 插件。" >&2
        exit 1
    fi
    if ! docker compose version >/dev/null 2>&1; then
        echo "未找到 docker compose 插件。" >&2
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo "Docker Engine 当前不可用。" >&2
        exit 1
    fi
}

pull_docker_image() {
    local image="$1"
    local attempt
    for attempt in 1 2 3; do
        echo "拉取基础镜像 $image（第 $attempt/3 次）..."
        if docker pull --platform linux/amd64 "$image"; then
            return
        fi
        if ((attempt < 3)); then
            sleep $((3 * attempt))
        fi
    done
    echo "基础镜像拉取失败：$image" >&2
    return 1
}

build_business_images() {
    local image_tag="$1"
    local base_image

    export DOCKER_BUILDKIT=1
    echo "正在根据当前源码构建业务镜像，标签：$image_tag"

    for base_image in \
        "node:22-alpine" \
        "nginx:alpine" \
        "python:3.12-slim" \
        "pytorch/pytorch:2.10.0-cuda13.0-cudnn9-runtime"; do
        pull_docker_image "$base_image"
    done

    docker build \
        --platform linux/amd64 \
        --build-arg VITE_APP_BASE_PATH=/ \
        -f apps/web/deploy/Dockerfile \
        -t "ai-studio-web:$image_tag" \
        apps/web

    docker build \
        --platform linux/amd64 \
        -f services/annotation/Dockerfile.deps \
        -t "ai-studio-annotation-deps:$image_tag" \
        services/annotation
    docker build \
        --platform linux/amd64 \
        --build-arg "BASE_IMAGE=ai-studio-annotation-deps:$image_tag" \
        -f services/annotation/Dockerfile \
        -t "ai-studio-annotation:$image_tag" \
        services/annotation

    docker build \
        --platform linux/amd64 \
        -f services/auth/Dockerfile.deps \
        -t "ai-studio-auth-deps:$image_tag" \
        services/auth
    docker build \
        --platform linux/amd64 \
        --build-arg "BASE_IMAGE=ai-studio-auth-deps:$image_tag" \
        -f services/auth/Dockerfile \
        -t "ai-studio-auth:$image_tag" \
        services/auth

    docker build \
        --platform linux/amd64 \
        -f services/recognition/Dockerfile.deps \
        -t "ai-studio-recognition-deps:$image_tag" \
        services/recognition

    local target
    for target in api worker consumer; do
        docker build \
            --platform linux/amd64 \
            --build-arg "BASE_IMAGE=ai-studio-recognition-deps:$image_tag" \
            -f "services/recognition/Dockerfile.$target" \
            -t "ai-studio-recognition-$target:$image_tag" \
            services/recognition
    done
}

gpu_enabled=false
configure_gpu_mode() {
    case "$gpu_mode" in
        gpu)
            gpu_enabled=true
            ;;
        cpu)
            gpu_enabled=false
            ;;
        auto)
            if docker info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; then
                gpu_enabled=true
            fi
            ;;
    esac

    if [[ "$gpu_enabled" == true ]]; then
        echo "已启用 NVIDIA GPU 容器配置。"
    else
        export RESOURCE_CHECK_ENABLED=false
        echo "未启用 NVIDIA GPU 容器配置；识别 GPU 资源检查已关闭。"
    fi
}

compose() {
    local arguments=(
        compose
        --project-directory "$repo_root"
        --env-file "$env_file"
        -f "$compose_file"
    )
    if [[ "$gpu_enabled" == true ]]; then
        arguments+=(-f "$gpu_compose_file")
    fi
    docker "${arguments[@]}" "$@"
}

prepare_runtime_directories() {
    mkdir -p \
        "$repo_root/services/annotation/logs" \
        "$repo_root/services/annotation/models" \
        "$repo_root/services/annotation/storage/train_data" \
        "$repo_root/services/annotation/runs" \
        "$repo_root/services/recognition/logs" \
        "$repo_root/services/recognition/models"
}

initialize_environment

if [[ "$action" == "init" ]]; then
    echo "请检查配置后启动："
    echo "  $env_file"
    echo "  ./scripts/server-local.sh up"
    exit 0
fi

require_docker
configure_gpu_mode

if [[ -n "$origin_override" ]]; then
    public_host="$(origin_host "$origin_override")"
    export PUBLIC_ORIGIN="$origin_override"
    export AUTH_ALLOWED_ORIGINS="$origin_override,http://localhost:7280,http://127.0.0.1:7280"
    export S3_PUBLIC_ENDPOINT="http://$public_host:19000"
    if [[ "$origin_override" == https://* ]]; then
        export AUTH_COOKIE_SECURE=true
    fi
fi

image_tag="${tag_override:-$(read_env_value BUSINESS_IMAGE_TAG)}"
image_tag="${image_tag:-local}"
export BUSINESS_IMAGE_TAG="$image_tag"

cd "$repo_root"

case "$action" in
    build)
        build_business_images "$image_tag"
        ;;
    up)
        prepare_runtime_directories
        if [[ "$skip_build" != true ]]; then
            build_business_images "$image_tag"
        fi
        compose up -d --remove-orphans
        compose ps
        echo
        echo "平台地址：${origin_override:-$(read_env_value PUBLIC_ORIGIN)}"
        echo "首次运行后创建超级管理员："
        echo "  ./scripts/server-local.sh create-admin"
        ;;
    restart)
        prepare_runtime_directories
        if [[ "$skip_build" != true ]]; then
            build_business_images "$image_tag"
        fi
        compose up -d --force-recreate --remove-orphans
        compose ps
        ;;
    down)
        compose down
        ;;
    status)
        compose ps
        ;;
    logs)
        compose logs --follow --tail=200
        ;;
    create-admin)
        compose exec auth python -m scripts.create_super_admin
        ;;
    config)
        compose config
        ;;
    reset)
        if [[ "$confirm_reset" != true ]]; then
            echo "reset 会删除这个独立部署的 PostgreSQL、RabbitMQ、Redis、MinIO 和认证密钥卷。" >&2
            echo "确认清空时执行：./scripts/server-local.sh reset --yes" >&2
            exit 1
        fi
        compose down --volumes --remove-orphans
        echo "独立部署的容器和命名卷已删除。源码及挂载的模型目录未删除。"
        ;;
esac
