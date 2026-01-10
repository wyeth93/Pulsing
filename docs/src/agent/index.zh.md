# Agent 框架集成

Pulsing 原生支持主流 Agent 框架，让您的应用轻松从单进程扩展到分布式集群。

## 设计理念

**不替代，而是增强。**

- 用户代码几乎无需改动
- API 与原框架完全兼容
- 一行代码实现分布式

## 支持的框架

| 框架 | 集成方式 | 说明 |
|------|----------|------|
| [AutoGen](autogen.zh.md) | `PulsingRuntime` | 替代默认运行时 |
| [LangGraph](langgraph.zh.md) | `with_pulsing()` | 包装编译后的图 |

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    您的 Agent 代码                          │
│              (AutoGen / LangGraph / ...)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Pulsing 集成层                           │
│          PulsingRuntime / with_pulsing()                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Pulsing Actor System                       │
│       Gossip 协议 │ 位置透明 │ 流式消息                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  节点 1  │◄─►│  节点 2  │◄─►│  节点 3  │
    │   GPU    │   │   CPU    │   │   CPU    │
    └──────────┘   └──────────┘   └──────────┘
```

## 快速对比

### AutoGen

```python
from pulsing.autogen import PulsingRuntime

# 替代 SingleThreadedAgentRuntime
runtime = PulsingRuntime(addr="0.0.0.0:8000")
await runtime.start()
await runtime.register_factory("agent", lambda: MyAgent())
```

### LangGraph

```python
from pulsing.langgraph import with_pulsing

app = graph.compile()
distributed_app = with_pulsing(
    app,
    node_mapping={"llm": "langgraph_node_llm"},
    seeds=["gpu-server:8001"],
)
```

## 典型场景

1. **LLM + Tool 分离** - LLM 在 GPU，工具在 CPU
2. **多 Agent 协作** - Agent 分布在不同节点
3. **弹性扩缩容** - 无需修改代码即可增删节点

## 运行示例

```bash
# AutoGen
cd examples/agent/autogen && ./run_distributed.sh

# LangGraph
cd examples/agent/langgraph && ./run_distributed.sh
```
