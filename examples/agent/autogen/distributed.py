"""
AutoGen 兼容性示例 - 分布式模式

演示 PulsingRuntime 的分布式能力

Usage:
    # 方式 1: 手动启动多个终端
    python distributed.py writer
    python distributed.py editor
    python distributed.py manager

    # 方式 2: 使用 torchrun 一键启动
    torchrun --nproc_per_node=3 distributed.py

    # 方式 3: 使用启动脚本
    ./run_distributed.sh
    
    # 方式 4: 单机模式测试
    python distributed.py standalone
"""

import asyncio
import os
import sys
from dataclasses import dataclass

from autogen_core import AgentId


# 消息类型
@dataclass
class RequestToSpeak:
    topic: str


@dataclass
class ChatMessage:
    content: str
    sender: str


# Agent 定义
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
                sender="editor",
            )
        elif isinstance(message, ChatMessage):
            print(f"[Editor] Received message from {message.sender}: {message.content[:50]}...")
        return None


# ============================================================================
# 分布式配置
# ============================================================================

# 角色定义: rank -> (role_name, agent_factory)
ROLE_MAP = {
    0: ("writer", WriterAgent),
    1: ("editor", EditorAgent),
    2: ("manager", None),  # Manager 不注册 Agent，只发起调用
}

BASE_PORT = 18000  # 基础端口


def get_distributed_config():
    """从环境变量获取分布式配置 (兼容 torchrun)"""
    rank = int(os.environ.get("RANK", os.environ.get("LOCAL_RANK", -1)))
    world_size = int(os.environ.get("WORLD_SIZE", -1))
    master_addr = os.environ.get("MASTER_ADDR", "127.0.0.1")
    master_port = int(os.environ.get("MASTER_PORT", BASE_PORT))

    return rank, world_size, master_addr, master_port


def get_pulsing_config(rank: int, world_size: int, master_addr: str, master_port: int):
    """根据 rank 生成 Pulsing 配置"""
    # 每个进程使用不同的端口
    my_port = master_port + rank
    my_addr = f"0.0.0.0:{my_port}"

    # Rank 0 是种子节点，其他节点连接到它
    if rank == 0:
        seeds = []
    else:
        seeds = [f"{master_addr}:{master_port}"]

    return my_addr, seeds


# ============================================================================
# 运行函数
# ============================================================================


async def run_with_rank(rank: int, world_size: int, master_addr: str, master_port: int):
    """根据 rank 运行对应的角色"""
    from pulsing.autogen import PulsingRuntime

    my_addr, seeds = get_pulsing_config(rank, world_size, master_addr, master_port)
    role_name, agent_class = ROLE_MAP.get(rank, (f"worker_{rank}", None))

    print(f"[Rank {rank}] Starting as '{role_name}' at {my_addr}, seeds: {seeds}")

    runtime = PulsingRuntime(addr=my_addr, seeds=seeds)
    await runtime.start()

    # 注册 Agent (如果有)
    if agent_class:
        await runtime.register_factory(role_name, lambda cls=agent_class: cls())
        print(f"[Rank {rank}] Registered agent: {role_name}")

    # 等待集群稳定
    await asyncio.sleep(2)

    # Manager (rank 2) 发起对话
    if rank == world_size - 1:  # 最后一个进程是 Manager
        await run_manager_logic(runtime)
        await runtime.stop()
    else:
        # Worker 等待信号退出
        print(f"[Rank {rank}] Waiting for messages... (Ctrl+C to stop)")
        try:
            await runtime.stop_when_signal()
        except asyncio.CancelledError:
            pass


async def run_manager_logic(runtime):
    """Manager 的业务逻辑"""
    print("\n" + "=" * 50)
    print("Manager: Starting conversation")
    print("=" * 50 + "\n")

    writer_id = AgentId("writer", "default")
    editor_id = AgentId("editor", "default")

    # Round 1: 让 Writer 写作
    print("Manager: Asking Writer to write about AI...")
    try:
        response = await runtime.send_message(
            RequestToSpeak(topic="AI and the future"),
            recipient=writer_id,
        )
        print(f"Writer response: {response}\n")
    except Exception as e:
        print(f"Error calling Writer: {e}\n")

    # Round 2: 让 Editor 审核
    print("Manager: Asking Editor to review...")
    try:
        response = await runtime.send_message(
            RequestToSpeak(topic="review"),
            recipient=editor_id,
        )
        print(f"Editor response: {response}\n")
    except Exception as e:
        print(f"Error calling Editor: {e}\n")

    print("=" * 50)
    print("Manager: Conversation complete!")
    print("=" * 50)


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

    await run_manager_logic(runtime)
    await runtime.stop()
    print("Done!")


# ============================================================================
# 手动启动模式 (向后兼容)
# ============================================================================


async def run_writer():
    """手动启动 Writer 节点"""
    from pulsing.autogen import PulsingRuntime

    print("Starting Writer Agent node...")
    runtime = PulsingRuntime(addr="0.0.0.0:8001", seeds=[])
    await runtime.start()
    await runtime.register_factory("writer", lambda: WriterAgent())
    print("Writer Agent ready, waiting for messages...")
    await runtime.stop_when_signal()


async def run_editor():
    """手动启动 Editor 节点"""
    from pulsing.autogen import PulsingRuntime

    print("Starting Editor Agent node...")
    runtime = PulsingRuntime(addr="0.0.0.0:8002", seeds=["127.0.0.1:8001"])
    await runtime.start()
    await runtime.register_factory("editor", lambda: EditorAgent())
    print("Editor Agent ready, waiting for messages...")
    await runtime.stop_when_signal()


async def run_manager():
    """手动启动 Manager 节点"""
    from pulsing.autogen import PulsingRuntime

    print("Starting Manager node...")
    runtime = PulsingRuntime(
        addr="0.0.0.0:8003",
        seeds=["127.0.0.1:8001", "127.0.0.1:8002"],
    )
    await runtime.start()
    await asyncio.sleep(2)
    await run_manager_logic(runtime)
    await runtime.stop()


# ============================================================================
# 入口
# ============================================================================


def main():
    # 检查是否通过 torchrun 启动
    rank, world_size, master_addr, master_port = get_distributed_config()

    if rank >= 0 and world_size > 0:
        # torchrun 模式
        print(f"[torchrun] rank={rank}, world_size={world_size}, master={master_addr}:{master_port}")
        asyncio.run(run_with_rank(rank, world_size, master_addr, master_port))
        return

    # 手动模式
    if len(sys.argv) < 2:
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
        print("   or: torchrun --nproc_per_node=3 distributed.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
