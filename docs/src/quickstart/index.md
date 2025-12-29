# Quick Start

Pulsing is a lightweight distributed Actor framework providing location-transparent messaging, cluster discovery, and high-performance async processing.

## Installation

```bash
pip install maturin
maturin develop
```

---

## 1. Basic Usage

### 1.1 Creating an Actor

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

### 1.2 Using @as_actor Decorator

The `@as_actor` decorator automatically converts a class into an Actor:

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

## 2. Cluster Communication

### 2.1 Starting a Cluster

```python
# Node 1 - Start seed node
config = SystemConfig.with_addr("0.0.0.0:8000")
system = await create_actor_system(config)
await system.spawn(WorkerActor(), "worker", public=True)

# Node 2 - Join cluster
config = SystemConfig.with_addr("0.0.0.0:8001").with_seeds(["192.168.1.1:8000"])
system = await create_actor_system(config)

# Wait for cluster sync
await asyncio.sleep(1.0)

# Find remote Actor
remote_ref = await system.find("worker")
response = await remote_ref.ask(Message.single("request", data))
```

### 2.2 Public vs Private Actors

- **Public Actors**: Visible to other nodes in the cluster, can be found via `system.find()`
- **Private Actors**: Only accessible locally

```python
# Public actor - can be found by other nodes
await system.spawn(WorkerActor(), "worker", public=True)

# Private actor - local only
await system.spawn(WorkerActor(), "local-worker", public=False)
```

---

## 3. Message Types

### 3.1 Single Message

```python
# Create single message
msg = Message.single("ping", b"data")

# Send and receive
response = await actor_ref.ask(msg)
```

### 3.2 Streaming Messages

```python
# Create streaming message
msg = Message.stream("process", b"data")

# Send streaming request
async for chunk in actor_ref.ask_stream(msg):
    print(f"Chunk: {chunk}")
```

---

## 4. Error Handling

```python
try:
    response = await actor_ref.ask(msg)
except Exception as e:
    print(f"Error: {e}")

# Check if actor exists
if await system.has_actor("worker"):
    ref = await system.find("worker")
```

---

## 5. Common Patterns

### 5.1 Request-Response Pattern

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

### 5.2 Stateful Actor

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

### 5.3 Async Methods

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

## 6. Best Practices

1. **Always shutdown the system**: Call `await system.shutdown()` when done
2. **Use public actors for cluster communication**: Set `public=True` for actors that need to be accessed remotely
3. **Handle errors gracefully**: Wrap `ask()` calls in try-except blocks
4. **Use async methods for I/O operations**: Prefer async methods for network or file operations
5. **Wait for cluster sync**: Add a small delay after joining a cluster before accessing remote actors

---

## Next Steps

- Read the [Architecture Guide](../guide/architecture.md) for system design details
- Check out [Remote Actors Guide](../guide/remote_actors.md) for advanced cluster usage
- Explore [Design Documents](../design/actor-system.md) for implementation details
- See [API Reference](../api_reference.md) for complete API documentation

