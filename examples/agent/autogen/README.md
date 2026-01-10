# AutoGen + Pulsing 示例

本目录包含使用 Pulsing 作为 AutoGen 运行时的示例代码。

## 概述

`PulsingRuntime` 完全兼容 AutoGen 的 `AgentRuntime` 协议，可以直接替代：
- `SingleThreadedAgentRuntime` (单机模式)
- `GrpcWorkerAgentRuntime` (分布式模式)

关键优势：**单机和分布式使用同一套 API，只需改配置**

## 示例文件

### simple.py - 单机模式

演示 PulsingRuntime 与 AutoGen SingleThreadedAgentRuntime 的兼容性。

```bash
# 运行
python simple.py
```

输出会显示两个运行时的结果对比，验证行为一致。

### distributed.py - 分布式模式

演示多节点分布式部署。

```bash
# 终端 1: 启动 Writer Agent
python distributed.py writer

# 终端 2: 启动 Editor Agent
python distributed.py editor

# 终端 3: 启动 Manager 发起对话
python distributed.py manager
```

或者单机测试所有功能：

```bash
python distributed.py standalone
```

## 使用方式

### 单机模式

```python
from pulsing.autogen import PulsingRuntime

# 创建运行时 - 单机模式
runtime = PulsingRuntime()
await runtime.start()

# 与 AutoGen 完全一样的使用方式
await runtime.register_factory("my_agent", lambda: MyAgent())
response = await runtime.send_message(msg, recipient=AgentId("my_agent", "default"))
```

### 分布式模式

```python
from pulsing.autogen import PulsingRuntime

# 节点 1: 第一个节点
runtime = PulsingRuntime(addr="0.0.0.0:8001")

# 节点 2: 加入集群
runtime = PulsingRuntime(
    addr="0.0.0.0:8002",
    seeds=["node1:8001"]
)

# 使用方式完全一样！
await runtime.start()
```

## 对比优势

| 特性 | AutoGen SingleThreaded | AutoGen gRPC | Pulsing Runtime |
|------|----------------------|--------------|-----------------|
| 单机开发 | ✅ | ❌ 需要 Host | ✅ |
| 分布式部署 | ❌ | ✅ 需要配置 | ✅ 同一 API |
| 中央协调器 | N/A | ✅ 必须 | ❌ 不需要 |
| 自动发现 | N/A | ❌ | ✅ Gossip |
| 故障转移 | N/A | ❌ | ✅ Circuit Breaker |
| K8s 部署 | N/A | 复杂 | ✅ 简单 |

## 依赖安装

```bash
# 安装 Pulsing
pip install pulsing

# (可选) 安装 AutoGen 用于对比测试
pip install autogen-core
```
