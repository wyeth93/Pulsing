"""
LangGraph + Pulsing 分布式模式示例

演示如何用一行 with_pulsing() 让 LangGraph 获得分布式能力

Usage (3 个终端):
    # 终端 1: 启动 LLM Worker (模拟 GPU 服务器)
    python distributed.py worker llm 8001
    
    # 终端 2: 启动 Tool Worker (模拟 CPU 服务器)
    python distributed.py worker tool 8002 8001
    
    # 终端 3: 运行主程序
    python distributed.py run
"""

import asyncio
import json
import sys
from typing import TypedDict, Annotated, Literal
from operator import add

# #region agent log
LOG_PATH = "/Users/reiase/workspace/Pulsing/.cursor/debug.log"
def debug_log(hyp, loc, msg, data=None):
    import time
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps({"hypothesisId": hyp, "location": loc, "message": msg, "data": data, "timestamp": int(time.time()*1000)}) + "\n")
# #endregion


# ============================================================
# 定义状态和节点 (与 simple.py 完全相同)
# ============================================================

class AgentState(TypedDict):
    """Agent 状态"""
    messages: Annotated[list, add]
    next_step: str


def llm_node(state: AgentState) -> AgentState:
    """
    LLM 节点 - 模拟 LLM 调用
    
    实际应用中这里会调用 OpenAI/Anthropic API
    适合部署在 GPU 服务器上
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else {}
    
    # 获取消息内容和角色
    content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
    role = last_msg.get("role", "") if isinstance(last_msg, dict) else ""
    
    # #region agent log
    debug_log("F", "distributed.py:llm_node", "LLM node called", {"content": content[:50], "role": role})
    # #endregion
    
    print(f"[LLM Node @ Worker] Processing: {content[:50]}... (role={role})")
    
    # 如果是 tool 返回的结果，生成最终答案
    if role == "tool":
        response = f"Based on the weather data: {content}"
        next_step = "end"
    # 如果是用户询问天气
    elif "weather" in content.lower():
        response = "I need to check the weather. Let me use the tool."
        next_step = "tool"
    else:
        response = f"Hello! I received: {content}"
        next_step = "end"
    
    print(f"[LLM Node @ Worker] Response: {response}")
    
    return {
        "messages": [{"role": "assistant", "content": response}],
        "next_step": next_step,
    }


def tool_node(state: AgentState) -> AgentState:
    """
    Tool 节点 - 模拟工具调用
    
    实际应用中这里会调用外部 API
    适合部署在普通 CPU 服务器上
    """
    # #region agent log
    debug_log("G", "distributed.py:tool_node", "Tool node called")
    # #endregion
    
    print("[Tool Node @ Worker] Calling weather API...")
    
    tool_result = "The weather is sunny, 25°C."
    print(f"[Tool Node @ Worker] Result: {tool_result}")
    
    return {
        "messages": [{"role": "tool", "content": tool_result}],
        "next_step": "llm",
    }


def should_continue(state: AgentState) -> Literal["tool", "end"]:
    """条件边"""
    return state.get("next_step", "end")


def build_graph():
    """构建 LangGraph 图"""
    from langgraph.graph import StateGraph, END
    
    graph = StateGraph(AgentState)
    graph.add_node("llm", llm_node)
    graph.add_node("tool", tool_node)
    graph.set_entry_point("llm")
    graph.add_conditional_edges("llm", should_continue, {"tool": "tool", "end": END})
    graph.add_edge("tool", "llm")
    
    return graph.compile()


# ============================================================
# 分布式运行
# ============================================================

async def run_distributed():
    """
    分布式模式主程序
    
    LLM 和 Tool 节点在不同机器上执行
    """
    print("=" * 60)
    print("LangGraph + Pulsing 分布式模式")
    print("=" * 60)
    
    # #region agent log
    debug_log("H", "distributed.py:run_distributed:start", "Starting distributed mode")
    # #endregion
    
    from pulsing.langgraph import with_pulsing
    
    app = build_graph()
    
    # ✨ 核心: 一行代码实现分布式
    distributed_app = with_pulsing(
        app,
        node_mapping={
            "llm": "langgraph_node_llm",    # LLM 节点 → llm worker
            "tool": "langgraph_node_tool",  # Tool 节点 → tool worker
        },
        seeds=["127.0.0.1:8001", "127.0.0.1:8002"],
    )
    
    # #region agent log
    debug_log("H", "distributed.py:run_distributed:wrapped", "with_pulsing called", {"node_mapping": distributed_app._node_mapping})
    # #endregion
    
    print("\n等待连接到集群...")
    await asyncio.sleep(2)
    
    # 测试: 天气查询 (会触发 LLM → Tool → LLM 的调用链)
    print("\n--- Test: Weather query (distributed) ---")
    print("Request: What's the weather?")
    print("-" * 40)
    
    try:
        result = await distributed_app.ainvoke({
            "messages": [{"role": "user", "content": "What's the weather?"}],
            "next_step": "",
        })
        # #region agent log
        debug_log("H", "distributed.py:run_distributed:success", "ainvoke succeeded", {"result_keys": list(result.keys())})
        # #endregion
    except Exception as e:
        # #region agent log
        debug_log("H", "distributed.py:run_distributed:error", "ainvoke failed", {"error": str(e), "type": type(e).__name__})
        # #endregion
        raise
    
    print("-" * 40)
    print(f"Final messages count: {len(result['messages'])}")
    
    await distributed_app.close()
    print("\n✅ Distributed execution completed!")


async def run_worker(node_name: str, port: int, seed_port: int | None = None):
    """启动 Worker 节点"""
    from pulsing.langgraph import start_worker
    
    node_funcs = {
        "llm": llm_node,
        "tool": tool_node,
    }
    
    if node_name not in node_funcs:
        print(f"Unknown node: {node_name}")
        print(f"Available: {list(node_funcs.keys())}")
        return
    
    seeds = [f"127.0.0.1:{seed_port}"] if seed_port else []
    
    print("=" * 60)
    print(f"{node_name.upper()} Worker")
    print(f"Port: {port}")
    print(f"Seeds: {seeds or '(seed node)'}")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")
    
    await start_worker(
        node_name,
        node_funcs[node_name],
        addr=f"0.0.0.0:{port}",
        seeds=seeds,
    )


# ============================================================
# 主程序
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python distributed.py run                    # 运行分布式主程序")
        print("  python distributed.py worker llm 8001        # 启动 LLM worker")
        print("  python distributed.py worker tool 8002 8001  # 启动 Tool worker")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "run":
        asyncio.run(run_distributed())
    
    elif cmd == "worker":
        if len(sys.argv) < 4:
            print("Usage: python distributed.py worker <node_name> <port> [seed_port]")
            return
        
        node_name = sys.argv[2]
        port = int(sys.argv[3])
        seed_port = int(sys.argv[4]) if len(sys.argv) > 4 else None
        
        asyncio.run(run_worker(node_name, port, seed_port))
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
