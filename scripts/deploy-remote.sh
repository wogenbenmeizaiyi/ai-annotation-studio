#!/usr/bin/env bash
# 在 GitLab CI 中运行（无容器镜像仓库方案）：
#   1. 解码 ENV_BUNDLE_B64 -> 三个服务的 .env
#   2. 上传还原出的 .env 到服务器
#   3. SSH 到服务器，cd 到部署目录并 git pull 最新代码
#   4. 服务器本地构建 6 个业务镜像并用 compose 启动
#     （复用 scripts/server-local.sh，无需任何镜像仓库）
#
# 需要的 GitLab CI/CD Variables：
#   ENV_BUNDLE_B64            三个服务 .env 的 base64（scripts/env-bundle.ps1 生成）
#   DEPLOY_KEY                服务器 SSH 私钥（Protected，File 或 String 均可）
#   DEPLOY_HOST               服务器 IP/域名
#   DEPLOY_USER               SSH 用户名（默认 root）
#   DEPLOY_PATH               服务器上仓库目录（默认 /opt/ai-annotation-studio）
#   DEPLOY_ORIGIN             浏览器访问地址，默认 http://$DEPLOY_HOST:7280
#   DEPLOY_BRANCH             服务器上要拉取的分支（默认 main）

set -Eeuo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST (服务器 IP/域名) 未设置}"
DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/ai-annotation-studio}"
DEPLOY_ORIGIN="${DEPLOY_ORIGIN:-http://$DEPLOY_HOST:7280}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
IMAGE_TAG="${IMAGE_TAG:-local}"

ENV_BUNDLE_B64="${ENV_BUNDLE_B64:?ENV_BUNDLE_B64 未设置}"
DEPLOY_KEY="${DEPLOY_KEY:?DEPLOY_KEY 未设置}"

# ---------- 准备 SSH ----------
TMP_SSH="$(mktemp -d)"
trap 'rm -rf "$TMP_SSH"' EXIT

# GitLab 变量为 File 类型时 DEPLOY_KEY 是文件路径，String 类型时是私钥内容。
# 与 ai-annotation-studio-web 项目一致的写法：printf + tr -d '\r' 清理 CR。
KEY_FILE="$TMP_SSH/deploy_key"
if [[ -f "$DEPLOY_KEY" ]]; then
    cp "$DEPLOY_KEY" "$KEY_FILE"
else
    printf '%s\n' "$DEPLOY_KEY" | tr -d '\r' >"$KEY_FILE"
fi
chmod 600 "$KEY_FILE"

SSH_OPTS=(
    -i "$KEY_FILE"
    -o IdentitiesOnly=yes
    -o StrictHostKeyChecking=accept-new
    -o UserKnownHostsFile="$TMP_SSH/known_hosts"
    -o ConnectTimeout=20
)
SSH_DEST="$DEPLOY_USER@$DEPLOY_HOST"

# ---------- 还原三个服务的 .env ----------
ENV_TEXT="$(printf '%s' "$ENV_BUNDLE_B64" | base64 -d)"
decode_env() {
    local marker="$1"
    local out="$2"
    mkdir -p "$(dirname "$out")"
    python3 - "$marker" "$ENV_TEXT" "$out" <<'PY'
import sys
marker, text, out = sys.argv[1], sys.argv[2], sys.argv[3]
chunks = text.split("### FILE: ")[1:]
for chunk in chunks:
    header, content = chunk.split("\n", 1)
    if header.strip() == marker:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        sys.exit(0)
sys.exit(1)
PY
}

decode_env "services/auth/.env"        "$TMP_SSH/services/auth/.env"
decode_env "services/annotation/.env"  "$TMP_SSH/services/annotation/.env"
decode_env "services/recognition/.env" "$TMP_SSH/services/recognition/.env"

# ---------- 上传 .env 到服务器 ----------
echo "==> 上传 .env 到 $SSH_DEST:/tmp"
scp "${SSH_OPTS[@]}" \
    "$TMP_SSH/services/auth/.env"       "$SSH_DEST:/tmp/ai-auth.env" \
    "$TMP_SSH/services/annotation/.env" "$SSH_DEST:/tmp/ai-annotation.env" \
    "$TMP_SSH/services/recognition/.env" "$SSH_DEST:/tmp/ai-recognition.env"

# ---------- 生成远程部署脚本 ----------
REMOTE_SCRIPT="$TMP_SSH/remote-deploy.sh"
cat >"$REMOTE_SCRIPT" <<'REMOTE_EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_PATH="$(printf '%s' "$DEPLOY_PATH_B64" | base64 -d)"
DEPLOY_ORIGIN="$(printf '%s' "$DEPLOY_ORIGIN_B64" | base64 -d)"
DEPLOY_BRANCH="$(printf '%s' "$DEPLOY_BRANCH_B64" | base64 -d)"
IMAGE_TAG="$(printf '%s' "$IMAGE_TAG_B64" | base64 -d)"

if [[ ! -d "$DEPLOY_PATH/.git" ]]; then
    echo "error: $DEPLOY_PATH 不是 git 仓库。请先在服务器执行 git clone。" >&2
    exit 1
fi

# ---------- 拉取最新代码 ----------
cd "$DEPLOY_PATH"
echo "==> git pull $DEPLOY_BRANCH"
git fetch origin "$DEPLOY_BRANCH"
git checkout -f "$DEPLOY_BRANCH"
git reset --hard "origin/$DEPLOY_BRANCH"

# ---------- 放置三个服务的 .env ----------
echo "==> 放置 .env"
mkdir -p "$DEPLOY_PATH/services/auth" "$DEPLOY_PATH/services/annotation" "$DEPLOY_PATH/services/recognition"
mv -f /tmp/ai-auth.env        "$DEPLOY_PATH/services/auth/.env"
mv -f /tmp/ai-annotation.env  "$DEPLOY_PATH/services/annotation/.env"
mv -f /tmp/ai-recognition.env "$DEPLOY_PATH/services/recognition/.env"

# ---------- 确保 server.env 存在并注入业务 Key ----------
mkdir -p "$DEPLOY_PATH/.local"
if [[ ! -f "$DEPLOY_PATH/.local/server.env" ]]; then
    echo "==> 首次部署，生成 .local/server.env"
    (cd "$DEPLOY_PATH" && bash scripts/server-local.sh init --origin "$DEPLOY_ORIGIN")
fi

set_key() {
    local key="$1"
    local value="$2"
    local f="$DEPLOY_PATH/.local/server.env"
    if [[ -z "$value" ]]; then
        return
    fi
    if grep -q "^$key=" "$f"; then
        sed -i "s|^$key=.*|$key=$value|" "$f"
    else
        printf '%s=%s\n' "$key" "$value" >>"$f"
    fi
}

AGENT_API_KEY="$(sed -n 's/^AGENT_API_KEY=//p' "$DEPLOY_PATH/services/annotation/.env" | tail -n 1)"
QWEN_API_KEY="$(sed -n 's/^QWEN_API_KEY=//p' "$DEPLOY_PATH/services/recognition/.env" | tail -n 1)"
set_key "AGENT_API_KEY" "$AGENT_API_KEY"
set_key "QWEN_API_KEY" "$QWEN_API_KEY"

# ---------- 本地构建并启动 ----------
echo "==> 服务器本地构建镜像并启动服务"
cd "$DEPLOY_PATH"
bash scripts/server-local.sh up --origin "$DEPLOY_ORIGIN" --tag "$IMAGE_TAG"

echo "==> 部署完成"
REMOTE_EOF

# ---------- 上传并执行远程脚本 ----------
echo "==> 在服务器执行部署"
scp "${SSH_OPTS[@]}" "$REMOTE_SCRIPT" "$SSH_DEST:/tmp/ai-annotation-studio-deploy.sh"
ssh "${SSH_OPTS[@]}" "$SSH_DEST" \
    "DEPLOY_PATH_B64='$(printf '%s' "$DEPLOY_PATH" | base64 -w0)' DEPLOY_ORIGIN_B64='$(printf '%s' "$DEPLOY_ORIGIN" | base64 -w0)' DEPLOY_BRANCH_B64='$(printf '%s' "$DEPLOY_BRANCH" | base64 -w0)' IMAGE_TAG_B64='$(printf '%s' "$IMAGE_TAG" | base64 -w0)' bash /tmp/ai-annotation-studio-deploy.sh"
