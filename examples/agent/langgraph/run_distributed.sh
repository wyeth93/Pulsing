#!/bin/bash
#
# LangGraph + Pulsing 分布式启动脚本
#
# Usage:
#   ./run_distributed.sh              # 启动完整分布式流程
#   ./run_distributed.sh workers      # 只启动 Workers (后台)
#   ./run_distributed.sh run          # 只运行主程序 (需要 Workers 已启动)
#   ./run_distributed.sh stop         # 停止所有 Workers
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
LLM_PORT=8001
TOOL_PORT=8002

# Python 命令 (支持 pyenv)
if command -v pyenv &> /dev/null; then
    PYTHON="pyenv exec python"
else
    PYTHON="python3"
fi

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}=============================================="
    echo "LangGraph + Pulsing 分布式模式"
    echo "==============================================${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

start_workers() {
    print_header
    print_info "Starting Workers..."
    echo ""
    
    # 检查端口是否已被占用
    if lsof -i:$LLM_PORT >/dev/null 2>&1; then
        print_error "Port $LLM_PORT is already in use"
        print_info "Run './run_distributed.sh stop' to stop existing workers"
        exit 1
    fi
    
    # 启动 LLM Worker
    echo -e "${YELLOW}[1/2]${NC} Starting LLM Worker on port $LLM_PORT..."
    python distributed.py worker llm $LLM_PORT > /tmp/langgraph_llm.log 2>&1 &
    LLM_PID=$!
    echo $LLM_PID > /tmp/langgraph_llm.pid
    sleep 2
    
    if ps -p $LLM_PID > /dev/null 2>&1; then
        print_status "LLM Worker started (PID: $LLM_PID)"
    else
        print_error "LLM Worker failed to start"
        cat /tmp/langgraph_llm.log
        exit 1
    fi
    
    # 启动 Tool Worker
    echo -e "${YELLOW}[2/2]${NC} Starting Tool Worker on port $TOOL_PORT..."
    python distributed.py worker tool $TOOL_PORT $LLM_PORT > /tmp/langgraph_tool.log 2>&1 &
    TOOL_PID=$!
    echo $TOOL_PID > /tmp/langgraph_tool.pid
    sleep 2
    
    if ps -p $TOOL_PID > /dev/null 2>&1; then
        print_status "Tool Worker started (PID: $TOOL_PID)"
    else
        print_error "Tool Worker failed to start"
        cat /tmp/langgraph_tool.log
        exit 1
    fi
    
    echo ""
    print_status "All workers started!"
    echo ""
    echo "  LLM Worker:  localhost:$LLM_PORT (PID: $LLM_PID)"
    echo "  Tool Worker: localhost:$TOOL_PORT (PID: $TOOL_PID)"
    echo ""
    echo "  Logs:"
    echo "    - LLM:  /tmp/langgraph_llm.log"
    echo "    - Tool: /tmp/langgraph_tool.log"
    echo ""
}

stop_workers() {
    print_header
    print_info "Stopping Workers..."
    echo ""
    
    stopped=0
    
    if [ -f /tmp/langgraph_llm.pid ]; then
        LLM_PID=$(cat /tmp/langgraph_llm.pid)
        if ps -p $LLM_PID > /dev/null 2>&1; then
            kill $LLM_PID 2>/dev/null || true
            print_status "LLM Worker stopped (PID: $LLM_PID)"
            stopped=1
        fi
        rm -f /tmp/langgraph_llm.pid
    fi
    
    if [ -f /tmp/langgraph_tool.pid ]; then
        TOOL_PID=$(cat /tmp/langgraph_tool.pid)
        if ps -p $TOOL_PID > /dev/null 2>&1; then
            kill $TOOL_PID 2>/dev/null || true
            print_status "Tool Worker stopped (PID: $TOOL_PID)"
            stopped=1
        fi
        rm -f /tmp/langgraph_tool.pid
    fi
    
    # 备用方式：通过进程名查找
    pkill -f "distributed.py worker" 2>/dev/null && stopped=1 || true
    
    if [ $stopped -eq 0 ]; then
        print_info "No workers running"
    else
        echo ""
        print_status "All workers stopped!"
    fi
}

run_main() {
    print_header
    
    # 检查 Workers 是否在运行
    if ! lsof -i:$LLM_PORT >/dev/null 2>&1; then
        print_error "LLM Worker not running on port $LLM_PORT"
        print_info "Run './run_distributed.sh workers' first"
        exit 1
    fi
    
    if ! lsof -i:$TOOL_PORT >/dev/null 2>&1; then
        print_error "Tool Worker not running on port $TOOL_PORT"
        print_info "Run './run_distributed.sh workers' first"
        exit 1
    fi
    
    print_status "Workers detected, running main program..."
    echo ""
    
    python distributed.py run
}

run_all() {
    # 清理函数
    cleanup() {
        echo ""
        print_info "Shutting down..."
        stop_workers
    }
    trap cleanup EXIT INT TERM
    
    # 启动 Workers
    start_workers
    
    # 等待 Workers 完全就绪
    print_info "Waiting for cluster to stabilize..."
    sleep 2
    
    # 运行主程序
    echo ""
    echo -e "${BLUE}----------------------------------------------"
    echo "Running Main Program"
    echo "----------------------------------------------${NC}"
    echo ""
    
    python distributed.py run
    
    echo ""
    print_status "Demo completed!"
}

show_help() {
    print_header
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  (no args)    启动完整分布式流程 (Workers + Main)"
    echo "  workers      只启动 Workers (后台运行)"
    echo "  run          只运行主程序 (需要 Workers 已启动)"
    echo "  stop         停止所有 Workers"
    echo "  help         显示帮助"
    echo ""
    echo "Architecture:"
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │              Main Program                   │"
    echo "  │         (with_pulsing wrapper)              │"
    echo "  └─────────────┬───────────────┬───────────────┘"
    echo "                │               │"
    echo "        ┌───────▼───────┐ ┌─────▼───────┐"
    echo "        │  LLM Worker   │ │ Tool Worker │"
    echo "        │   :$LLM_PORT        │ │   :$TOOL_PORT       │"
    echo "        │  (GPU Server) │ │ (CPU Server)│"
    echo "        └───────────────┘ └─────────────┘"
    echo ""
}

# 主逻辑
case "${1:-}" in
    workers)
        start_workers
        ;;
    run)
        run_main
        ;;
    stop)
        stop_workers
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        run_all
        ;;
esac
