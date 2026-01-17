"""
LangGraph Node Executor - 在 Pulsing Actor 中执行 LangGraph 节点

Features:
- 可配置的线程池大小
- 有界队列 + backpressure 支持
- 优雅的过载处理
"""

from __future__ import annotations

import asyncio
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict

from pulsing.actor import Actor, ActorId, ActorRef, SystemConfig, create_actor_system

logger = logging.getLogger("pulsing.langgraph")

# Default configuration
DEFAULT_MAX_WORKERS = 4
DEFAULT_QUEUE_SIZE = 100


class ExecutorConfig:
    """执行器配置"""

    def __init__(
        self,
        max_workers: int = DEFAULT_MAX_WORKERS,
        queue_size: int = DEFAULT_QUEUE_SIZE,
        queue_timeout: float = 30.0,
    ):
        """
        Args:
            max_workers: 线程池中的最大工作线程数
            queue_size: 有界队列的最大容量
            queue_timeout: 队列满时等待的超时时间 (秒)
        """
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.queue_timeout = queue_timeout


class BoundedExecutor:
    """带有界队列和 backpressure 的线程池执行器"""

    def __init__(self, config: ExecutorConfig | None = None):
        self._config = config or ExecutorConfig()
        self._executor = ThreadPoolExecutor(max_workers=self._config.max_workers)
        self._semaphore = asyncio.Semaphore(self._config.queue_size)
        self._pending_count = 0
        self._lock = asyncio.Lock()

    async def submit(self, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务到线程池

        如果队列已满，会等待 queue_timeout 秒。
        超时后抛出 asyncio.TimeoutError。

        Returns:
            任务执行结果
        """
        # 等待获取信号量 (backpressure)
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(), timeout=self._config.queue_timeout
            )
            if not acquired:
                raise RuntimeError("Failed to acquire semaphore")
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Executor queue full ({self._config.queue_size} pending tasks), "
                f"timed out after {self._config.queue_timeout}s"
            )

        async with self._lock:
            self._pending_count += 1

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, func, *args, **kwargs)
            return result
        finally:
            self._semaphore.release()
            async with self._lock:
                self._pending_count -= 1

    @property
    def pending_count(self) -> int:
        """当前等待执行的任务数"""
        return self._pending_count

    @property
    def queue_capacity(self) -> int:
        """队列容量"""
        return self._config.queue_size

    @property
    def available_slots(self) -> int:
        """可用的队列槽位数"""
        return self._config.queue_size - self._pending_count

    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        self._executor.shutdown(wait=wait)


class LangGraphNodeActor(Actor):
    """将 LangGraph 节点函数包装为 Pulsing Actor"""

    def __init__(
        self,
        node_name: str,
        node_func: Callable,
        executor_config: ExecutorConfig | None = None,
    ):
        self.node_name = node_name
        self.node_func = node_func
        self._executor = BoundedExecutor(executor_config)

    def on_start(self, actor_id: ActorId) -> None:
        logger.info(
            f"LangGraph node '{self.node_name}' started "
            f"(workers={self._executor._config.max_workers}, "
            f"queue={self._executor._config.queue_size})"
        )

    def on_stop(self) -> None:
        self._executor.shutdown(wait=True)
        logger.info(f"LangGraph node '{self.node_name}' stopped")

    def metadata(self) -> dict[str, str]:
        return {
            "type": "langgraph_node",
            "node_name": self.node_name,
            "pending_tasks": str(self._executor.pending_count),
            "queue_capacity": str(self._executor.queue_capacity),
        }

    async def receive(self, msg: Any) -> Any:
        if not isinstance(msg, dict):
            return {"success": False, "error": "Invalid message format"}

        msg_type = msg.get("type")

        # 健康检查 / 状态查询
        if msg_type == "status":
            return {
                "success": True,
                "node": self.node_name,
                "pending_tasks": self._executor.pending_count,
                "available_slots": self._executor.available_slots,
                "queue_capacity": self._executor.queue_capacity,
            }

        # 执行节点
        if msg_type != "execute":
            return {"success": False, "error": f"Unknown message type: {msg_type}"}

        try:
            state = msg.get("state", {})

            if asyncio.iscoroutinefunction(self.node_func):
                result = await self.node_func(state)
            else:
                # 使用有界执行器 (支持 backpressure)
                result = await self._executor.submit(self.node_func, state)

            return {"success": True, "state": result, "node": self.node_name}
        except asyncio.TimeoutError as e:
            logger.warning(f"Node '{self.node_name}' backpressure triggered: {e}")
            return {
                "success": False,
                "error": str(e),
                "node": self.node_name,
                "backpressure": True,
            }
        except Exception as e:
            logger.exception(f"Node '{self.node_name}' failed: {e}")
            return {"success": False, "error": str(e), "node": self.node_name}


class NodeExecutorPool:
    """管理到远程节点的连接"""

    def __init__(self, system, node_mapping: Dict[str, str]):
        self._system = system
        self._node_mapping = node_mapping
        self._node_refs: Dict[str, ActorRef] = {}

    async def execute(
        self, node_name: str, state: dict, config: dict | None = None
    ) -> dict:
        """执行节点（可能是远程的）"""
        actor_ref = await self._get_node_ref(node_name)

        if actor_ref is None:
            return {
                "success": False,
                "error": f"Node '{node_name}' not found",
                "node": node_name,
            }

        result = await actor_ref.ask(
            {"type": "execute", "state": state, "config": config}
        )
        return self._deserialize(result)

    async def get_status(self, node_name: str) -> dict:
        """获取节点状态（包括 backpressure 信息）"""
        actor_ref = await self._get_node_ref(node_name)

        if actor_ref is None:
            return {"success": False, "error": f"Node '{node_name}' not found"}

        result = await actor_ref.ask({"type": "status"})
        return self._deserialize(result)

    def _deserialize(self, response) -> dict:
        """反序列化响应 (处理 pickle 序列化的 Python 对象)"""
        if hasattr(response, "msg_type") and hasattr(response, "payload"):
            if not response.msg_type and isinstance(response.payload, bytes):
                try:
                    return pickle.loads(response.payload)
                except Exception:
                    pass
        return (
            response
            if isinstance(response, dict)
            else {"success": False, "error": "Bad response"}
        )

    async def _get_node_ref(self, node_name: str) -> ActorRef | None:
        """获取节点的 ActorRef"""
        if node_name in self._node_refs:
            return self._node_refs[node_name]

        actor_name = self._node_mapping.get(node_name, f"langgraph_node_{node_name}")
        try:
            ref = await self._system.resolve_named(actor_name)
            self._node_refs[node_name] = ref
            return ref
        except Exception as e:
            logger.warning(f"Failed to resolve '{node_name}' -> '{actor_name}': {e}")
            return None

    def is_distributed_node(self, node_name: str) -> bool:
        return node_name in self._node_mapping


async def start_worker(
    node_name: str,
    node_func: Callable,
    *,
    addr: str,
    seeds: list[str] | None = None,
    actor_name: str | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    queue_size: int = DEFAULT_QUEUE_SIZE,
    queue_timeout: float = 30.0,
):
    """
    启动 LangGraph 节点 Worker

    Args:
        node_name: 节点名称
        node_func: 节点处理函数
        addr: 绑定地址
        seeds: 集群种子节点
        actor_name: Actor 名称 (默认为 langgraph_node_{node_name})
        max_workers: 线程池最大工作线程数
        queue_size: 有界队列容量
        queue_timeout: 队列满时的等待超时

    Example:
        await start_worker(
            "llm",
            llm_node,
            addr="0.0.0.0:8001",
            max_workers=8,
            queue_size=200,
        )
    """
    config = SystemConfig.with_addr(addr)
    if seeds:
        config = config.with_seeds(seeds)
    system = await create_actor_system(config)

    executor_config = ExecutorConfig(
        max_workers=max_workers,
        queue_size=queue_size,
        queue_timeout=queue_timeout,
    )

    actor = LangGraphNodeActor(node_name, node_func, executor_config)
    name = actor_name or f"langgraph_node_{node_name}"

    await system.spawn(name, actor, public=True)
    logger.info(
        f"Worker started: {name} @ {addr} "
        f"(workers={max_workers}, queue={queue_size})"
    )

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        await system.shutdown()
