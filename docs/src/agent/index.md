# Agent Framework Integration

Pulsing provides native support for popular agent frameworks, enabling seamless scaling from single-process to distributed clusters.

## Design Philosophy

**Enhance, not replace.**

- Your existing agent code requires minimal changes
- APIs remain fully compatible with original frameworks
- One line of code to enable distributed execution

## Supported Frameworks

| Framework | Integration | Description |
|-----------|-------------|-------------|
| [AutoGen](autogen.md) | `PulsingRuntime` | Drop-in replacement for default runtime |
| [LangGraph](langgraph.md) | `with_pulsing()` | Wrap compiled graphs |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Agent Code                          │
│              (AutoGen / LangGraph / ...)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Pulsing Integration                        │
│          PulsingRuntime / with_pulsing()                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Pulsing Actor System                       │
│     Gossip Protocol │ Location Transparency │ Streaming     │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Node 1  │◄─►│  Node 2  │◄─►│  Node 3  │
    │   GPU    │   │   CPU    │   │   CPU    │
    └──────────┘   └──────────┘   └──────────┘
```

## Quick Comparison

### AutoGen

```python
from pulsing.autogen import PulsingRuntime

# Replace SingleThreadedAgentRuntime
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

## Use Cases

1. **LLM + Tool Separation** - LLM on GPU, tools on CPU
2. **Multi-Agent Collaboration** - Agents on different nodes
3. **Elastic Scaling** - Add/remove nodes without code changes

## Running Examples

```bash
# AutoGen
cd examples/agent/autogen && ./run_distributed.sh

# LangGraph
cd examples/agent/langgraph && ./run_distributed.sh
```
