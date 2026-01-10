# LangGraph + Pulsing 集成示例

一行 `with_pulsing()` 让 LangGraph 获得分布式能力。

## 核心用法

```python
from pulsing.langgraph import with_pulsing

app = graph.compile()

# ✨ 一行代码实现分布式
distributed_app = with_pulsing(
    app,
    node_mapping={"llm": "langgraph_node_llm"},
    seeds=["gpu-server:8001"],
)

result = await distributed_app.ainvoke(input)
```

## 快速开始

### 单机模式

```bash
python simple.py
```

### 分布式模式

```bash
# 一键启动
./run_distributed.sh

# 或手动启动 (3 个终端)
python distributed.py worker llm 8001
python distributed.py worker tool 8002 8001
python distributed.py run
```

## 架构

```
┌─────────────────────────────────────────┐
│           Main Program                  │
│         with_pulsing(app)               │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌───────────┐          ┌───────────┐
│ LLM Worker│◄────────►│Tool Worker│
│   :8001   │  Gossip  │   :8002   │
│   (GPU)   │          │   (CPU)   │
└───────────┘          └───────────┘
```

## node_mapping

- **Key**: LangGraph 节点名称
- **Value**: Pulsing Actor 名称
- 未映射的节点本地执行
