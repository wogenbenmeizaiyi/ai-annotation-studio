#!/usr/bin/env bash
# 在 GitLab CI 中运行（无容器镜像仓库方案）：
#   SSH 到服务器，把 ENV_BUNDLE_B64 和部署参数传过去，
#   服务器上解码还原三个服务的 .env -> git pull 最新代码
#   -> 本地构建 6 个业务镜像并用 compose 启动（scripts/server-local.sh）。
#
# 需要的前置（在 .gitlab-ci.yml 的 before_script 中准备 ~/.ssh/id_ed25519）：
#   DEPLOY_KEY                服务器 SSH 私钥
#   ENV_BUNDLE_B64            三个服务 .env 的 base64（scripts/env-bundle.ps1 生成）
#   DEPLOY_HOST / DEPLOY_USER / DEPLOY_PATH / DEPLOY_ORIGIN / DEPLOY_BRANCH

set -Eeuo pipefail

DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST 未设置}"
DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/ai-annotation-studio}"
DEPLOY_ORIGIN="${DEPLOY_ORIGIN:-http://$DEPLOY_HOST:7280}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
IMAGE_TAG="${IMAGE_TAG:-local}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"

ENV_BUNDLE_B64="${ENV_BUNDLE_B64:?ENV_BUNDLE_B64 未设置}"

SSH_OPTS=(
    -i "${DEPLOY_KEY_FILE:-$HOME/.ssh/id_ed25519}"
    -p "$DEPLOY_PORT"
    -o IdentitiesOnly=yes
    -o StrictHostKeyChecking=accept-new
    -o UserKnownHostsFile="$HOME/.ssh/known_hosts"
    -o ConnectTimeout=20
)
SSH_DEST="$DEPLOY_USER@$DEPLOY_HOST"

# ---------- 生成远程脚本（heredoc 内联，不传文件） ----------
REMOTE_SCRIPT="$(
cat <<'REMOTE_EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_PATH="$DEPLOY_PATH"
DEPLOY_ORIGIN="$DEPLOY_ORIGIN"
DEPLOY_BRANCH="$DEPLOY_BRANCH"
IMAGE_TAG="$IMAGE_TAG"
ENV_BUNDLE_B64="$ENV_BUNDLE_B64"

# ---------- 解码三个服务的 .env ----------
decode_env() {
    local marker="$1"
    local out="$2"
    mkdir -p "$(dirname "$out")"
    python3 - "$marker" "$out" <<'PY'
import base64, os, sys
marker, out = sys.argv[1], sys.argv[2]
text = base64.b64decode(os.environ["ENV_BUNDLE_B64"]).decode("utf-8")
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

decode_env "services/auth/.env"        "$DEPLOY_PATH/services/auth/.env"
decode_env "services/annotation/.env"  "$DEPLOY_PATH/services/annotation/.env"
decode_env "services/recognition/.env" "$DEPLOY_PATH/services/recognition/.env"
echo "==> .env 已还原"

# ---------- 拉取最新代码 ----------
if [[ ! -d "$DEPLOY_PATH/.git" ]]; then
    echo "error: $DEPLOY_PATH 不是 git 仓库。请先在服务器执行 git clone。" >&2
    exit 1
fi
cd "$DEPLOY_PATH"
echo "==> git pull $DEPLOY_BRANCH"
git fetch origin "$DEPLOY_BRANCH"
git checkout -f "$DEPLOY_BRANCH"
git reset --hard "origin/$DEPLOY_BRANCH"

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
)"

echo "==> 在服务器执行部署"
ssh "${SSH_OPTS[@]}" "$SSH_DEST" \
    "DEPLOY_PATH='$DEPLOY_PATH' DEPLOY_ORIGIN='$DEPLOY_ORIGIN' DEPLOY_BRANCH='$DEPLOY_BRANCH' IMAGE_TAG='$IMAGE_TAG' ENV_BUNDLE_B64='$ENV_BUNDLE_B64' bash -s" <<<"$REMOTE_SCRIPT"
