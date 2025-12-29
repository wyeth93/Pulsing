# 快速开始

Pulsing 是一个轻量级分布式 Actor 框架，提供位置透明的消息传递、集群发现和高性能异步处理。

## 安装

```bash
pip install maturin
maturin develop
```

---

## 1. 基础用法

### 1.1 创建 Actor

```python
import asyncio
from pulsing.actor import Actor, Message, SystemConfig, create_actor_system

class EchoActor(Actor):
    async def receive(self, msg: Message) -> Message:
        return Message.single("echo", msg.payload)

async def main():
    config = SystemConfig.standalone()
    system = await create_actor_system(config)
    
    actor_ref = await system.spawn(EchoActor(), "echo")
    
    response = await actor_ref.ask(Message.single("hello", b"world"))
    print(f"Response: {response.payload}")
    
    await system.shutdown()

asyncio.run(main())
```

### 1.2 使用 @as_actor 装饰器

`@as_actor` 装饰器可以自动将类转换为 Actor：

```python
from pulsing.actor import SystemConfig, as_actor, create_actor_system

@as_actor
class Counter:
    def __init__(self, init_value: int = 0):
        self.value = init_value

    def get(self) -> int:
        return self.value

    def increment(self, n: int = 1) -> int:
        self.value += n
        return self.value

async def main():
    system = await create_actor_system(SystemConfig.standalone())
    
    counter = await Counter.local(system, init_value=10)
    print(await counter.get())  # 10
    print(await counter.increment(5))  # 15
    
    await system.shutdown()
```

---

## 2. 集群通信

### 2.1 启动集群

```python
# Node 1 - 启动 seed 节点
config = SystemConfig.with_addr("0.0.0.0:8000")
system = await create_actor_system(config)
await system.spawn(WorkerActor(), "worker", public=True)

# Node 2 - 加入集群
config = SystemConfig.with_addr("0.0.0.0:8001").with_seeds(["192.168.1.1:8000"])
system = await create_actor_system(config)

# 等待集群同步
await asyncio.sleep(1.0)

# 查找远程 Actor
remote_ref = await system.find("worker")
response = await remote_ref.ask(Message.single("request", data))
```

### 2.2 公共 vs 私有 Actor

- **公共 Actor**：集群中其他节点可见，可通过 `system.find()` 查找
- **私有 Actor**：仅本地可访问

```python
# 公共 actor - 可被其他节点找到
await system.spawn(WorkerActor(), "worker", public=True)

# 私有 actor - 仅本地
await system.spawn(WorkerActor(), "local-worker", public=False)
```

---

## 3. 消息类型

### 3.1 单条消息

```python
# 创建单条消息
msg = Message.single("ping", b"data")

# 发送并接收
response = await actor_ref.ask(msg)
```

### 3.2 流式消息

```python
# 创建流式消息
msg = Message.stream("process", b"data")

# 发送流式请求
async for chunk in actor_ref.ask_stream(msg):
    print(f"Chunk: {chunk}")
```

---

## 4. 错误处理

```python
try:
    response = await actor_ref.ask(msg)
except Exception as e:
    print(f"Error: {e}")

# 检查 actor 是否存在
if await system.has_actor("worker"):
    ref = await system.find("worker")
```

---

## 5. 常用模式

### 5.1 请求-响应模式

```python
@as_actor
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def multiply(self, a: int, b: int) -> int:
        return a * b

async def main():
    system = await create_actor_system(SystemConfig.standalone())
    calc = await Calculator.local(system)
    
    result = await calc.add(10, 20)  # 30
    result = await calc.multiply(5, 6)  # 30
```

### 5.2 有状态 Actor

```python
@as_actor
class StatefulActor:
    def __init__(self):
        self.state = {}

    def set(self, key: str, value: str) -> None:
        self.state[key] = value

    def get(self, key: str, default=None):
        return self.state.get(key, default)
```

### 5.3 异步方法

```python
@as_actor
class AsyncWorker:
    async def process(self, data: str) -> dict:
        await asyncio.sleep(0.1)
        return {"processed": data.upper()}

async def main():
    system = await create_actor_system(SystemConfig.standalone())
    worker = await AsyncWorker.local(system)
    
    result = await worker.process("hello")
    print(result)  # {"processed": "HELLO"}
```

---

## 6. 最佳实践

1. **始终关闭系统**：完成后调用 `await system.shutdown()`
2. **集群通信使用公共 actor**：需要远程访问的 actor 设置 `public=True`
3. **优雅处理错误**：在 try-except 块中包装 `ask()` 调用
4. **I/O 操作使用异步方法**：网络或文件操作优先使用异步方法
5. **等待集群同步**：加入集群后稍等片刻再访问远程 actor

---

## 下一步

- 阅读[架构指南](../guide/architecture.md)了解系统设计细节
- 查看[远程 Actor 指南](../guide/remote_actors.md)了解高级集群用法
- 探索[设计文档](../design/actor-system.md)了解实现细节
- 查看[API 参考](../api_reference.md)获取完整 API 文档

