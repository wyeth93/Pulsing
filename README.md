# Pulsing

[![CI](https://github.com/reiase/pulsing/actions/workflows/ci.yml/badge.svg)](https://github.com/reiase/pulsing/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)

Pulsing 是一个轻量级分布式 Actor 框架，专为 LLM 推理服务设计。基于 Rust 和 Tokio 构建，提供高性能的异步 Actor 模型，支持集群通信和服务发现。

## 特性

- **零外部依赖**：基于 Tokio 的纯 Rust 实现，无需 NATS/etcd 等外部服务
- **Gossip 协议发现**：内置 SWIM 协议实现节点发现和故障检测
- **位置透明**：ActorRef 支持本地和远程 Actor 的统一访问
- **流式消息**：原生支持流式请求和响应
- **Agent 框架支持**：原生集成 AutoGen 和 LangGraph，轻松实现分布式 Agent
- **Python 绑定**：通过 PyO3 提供完整的 Python API

## 快速上手

### 安装

```bash
pip install pulsing
```

### 30秒入门

```python
import asyncio
from pulsing.actor import Actor, SystemConfig, create_actor_system


class PingPong(Actor):
    async def receive(self, msg):
        if msg == "ping":
            return "pong"
        return f"echo: {msg}"


async def main():
    system = await create_actor_system(SystemConfig.standalone())
    actor = await system.spawn("pingpong", PingPong())

    print(await actor.ask("ping"))   # -> pong
    print(await actor.ask("hello"))  # -> echo: hello

    await system.shutdown()


asyncio.run(main())
```

**任意 Python 对象**都可以作为消息：字符串、字典、列表、自定义类等。

### 有状态 Actor

```python
class Counter(Actor):
    def __init__(self):
        self.value = 0

    async def receive(self, msg):
        if msg == "inc":
            self.value += 1
            return self.value
        if isinstance(msg, dict) and msg.get("op") == "add":
            self.value += msg.get("n", 0)
            return {"value": self.value}
```

### 集群通信

```python
# Node 1 - 启动 seed 节点
config = SystemConfig.with_addr("0.0.0.0:8000")
system = await create_actor_system(config)
await system.spawn("worker", WorkerActor(), public=True)

# Node 2 - 加入集群
config = SystemConfig.with_addr("0.0.0.0:8001").with_seeds(["192.168.1.1:8000"])
system = await create_actor_system(config)

# 查找并调用远程 Actor（API 完全相同！）
worker = await system.resolve_named("worker")
result = await worker.ask("do_work")
```

## Agent 框架集成

Pulsing 原生支持主流 Agent 框架，**不替代，而是增强**——用户代码几乎无需改动。

### AutoGen

`PulsingRuntime` 替代 AutoGen 默认运行时，实现分布式 Agent：

```python
from pulsing.autogen import PulsingRuntime

runtime = PulsingRuntime(addr="0.0.0.0:8000")  # 分布式模式
await runtime.start()
await runtime.register_factory("agent", lambda: MyAgent())
await runtime.send_message("Hello", AgentId("agent", "default"))
```

### LangGraph

`with_pulsing()` 一行代码实现分布式：

```python
from pulsing.langgraph import with_pulsing

app = graph.compile()
distributed_app = with_pulsing(
    app,
    node_mapping={"llm": "langgraph_node_llm"},  # LLM → GPU 服务器
    seeds=["gpu-server:8001"],
)
await distributed_app.ainvoke(inputs)
```

### 运行示例

```bash
# AutoGen 分布式示例
cd examples/agent/autogen && ./run_distributed.sh

# LangGraph 分布式示例
cd examples/agent/langgraph && ./run_distributed.sh
```

## CLI 命令

Pulsing 提供基于 Actor System 的 LLM 推理服务：

```bash
# 启动 Router (OpenAI 兼容 API)
pulsing actor router --addr 0.0.0.0:8000 --http_port 8080 --model_name my-llm

# 启动 vLLM Worker
pulsing actor vllm --model Qwen/Qwen2.5-0.5B --addr 0.0.0.0:8002 --seeds 127.0.0.1:8000

# 运行基准测试
pulsing bench --tokenizer_name gpt2 --url http://localhost:8080
```

### 测试推理服务

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "my-llm", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'
```

## 项目结构

```
Pulsing/
├── crates/                   # Rust crates
│   ├── pulsing-actor/        # Actor System 核心库
│   ├── pulsing-bench/        # 性能基准测试工具
│   └── pulsing-py/           # PyO3 核心绑定
├── python/pulsing/           # Python 包
│   ├── actor/                # Actor System Python API
│   ├── actors/               # LLM serving actors
│   ├── autogen/              # AutoGen 集成 (PulsingRuntime)
│   ├── langgraph/            # LangGraph 集成 (with_pulsing)
│   └── cli/                  # 命令行工具
├── examples/
│   ├── agent/                # Agent 框架示例
│   │   ├── autogen/          # AutoGen 分布式示例
│   │   └── langgraph/        # LangGraph 分布式示例
│   └── python/               # 基础示例
└── docs/                     # 文档
```

## 构建

```bash
# 开发构建
maturin develop

# 发布构建
maturin build --release
```

## 运行测试

```bash
pytest tests/python/
cargo test --workspace
```

## 许可证

Apache-2.0
