#!/bin/bash
#
# 分布式 Agent 启动脚本
#
# Usage:
#   ./run_distributed.sh              # 使用 torchrun 启动 3 个进程
#   ./run_distributed.sh --manual     # 手动模式 (在后台启动各进程)
#   ./run_distributed.sh --nproc 5    # 指定进程数
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
NPROC=3
MODE="torchrun"
MASTER_PORT=18000

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --manual)
            MODE="manual"
            shift
            ;;
        --nproc)
            NPROC="$2"
            shift 2
            ;;
        --port)
            MASTER_PORT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --manual       手动模式 (后台启动各进程)"
            echo "  --nproc N      进程数 (默认: 3)"
            echo "  --port PORT    基础端口 (默认: 18000)"
            echo "  -h, --help     显示帮助"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=============================================="
echo "Pulsing Distributed Agent Demo"
echo "=============================================="
echo "Mode: $MODE"
echo "Processes: $NPROC"
echo "Base Port: $MASTER_PORT"
echo "=============================================="
echo ""

if [ "$MODE" = "torchrun" ]; then
    # 使用 torchrun 启动
    echo "Starting with torchrun..."
    echo ""
    
    MASTER_PORT=$MASTER_PORT torchrun \
        --nproc_per_node=$NPROC \
        --master_addr=127.0.0.1 \
        --master_port=$MASTER_PORT \
        distributed.py
    
else
    # 手动模式：后台启动各进程
    echo "Starting in manual mode..."
    echo ""
    
    # 清理函数
    cleanup() {
        echo ""
        echo "Stopping all processes..."
        kill $(jobs -p) 2>/dev/null || true
        wait 2>/dev/null || true
        echo "Done."
    }
    trap cleanup EXIT INT TERM
    
    # 启动 Writer (rank 0)
    echo "[1/$NPROC] Starting Writer..."
    python distributed.py writer &
    WRITER_PID=$!
    sleep 1
    
    # 启动 Editor (rank 1)
    echo "[2/$NPROC] Starting Editor..."
    python distributed.py editor &
    EDITOR_PID=$!
    sleep 1
    
    # 启动 Manager (rank 2) - 前台运行
    echo "[3/$NPROC] Starting Manager..."
    python distributed.py manager
    
    # Manager 完成后等待一下让输出显示
    sleep 1
fi

echo ""
echo "=============================================="
echo "Demo completed!"
echo "=============================================="
