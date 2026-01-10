#!/bin/bash
# LangGraph + Pulsing 分布式启动脚本
# Usage: ./run_distributed.sh [workers|run|stop|help]

set -e
cd "$(dirname "$0")"

LLM_PORT=8001
TOOL_PORT=8002

# 初始化 pyenv
command -v pyenv &>/dev/null && eval "$(pyenv init -)"
PYTHON="${PYTHON:-python}"

case "${1:-}" in
    workers)
        echo "Starting Workers..."
        $PYTHON distributed.py worker llm $LLM_PORT > /tmp/langgraph_llm.log 2>&1 &
        echo $! > /tmp/langgraph_llm.pid
        sleep 2
        $PYTHON distributed.py worker tool $TOOL_PORT $LLM_PORT > /tmp/langgraph_tool.log 2>&1 &
        echo $! > /tmp/langgraph_tool.pid
        sleep 1
        echo "Workers started: LLM(:$LLM_PORT) Tool(:$TOOL_PORT)"
        ;;
    run)
        $PYTHON distributed.py run
        ;;
    stop)
        [ -f /tmp/langgraph_llm.pid ] && kill $(cat /tmp/langgraph_llm.pid) 2>/dev/null && rm /tmp/langgraph_llm.pid
        [ -f /tmp/langgraph_tool.pid ] && kill $(cat /tmp/langgraph_tool.pid) 2>/dev/null && rm /tmp/langgraph_tool.pid
        pkill -f "distributed.py worker" 2>/dev/null || true
        echo "Workers stopped"
        ;;
    help|-h)
        echo "Usage: $0 [command]"
        echo "  (none)   Full demo (workers + run)"
        echo "  workers  Start workers only"
        echo "  run      Run main program"
        echo "  stop     Stop workers"
        ;;
    *)
        trap '$0 stop' EXIT INT TERM
        $0 workers
        sleep 2
        $0 run
        ;;
esac
