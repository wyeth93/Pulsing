# Ping-Pong

最基础的 Actor 通信示例（请求-响应与 fire-and-forget）。

## 展示内容

- Actor 生命周期（`on_start`、`on_stop`）
- `ask`（请求-响应）
- `tell`（单向发送）

## 代码

本页对应可直接运行的脚本：`examples/python/ping_pong.py`。

```python
import asyncio
from pulsing.actor import Actor, ActorId, Message, SystemConfig, create_actor_system


class Counter(Actor):
    def __init__(self):
        self.count = 0

    def on_start(self, actor_id: ActorId):
        print(f"[{actor_id}] Started with count: {self.count}")

    def on_stop(self):
        print(f"Stopped with count: {self.count}")

    def receive(self, msg: Message) -> Message:
        if msg.msg_type == "Ping":
            value = msg.to_json().get("value", 1)
            self.count += value
            return Message.from_json("Pong", {"result": self.count})
        elif msg.msg_type == "GetCount":
            return Message.from_json("Count", {"count": self.count})
        return Message.empty()


async def main():
    system = await create_actor_system(SystemConfig.standalone())
    actor = await system.spawn("counter", Counter())

    for i in range(1, 4):
        resp = await actor.ask(Message.from_json("Ping", {"value": i * 10}))
        print(resp.to_json())

    await actor.tell(Message.from_json("Ping", {"value": 100}))
    await asyncio.sleep(0.05)

    resp = await actor.ask(Message.from_json("GetCount", {}))
    print(resp.to_json())

    await system.shutdown()


asyncio.run(main())
```

## 运行方式

```bash
python examples/python/ping_pong.py
```


