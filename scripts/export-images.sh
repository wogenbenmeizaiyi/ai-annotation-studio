#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"
export_directory="$repo_root/.local/exports"

image_set="business"
tag="offline"
output_path=""
build_images=false
force=false
temporary_archive=""

usage() {
    cat <<'EOF'
用法：
  ./scripts/export-images.sh [选项]

选项：
  --image-set <business|infrastructure|all>  默认 business
  --tag <tag>                               业务镜像标签，默认 offline
  --output <path.tar.gz>                    指定输出文件
  --build                                   导出前按当前源码构建业务镜像
  --force                                   覆盖现有文件
  -h, --help                                显示帮助
EOF
}

require_value() {
    if [[ -z "${2:-}" || "$2" == --* ]]; then
        echo "参数 $1 缺少值。" >&2
        exit 2
    fi
}

while (($# > 0)); do
    case "$1" in
        --image-set)
            require_value "$1" "${2:-}"
            image_set="$2"
            shift 2
            ;;
        --tag)
            require_value "$1" "${2:-}"
            tag="$2"
            shift 2
            ;;
        --output)
            require_value "$1" "${2:-}"
            output_path="$2"
            shift 2
            ;;
        --build)
            build_images=true
            shift
            ;;
        --force)
            force=true
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

case "$image_set" in
    business|infrastructure|all) ;;
    *)
        echo "--image-set 只支持 business、infrastructure 或 all。" >&2
        exit 2
        ;;
esac

business_images=(
    "ai-studio-web:$tag"
    "ai-studio-annotation:$tag"
    "ai-studio-auth:$tag"
    "ai-studio-recognition-api:$tag"
    "ai-studio-recognition-worker-gpu:$tag"
    "ai-studio-recognition-worker-multimodal:$tag"
    "ai-studio-recognition-consumer:$tag"
)
infrastructure_images=(
    "postgres:alpine"
    "rabbitmq:management-alpine"
    "redis:alpine"
    "minio/minio:latest"
    "minio/mc:latest"
)

cleanup() {
    if [[ -n "$temporary_archive" && -f "$temporary_archive" ]]; then
        rm -f -- "$temporary_archive"
    fi
}
trap cleanup EXIT

for command_name in docker gzip sha256sum; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "未找到 $command_name。" >&2
        exit 1
    fi
done
if ! docker info >/dev/null 2>&1; then
    echo "Docker Engine 当前不可用。" >&2
    exit 1
fi

cd "$repo_root"
if [[ "$build_images" == true && "$image_set" != "infrastructure" ]]; then
    "$repo_root/scripts/server-local.sh" build --tag "$tag"
fi

case "$image_set" in
    business) images=("${business_images[@]}") ;;
    infrastructure) images=("${infrastructure_images[@]}") ;;
    all) images=("${business_images[@]}" "${infrastructure_images[@]}") ;;
esac

missing_images=()
for image in "${images[@]}"; do
    if ! docker image inspect "$image" >/dev/null 2>&1; then
        missing_images+=("$image")
    fi
done
if ((${#missing_images[@]} > 0)); then
    echo "缺少以下镜像：" >&2
    printf '  %s\n' "${missing_images[@]}" >&2
    echo "业务镜像可增加 --build 后重新执行。" >&2
    exit 1
fi

mkdir -p -- "$export_directory"
if [[ -z "$output_path" ]]; then
    timestamp="$(date '+%Y%m%d-%H%M%S')"
    output_path="$export_directory/ai-annotation-studio-$image_set-$tag-$timestamp.tar.gz"
elif [[ "$output_path" != /* ]]; then
    output_path="$repo_root/$output_path"
fi
if [[ "$output_path" != *.tar.gz ]]; then
    echo "--output 必须以 .tar.gz 结尾。" >&2
    exit 2
fi

output_directory="$(dirname -- "$output_path")"
mkdir -p -- "$output_directory"
output_directory="$(CDPATH= cd -- "$output_directory" && pwd)"
output_path="$output_directory/$(basename -- "$output_path")"
checksum_path="$output_path.sha256"

if [[ -e "$output_path" || -e "$checksum_path" ]]; then
    if [[ "$force" != true ]]; then
        echo "输出文件已经存在：$output_path。需要覆盖时增加 --force。" >&2
        exit 1
    fi
    rm -f -- "$output_path" "$checksum_path"
fi

temporary_archive="$(mktemp --tmpdir="$output_directory" '.ai-studio-images.XXXXXX.tar.gz')"
echo "正在导出镜像："
printf '  %s\n' "${images[@]}"
docker save "${images[@]}" | gzip -1 >"$temporary_archive"
mv -- "$temporary_archive" "$output_path"
temporary_archive=""

(
    cd "$output_directory"
    sha256sum "$(basename -- "$output_path")" >"$(basename -- "$checksum_path")"
)

echo
echo "镜像包：$output_path"
echo "校验文件：$checksum_path"
echo "文件大小：$(du -h "$output_path" | awk '{print $1}')"
