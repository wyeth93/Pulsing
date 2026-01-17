# Pulsing

[![CI](https://github.com/reiase/pulsing/actions/workflows/ci.yml/badge.svg)](https://github.com/reiase/pulsing/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)

**[中文文档](README.zh.md)**

**Lightweight distributed framework designed for high-performance AI applications.**

Zero external dependencies, one line of code for distributed deployment — seamlessly scale your AI applications from a single machine to a cluster.

```
┌─────────────────────────────────────────────────────────────┐
│                      Your AI Application                     │
│            Multi-Agent / LLM Serving / RAG Pipeline          │
└─────────────────────────────────────────────────────────────┘
                              │
                    Pulsing Actor System
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  Node 1  │◄──────►│  Node 2  │◄──────►│  Node 3  │
    │   GPU    │        │   CPU    │        │   CPU    │
    └──────────┘        └──────────┘        └──────────┘
```

## 🚀 Get Started in 5 Minutes

### Installation

```bash
pip install pulsing
```

### Your First Multi-Agent Application

```python
import asyncio
from pulsing.actor import remote, resolve
from pulsing.agent import runtime

@remote
class Greeter:
    def __init__(self, display_name: str):
        self.display_name = display_name
    
    def greet(self, message: str) -> str:
        return f"[{self.display_name}] Received: {message}"
    
    async def chat_with(self, peer_name: str, message: str) -> str:
        peer = await resolve(peer_name)
        return await peer.greet(f"From {self.display_name}: {message}")

async def main():
    async with runtime():
        # Create two agents
        alice = await Greeter.spawn(display_name="Alice", name="alice")
        bob = await Greeter.spawn(display_name="Bob", name="bob")
        
        # Agent communication
        reply = await alice.chat_with("bob", "Hello!")
        print(reply)  # [Bob] Received: From Alice: Hello!

asyncio.run(main())
```

**That's it!** `@remote` turns a regular class into a distributed Actor, and `resolve()` enables agents to discover and communicate with each other.

## 💡 I want to...

| Scenario | Example | Description |
|----------|---------|-------------|
| **Quick start** | `examples/quickstart/` | Get started in 10 lines |
| **Multi-Agent collaboration** | `examples/agent/pulsing/` | AI debate, brainstorming, role-playing |
| **Distributed LLM inference** | `pulsing actor router/vllm` | GPU cluster inference service |
| **Integrate AutoGen** | `examples/agent/autogen/` | One line to go distributed |
| **Integrate LangGraph** | `examples/agent/langgraph/` | Execute graphs across nodes |

## 🎯 Core Capabilities

### 1. Multi-Agent Collaboration

Multiple AI Agents working in parallel and communicating:

```python
from pulsing.agent import agent, runtime, llm

@agent(role="Researcher", goal="Deep analysis")
class Researcher:
    async def analyze(self, topic: str) -> str:
        client = await llm()
        return await client.ainvoke(f"Analyze: {topic}")

@agent(role="Reviewer", goal="Evaluate proposals")  
class Reviewer:
    async def review(self, proposal: str) -> str:
        client = await llm()
        return await client.ainvoke(f"Review: {proposal}")

async with runtime():
    researcher = await Researcher.spawn(name="researcher")
    reviewer = await Reviewer.spawn(name="reviewer")
    
    # Parallel work and collaboration
    analysis = await researcher.analyze("AI trends")
    feedback = await reviewer.review(analysis)
```

```bash
# Run MBTI personality discussion example
python examples/agent/pulsing/mbti_discussion.py --mock --group-size 6

# Run parallel idea generation example
python examples/agent/pulsing/parallel_ideas_async.py --mock --n-ideas 5
```

### 2. One Line to Distributed

Develop locally, scale seamlessly to clusters:

```python
# Standalone mode (development)
async with runtime():
    agent = await MyAgent.spawn(name="agent")

# Distributed mode (production) — just add address
async with runtime(addr="0.0.0.0:8001"):
    agent = await MyAgent.spawn(name="agent")

# Other nodes auto-discover
async with runtime(addr="0.0.0.0:8002", seeds=["node1:8001"]):
    agent = await resolve("agent")  # Cross-node transparent call
```

### 3. LLM Inference Service

Out-of-the-box GPU cluster inference:

```bash
# Start Router (OpenAI-compatible API)
pulsing actor router --addr 0.0.0.0:8000 --http_port 8080 --model_name my-llm

# Start vLLM Worker (can have multiple)
pulsing actor vllm --model Qwen/Qwen2.5-0.5B --addr 0.0.0.0:8002 --seeds 127.0.0.1:8000

# Test
curl http://localhost:8080/v1/chat/completions \
  -d '{"model": "my-llm", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 4. Agent Framework Integration

Have existing AutoGen/LangGraph code? One-line migration:

```python
# AutoGen: Replace runtime
from pulsing.autogen import PulsingRuntime
runtime = PulsingRuntime(addr="0.0.0.0:8000")

# LangGraph: Wrap the graph
from pulsing.langgraph import with_pulsing
distributed_app = with_pulsing(app, seeds=["gpu-server:8001"])
```

## 📚 Example Guide

```
examples/
├── quickstart/              # ⭐ 5-minute quickstart
│   └── hello_agent.py       #    First Agent
├── agent/
│   ├── pulsing/             # ⭐⭐ Multi-Agent apps
│   │   ├── mbti_discussion.py      # MBTI personality discussion
│   │   └── parallel_ideas_async.py # Parallel idea generation
│   ├── autogen/             # AutoGen integration
│   └── langgraph/           # LangGraph integration
├── python/                  # ⭐⭐ Basic examples
│   ├── ping_pong.py         #    Actor basics
│   ├── cluster.py           #    Cluster communication
│   └── ...
└── rust/                    # Rust examples
```

## 🔧 Technical Features

- **Zero external dependencies**: Pure Rust + Tokio, no NATS/etcd/Redis needed
- **Gossip protocol**: Built-in SWIM protocol for node discovery and failure detection
- **Location transparency**: Same API for local and remote Actors
- **Streaming messages**: Native support for streaming requests/responses (LLM-ready)
- **Type safety**: Rust Behavior API provides compile-time message type checking

## 📦 Project Structure

```
Pulsing/
├── crates/                   # Rust core
│   ├── pulsing-actor/        #   Actor System
│   └── pulsing-py/           #   Python bindings
├── python/pulsing/           # Python package
│   ├── actor/                #   Actor API
│   ├── agent/                #   Agent toolkit
│   ├── autogen/              #   AutoGen integration
│   └── langgraph/            #   LangGraph integration
├── examples/                 # Example code
└── docs/                     # Documentation
```

## 🛠️ Development

```bash
# Development build
maturin develop

# Run tests
pytest tests/python/
cargo test --workspace
```

## 📄 License

Apache-2.0
