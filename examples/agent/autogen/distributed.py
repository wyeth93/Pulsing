"""
AutoGen 兼容性示例 - 分布式模式

演示 PulsingRuntime 的分布式能力

Usage (3 个终端):
    # 终端 1: 启动 Writer Agent
    python distributed.py writer
    
    # 终端 2: 启动 Editor Agent  
    python distributed.py editor
    
    # 终端 3: 启动 Manager 并发起对话
    python distributed.py manager
"""

import asyncio
import sys
from dataclasses import dataclass

# 消息类型
@dataclass
class RequestToSpeak:
    topic: str


@dataclass
class ChatMessage:
    content: str
    sender: str


# 简化版 Agent (不依赖 autogen_core)
class WriterAgent:
    """Writer Agent - 负责写作"""
    
    def __init__(self):
        self.id = None
        self._runtime = None
    
    async def bind_id_and_runtime(self, id, runtime):
        self.id = id
        self._runtime = runtime
    
    async def on_message(self, message, ctx):
        if isinstance(message, RequestToSpeak):
            print(f"[Writer] Received request to speak about: {message.topic}")
            response = f"Here's my creative writing about {message.topic}: It was a dark and stormy night..."
            return ChatMessage(content=response, sender="writer")
        elif isinstance(message, ChatMessage):
            print(f"[Writer] Received feedback from {message.sender}: {message.content[:50]}...")
        return None


class EditorAgent:
    """Editor Agent - 负责编辑审核"""
    
    def __init__(self):
        self.id = None
        self._runtime = None
    
    async def bind_id_and_runtime(self, id, runtime):
        self.id = id
        self._runtime = runtime
    
    async def on_message(self, message, ctx):
        if isinstance(message, RequestToSpeak):
            print(f"[Editor] Received request to review")
            return ChatMessage(
                content="The writing is good, but consider adding more details.",
                sender="editor"
            )
        elif isinstance(message, ChatMessage):
            print(f"[Editor] Received message from {message.sender}: {message.content[:50]}...")
        return None


async def run_writer():
    """运行 Writer Agent 节点"""
    from pulsing.autogen import PulsingRuntime
    
    print("Starting Writer Agent node...")
    runtime = PulsingRuntime(
        addr="0.0.0.0:8001",
        seeds=[],  # 第一个节点
    )
    await runtime.start()
    
    await runtime.register_factory("writer", lambda: WriterAgent())
    
    print("Writer Agent ready, waiting for messages...")
    print("Press Ctrl+C to stop")
    
    await runtime.stop_when_signal()


async def run_editor():
    """运行 Editor Agent 节点"""
    from pulsing.autogen import PulsingRuntime
    
    print("Starting Editor Agent node...")
    runtime = PulsingRuntime(
        addr="0.0.0.0:8002",
        seeds=["127.0.0.1:8001"],  # 加入 Writer 节点的集群
    )
    await runtime.start()
    
    await runtime.register_factory("editor", lambda: EditorAgent())
    
    print("Editor Agent ready, waiting for messages...")
    print("Press Ctrl+C to stop")
    
    await runtime.stop_when_signal()


async def run_manager():
    """运行 Manager - 发起对话"""
    from pulsing.autogen import PulsingRuntime
    
    print("Starting Manager node...")
    runtime = PulsingRuntime(
        addr="0.0.0.0:8003",
        seeds=["127.0.0.1:8001", "127.0.0.1:8002"],  # 加入集群
    )
    await runtime.start()
    
    # 等待集群稳定
    await asyncio.sleep(2)
    
    # 创建 AgentId
    class AgentId:
        def __init__(self, type, key="default"):
            self.type = type
            self.key = key
    
    writer_id = AgentId("writer", "default")
    editor_id = AgentId("editor", "default")
    
    print("\n--- Starting conversation ---\n")
    
    # Round 1: 让 Writer 写作
    print("Manager: Asking Writer to write about AI...")
    response = await runtime.send_message(
        RequestToSpeak(topic="AI and the future"),
        recipient=writer_id,
    )
    print(f"Writer response: {response}\n")
    
    # Round 2: 让 Editor 审核
    print("Manager: Asking Editor to review...")
    response = await runtime.send_message(
        RequestToSpeak(topic="review"),
        recipient=editor_id,
    )
    print(f"Editor response: {response}\n")
    
    print("--- Conversation complete ---")
    
    await runtime.stop()


async def run_standalone():
    """单机模式演示 (所有 Agent 在同一进程)"""
    from pulsing.autogen import PulsingRuntime
    
    print("=" * 60)
    print("Running in standalone mode (all agents in one process)")
    print("=" * 60)
    
    runtime = PulsingRuntime()  # 单机模式
    await runtime.start()
    
    # 注册所有 Agent
    await runtime.register_factory("writer", lambda: WriterAgent())
    await runtime.register_factory("editor", lambda: EditorAgent())
    
    class AgentId:
        def __init__(self, type, key="default"):
            self.type = type
            self.key = key
    
    writer_id = AgentId("writer")
    editor_id = AgentId("editor")
    
    print("\n--- Starting conversation ---\n")
    
    # Round 1
    response = await runtime.send_message(
        RequestToSpeak(topic="AI"),
        recipient=writer_id,
    )
    print(f"Writer: {response}\n")
    
    # Round 2
    response = await runtime.send_message(
        RequestToSpeak(topic="review"),
        recipient=editor_id,
    )
    print(f"Editor: {response}\n")
    
    await runtime.stop()
    print("Done!")


def main():
    if len(sys.argv) < 2:
        # 默认运行单机模式
        asyncio.run(run_standalone())
        return
    
    role = sys.argv[1].lower()
    
    if role == "writer":
        asyncio.run(run_writer())
    elif role == "editor":
        asyncio.run(run_editor())
    elif role == "manager":
        asyncio.run(run_manager())
    elif role == "standalone":
        asyncio.run(run_standalone())
    else:
        print(f"Unknown role: {role}")
        print("Usage: python distributed.py [writer|editor|manager|standalone]")
        sys.exit(1)


if __name__ == "__main__":
    main()
