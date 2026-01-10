"""
AutoGen 兼容性示例 - 单机模式

演示 PulsingRuntime 如何直接替代 AutoGen SingleThreadedAgentRuntime

Usage:
    pip install autogen-core
    python simple.py
"""

import asyncio
from dataclasses import dataclass

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)
from pulsing.autogen import PulsingRuntime


# 定义消息类型
@dataclass
class Ping:
    content: str


@dataclass
class Pong:
    content: str
    count: int


# 使用 AutoGen 原生 Agent 定义
class PingPongAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("PingPong Agent")
        self._count = 0

    @message_handler
    async def handle_ping(self, message: Ping, ctx: MessageContext) -> Pong:
        self._count += 1
        print(f"[PingPongAgent] Received: {message.content}, count: {self._count}")
        return Pong(content=f"Pong: {message.content}", count=self._count)


async def main_with_pulsing():
    """使用 PulsingRuntime"""
    print("=" * 50)
    print("Running with PulsingRuntime (standalone mode)")
    print("=" * 50)

    # 创建运行时 - 单机模式
    runtime = PulsingRuntime()
    await runtime.start()

    # 注册 Agent
    await runtime.register_factory(
        "ping_pong",
        lambda: PingPongAgent(),
    )

    # 发送消息
    for i in range(3):
        response = await runtime.send_message(
            Ping(content=f"Hello {i}"),
            recipient=AgentId("ping_pong", "default"),
        )
        print(f"[Main] Response: {response}")

    await runtime.stop()
    print("Done!\n")


async def main_with_autogen():
    """使用 AutoGen SingleThreadedAgentRuntime (对照组)"""
    print("=" * 50)
    print("Running with AutoGen SingleThreadedAgentRuntime")
    print("=" * 50)

    runtime = SingleThreadedAgentRuntime()

    await PingPongAgent.register(
        runtime,
        "ping_pong",
        lambda: PingPongAgent(),
    )

    runtime.start()

    for i in range(3):
        response = await runtime.send_message(
            Ping(content=f"Hello {i}"),
            recipient=AgentId("ping_pong", "default"),
        )
        print(f"[Main] Response: {response}")

    await runtime.stop()
    print("Done!\n")


async def main():
    # 先用 Pulsing
    await main_with_pulsing()

    # 再用 AutoGen 对照
    await main_with_autogen()


if __name__ == "__main__":
    asyncio.run(main())
