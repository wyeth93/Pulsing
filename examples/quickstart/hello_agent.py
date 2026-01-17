"""
🚀 Pulsing 快速入门 - 第一个 Multi-Agent 应用

运行: python examples/quickstart/hello_agent.py

你将看到两个 Agent 互相打招呼！
"""

import asyncio
from pulsing.actor import remote, resolve
from pulsing.agent import runtime


@remote
class Greeter:
    """一个简单的问候 Agent"""

    def __init__(self, display_name: str):
        self.display_name = display_name
        print(f"✨ [{self.display_name}] 已上线")

    def greet(self, message: str) -> str:
        """接收问候"""
        print(f"📨 [{self.display_name}] 收到消息: {message}")
        return f"你好！我是 {self.display_name}"

    async def say_hello_to(self, peer_name: str) -> str:
        """向另一个 Agent 打招呼"""
        peer = await resolve(peer_name)
        print(f"👋 [{self.display_name}] 正在向 [{peer_name}] 打招呼...")
        reply = await peer.greet(f"嗨，我是 {self.display_name}！")
        print(f"💬 [{self.display_name}] 收到回复: {reply}")
        return reply


async def main():
    print("=" * 50)
    print("🎉 Pulsing Multi-Agent 快速入门")
    print("=" * 50)

    async with runtime():
        # 创建两个 Agent
        alice = await Greeter.spawn(display_name="Alice", name="alice")
        bob = await Greeter.spawn(display_name="Bob", name="bob")

        print("\n--- Agent 互相打招呼 ---\n")

        # Alice 向 Bob 打招呼
        await alice.say_hello_to("bob")

        print()

        # Bob 向 Alice 打招呼
        await bob.say_hello_to("alice")

    print("\n" + "=" * 50)
    print("✅ 完成！你已经创建了第一个 Multi-Agent 应用")
    print("=" * 50)
    print("\n下一步:")
    print("  - 试试 MBTI 讨论: python examples/agent/pulsing/mbti_discussion.py --mock")
    print("  - 试试并行创意:   python examples/agent/pulsing/parallel_ideas_async.py --mock")


if __name__ == "__main__":
    asyncio.run(main())
