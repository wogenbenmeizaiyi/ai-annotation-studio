#!/usr/bin/env bash
# ===========================================
# AI Image Recognition Server & Worker Manager
# ===========================================
# Usage: bash start.sh start | stop
# ===========================================

UVICORN_APP="api_server:app"
UVICORN_PORT="7987"
GPU_CELERY_APP="worker_server_gpu.celery_app"
MULTIMODAL_CELERY_APP="worker_server_multimodal.celery_app"
LOG_DIR="logs"
PID_DIR=".pids"
export PYTHONPATH="$PWD/api/src:$PWD/worker/src:$PWD/consumer/src:$PWD/core/src:$PWD/engine/src${PYTHONPATH:+:$PYTHONPATH}"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

start() {
    # 检查 uv
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}[!] 错误: 未检测到 uv${NC}"
        exit 1
    fi

    # 检查虚拟环境
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}[!] 未检测到虚拟环境，正在安装依赖...${NC}"
        uv sync
    fi

    # 检查是否已运行
    if [ -f "$PID_DIR/api.pid" ] && kill -0 "$(cat "$PID_DIR/api.pid")" 2>/dev/null; then
        echo -e "${YELLOW}[!] FastAPI 已在运行 (PID: $(cat "$PID_DIR/api.pid"))${NC}"
        exit 1
    fi

    mkdir -p "$LOG_DIR" "$PID_DIR"

    # 1. 启动 FastAPI
    echo -e "${GREEN}[1/3] 启动 FastAPI: http://localhost:$UVICORN_PORT${NC}"
    nohup uv run uvicorn "$UVICORN_APP" \
        --host 0.0.0.0 \
        --port "$UVICORN_PORT" \
        --log-level info \
        >> "$LOG_DIR/api.log" 2>&1 &
    echo $! > "$PID_DIR/api.pid"

    sleep 2

    # 2. 启动 GPU Celery Worker
    echo -e "${GREEN}[2/3] 启动 GPU Worker (固定 YOLO/SAM 队列)${NC}"
    nohup uv run celery -A "$GPU_CELERY_APP" worker \
        --loglevel=info \
        --pool=solo \
        --concurrency=1 \
        --prefetch-multiplier=1 \
        --hostname='recognition-gpu@%h' \
        -Q "tasks.image.recognition.yolo,tasks.image.recognition.sam" \
        >> "$LOG_DIR/worker-gpu.log" 2>&1 &
    echo $! > "$PID_DIR/worker-gpu.pid"

    # 3. 启动多模态 Celery Worker
    echo -e "${GREEN}[3/3] 启动多模态 Worker (固定队列，并发: 4)${NC}"
    nohup uv run celery -A "$MULTIMODAL_CELERY_APP" worker \
        --loglevel=info \
        --pool=threads \
        --concurrency=4 \
        --hostname='recognition-multimodal@%h' \
        -Q "tasks.image.recognition.multimodal" \
        >> "$LOG_DIR/worker-multimodal.log" 2>&1 &
    echo $! > "$PID_DIR/worker-multimodal.pid"

    echo ""
    echo -e "${GREEN}[*] 服务已后台启动!${NC}"
    echo "    FastAPI PID: $(cat "$PID_DIR/api.pid") -> http://localhost:$UVICORN_PORT/docs"
    echo "    GPU Worker PID: $(cat "$PID_DIR/worker-gpu.pid")"
    echo "    Multimodal Worker PID: $(cat "$PID_DIR/worker-multimodal.pid")"
    echo -e "    日志: ${CYAN}$LOG_DIR/api.log${NC}, ${CYAN}$LOG_DIR/worker-gpu.log${NC}, ${CYAN}$LOG_DIR/worker-multimodal.log${NC}"
}

stop() {
    echo -e "${YELLOW}[*] 正在停止服务...${NC}"

    if [ -f "$PID_DIR/api.pid" ]; then
        kill "$(cat "$PID_DIR/api.pid")" 2>/dev/null
        rm -f "$PID_DIR/api.pid"
        echo -e "    FastAPI 已停止"
    else
        echo -e "    未找到 FastAPI PID"
    fi

    if [ -f "$PID_DIR/worker-gpu.pid" ]; then
        kill "$(cat "$PID_DIR/worker-gpu.pid")" 2>/dev/null
        rm -f "$PID_DIR/worker-gpu.pid"
        echo -e "    GPU Worker 已停止"
    else
        echo -e "    未找到 GPU Worker PID"
    fi

    if [ -f "$PID_DIR/worker-multimodal.pid" ]; then
        kill "$(cat "$PID_DIR/worker-multimodal.pid")" 2>/dev/null
        rm -f "$PID_DIR/worker-multimodal.pid"
        echo -e "    Multimodal Worker 已停止"
    else
        echo -e "    未找到 Multimodal Worker PID"
    fi

    echo -e "${GREEN}[*] 所有服务已停止${NC}"
}

status() {
    if [ -f "$PID_DIR/api.pid" ] && kill -0 "$(cat "$PID_DIR/api.pid")" 2>/dev/null; then
        echo -e "FastAPI: ${GREEN}运行中${NC} (PID: $(cat "$PID_DIR/api.pid"))"
    else
        echo -e "FastAPI: ${RED}已停止${NC}"
    fi

    if [ -f "$PID_DIR/worker-gpu.pid" ] && kill -0 "$(cat "$PID_DIR/worker-gpu.pid")" 2>/dev/null; then
        echo -e "GPU Worker: ${GREEN}运行中${NC} (PID: $(cat "$PID_DIR/worker-gpu.pid"))"
    else
        echo -e "GPU Worker: ${RED}已停止${NC}"
    fi

    if [ -f "$PID_DIR/worker-multimodal.pid" ] && kill -0 "$(cat "$PID_DIR/worker-multimodal.pid")" 2>/dev/null; then
        echo -e "Multimodal Worker: ${GREEN}运行中${NC} (PID: $(cat "$PID_DIR/worker-multimodal.pid"))"
    else
        echo -e "Multimodal Worker: ${RED}已停止${NC}"
    fi
}

case "$1" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    *)
        echo -e "${CYAN}Usage: bash $0 {start|stop|status}${NC}"
        exit 1
        ;;
esac
