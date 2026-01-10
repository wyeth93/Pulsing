# LangGraph + Pulsing 集成示例

通过 `with_pulsing()` 一行代码，让 LangGraph 获得分布式执行能力。

## 核心理念

**不是替代，而是增强。** 用户的 LangGraph 代码几乎不需要改动。

```python
from langgraph.graph import StateGraph
from pulsing.langgraph import with_pulsing

# 原有 LangGraph 代码完全不变
graph = StateGraph(MyState)
graph.add_node("llm", llm_node)
graph.add_node("tool", tool_node)
app = graph.compile()

# ✨ 一行代码实现分布式
distributed_app = with_pulsing(
    app,
    node_mapping={
        "llm": "node:llm",    # LLM 节点 → GPU 集群
        "tool": "node:tool",  # Tool 节点 → CPU 集群
    },
    seeds=["gpu-server:8001"],
)

# 使用方式完全相同
result = await distributed_app.ainvoke(input)
```

## 示例文件

| 文件 | 说明 |
|------|------|
| `simple.py` | 单机模式，验证 API 兼容性 |
| `distributed.py` | 分布式模式，多节点协作 |

## 快速开始

### 单机模式

```bash
# 安装依赖
pip install langgraph

# 运行
python simple.py
```

### 分布式模式

需要 3 个终端：

```bash
# 终端 1: 启动 LLM Worker (模拟 GPU 服务器)
python distributed.py worker llm 8001

# 终端 2: 启动 Tool Worker (模拟 CPU 服务器)
python distributed.py worker tool 8002 8001

# 终端 3: 运行主程序
python distributed.py run
```

## 架构

```
                    ┌─────────────────┐
                    │   Main Program  │
                    │  with_pulsing() │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ LLM Worker  │   │ Tool Worker │   │   ...更多   │
    │  (GPU)      │◄─►│   (CPU)     │◄─►│   Worker    │
    └─────────────┘   └─────────────┘   └─────────────┘
           │                 │                 │
           └─────────────────┴─────────────────┘
                   Pulsing Gossip Protocol
```

## node_mapping 说明

`node_mapping` 定义了哪些节点需要分布式执行：

```python
node_mapping={
    "llm": "node:llm",      # LangGraph 的 "llm" 节点 → Pulsing 的 "node:llm" Actor
    "tool": "node:tool",    # LangGraph 的 "tool" 节点 → Pulsing 的 "node:tool" Actor
}
```

- **Key**: LangGraph 中的节点名称
- **Value**: Pulsing 集群中的 Actor 名称
- **未映射的节点**: 在本地执行

## 典型场景

1. **LLM + RAG 分离**
   - LLM 节点 → GPU 服务器
   - RAG 检索节点 → 高内存服务器

2. **多模型协作**
   - 不同 LLM 节点 → 不同模型服务

3. **工具调用隔离**
   - 危险工具节点 → 沙箱环境

## 注意事项

1. 节点函数的输入/输出需要可序列化 (Pulsing 使用 pickle)
2. 确保所有 Worker 都已启动后再运行主程序
3. 分布式模式下，节点间通信有网络延迟
