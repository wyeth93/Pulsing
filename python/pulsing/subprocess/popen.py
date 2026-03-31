"""
pulsing.subprocess — sync helpers mirroring the stdlib subprocess module.

Calls without ``resources`` use Python's native ``subprocess`` module.
Resource-backed Pulsing mode is enabled only when both of these are true:

* ``resources`` is a non-empty dict
* ``USE_POLSING_SUBPROCESS`` is set to a truthy value

In that resource-backed mode this module lazily initializes Pulsing
internally, so callers do not need to call ``await pul.init()`` first.
"""

from __future__ import annotations

import asyncio
import atexit
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pulsing.exceptions import PulsingActorError

from .process import _StderrProxy, _StdinProxy, _StdoutProxy

_pulsing_loop: asyncio.AbstractEventLoop | None = None
_module_loop: asyncio.AbstractEventLoop | None = None
_module_thread: threading.Thread | None = None
_module_ready: threading.Event | None = None
_module_lock = threading.Lock()
_module_owns_system = False
_cleanup_registered = False
_USE_PULSING_SUBPROCESS_ENV = "USE_POLSING_SUBPROCESS"
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})

CompletedProcess = subprocess.CompletedProcess


def _set_pulsing_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    global _pulsing_loop
    _pulsing_loop = loop


def _get_running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def _valid_loop(
    loop: asyncio.AbstractEventLoop | None,
) -> asyncio.AbstractEventLoop | None:
    if loop is None:
        return None
    if loop.is_closed() or not loop.is_running():
        return None
    return loop


def _get_dispatch_loop() -> asyncio.AbstractEventLoop | None:
    return _valid_loop(_pulsing_loop) or _valid_loop(_module_loop)


def _run_in_worker(awaitable) -> Any:
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _ensure_coro(awaitable)).result()


def _start_module_loop() -> asyncio.AbstractEventLoop:
    global _cleanup_registered, _module_loop, _module_ready, _module_thread

    loop = _valid_loop(_module_loop)
    if loop is not None:
        return loop

    ready = threading.Event()

    def _run() -> None:
        global _module_loop

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _module_loop = loop
        ready.set()
        loop.run_forever()

        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    _module_ready = ready
    _module_thread = threading.Thread(
        target=_run,
        daemon=True,
        name="pulsing-subprocess-loop",
    )
    _module_thread.start()
    ready.wait()

    if not _cleanup_registered:
        atexit.register(_shutdown_module_runtime)
        _cleanup_registered = True

    return _module_loop


def _submit_to_loop(loop: asyncio.AbstractEventLoop, awaitable) -> Any:
    return asyncio.run_coroutine_threadsafe(_ensure_coro(awaitable), loop).result()


def _shutdown_module_runtime() -> None:
    global _module_loop, _module_ready, _module_thread, _module_owns_system

    with _module_lock:
        loop = _module_loop
        thread = _module_thread
        owns_system = _module_owns_system

        if loop is None:
            _set_pulsing_loop(None)
            _module_ready = None
            _module_owns_system = False
            return

        if owns_system:
            try:
                import pulsing as pul

                if pul.is_initialized():
                    _submit_to_loop(loop, pul.shutdown())
            except Exception:
                pass

        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass

        if thread is not None:
            thread.join(timeout=5)

        _module_loop = None
        _module_thread = None
        _module_ready = None
        _module_owns_system = False
        _set_pulsing_loop(None)


async def _ensure_coro(obj) -> Any:
    """Await obj (works for coroutines and awaitable proxy objects)."""
    return await obj


def _env_enabled(name: str) -> bool:
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY_ENV_VALUES


def _should_use_pulsing(resources: dict | None) -> bool:
    return bool(resources) and _env_enabled(_USE_PULSING_SUBPROCESS_ENV)


def _ensure_module_owned_system() -> None:
    global _module_owns_system

    import pulsing as pul

    with _module_lock:
        if pul.is_initialized():
            system = pul.get_system()
            if system.addr is None:
                raise RuntimeError(
                    "resources requires a routable Pulsing address. "
                    "Initialize Pulsing explicitly with pul.init(addr='0.0.0.0:0')."
                )
            return

        loop = _start_module_loop()
        _module_owns_system = True
        _set_pulsing_loop(loop)
        _submit_to_loop(loop, pul.init(addr="0.0.0.0:0"))


def _run_sync(awaitable) -> Any:
    """Run an awaitable from sync code.

    If the active Pulsing system is owned by the caller's current event loop,
    synchronous dispatch would deadlock that loop, so we fail fast with a clear
    error. Auto-initialized subprocess backends run on a dedicated background
    loop and remain safe to call from ``async def`` without extra wrapping.
    """
    dispatch_loop = _get_dispatch_loop()
    running_loop = _get_running_loop()

    if dispatch_loop is not None:
        if running_loop is dispatch_loop:
            raise RuntimeError(
                "pulsing.subprocess cannot block on the same event loop that owns "
                "the active Pulsing system. Let pulsing.subprocess auto-initialize "
                "its own backend loop, call it from synchronous code, or use "
                "run_in_executor for this explicit pul.init() loop."
            )
        return _submit_to_loop(dispatch_loop, awaitable)

    if running_loop is not None:
        return _run_in_worker(awaitable)

    return asyncio.run(_ensure_coro(awaitable))


def _maybe_raise_timeout_expired(
    error: PulsingActorError, args: Any, timeout: float | None
) -> None:
    if timeout is None:
        raise error

    if "timed out after" not in str(error):
        raise error

    raise subprocess.TimeoutExpired(args, timeout) from error


class Popen:
    """Subprocess-compatible wrapper that switches between native and Pulsing backends."""

    def __init__(self, args, **kwargs):
        self.args = args
        self._args = args
        self._placement = kwargs.pop("placement", "local")
        self._system = kwargs.pop("system", None)
        self._name = kwargs.pop("name", None)
        self._resources = kwargs.pop("resources", None)
        self._spawn_kwargs = kwargs
        self._proxy = None
        self._native = None
        self._uses_pulsing = _should_use_pulsing(self._resources)

        self.returncode: int | None = None
        self.pid: int | None = None
        self.stdin = None
        self.stdout = None
        self.stderr = None

        if self._uses_pulsing:
            _ensure_module_owned_system()
            spawn_coro = self._aspawn()
            try:
                _run_sync(spawn_coro)
            except Exception:
                spawn_coro.close()
                raise
        else:
            self._spawn_native()

    def _spawn_native(self) -> None:
        self._native = subprocess.Popen(self._args, **self._spawn_kwargs)
        self.pid = self._native.pid
        self.returncode = self._native.returncode
        self.stdin = self._native.stdin
        self.stdout = self._native.stdout
        self.stderr = self._native.stderr

    async def _aspawn(self) -> None:
        from .ray_spawn import ray_spawn_process_actor
        from pulsing.core import get_system

        system = self._system or get_system()
        self._proxy = await ray_spawn_process_actor(
            system,
            self._args,
            actor_name=self._name,
            resources=self._resources,
            **self._spawn_kwargs,
        )

        self.pid = await self._proxy.pid()
        self.stdin = _StdinProxy(self._proxy, _run_sync)
        self.stdout = _StdoutProxy(self._proxy, _run_sync)
        self.stderr = _StderrProxy(self._proxy, _run_sync)

    def __enter__(self):
        if self._native is not None:
            self._native.__enter__()
        return self

    def __exit__(self, *exc):
        if self._native is not None:
            return self._native.__exit__(*exc)
        self.wait()
        self.close()
        return None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __getattr__(self, name: str):
        if self._native is not None:
            return getattr(self._native, name)
        raise AttributeError(name)

    def close(self) -> None:
        if self._native is not None:
            return

        if getattr(self._proxy, "_ray_node_actor", None) is not None:
            from .ray_spawn import cleanup_ray_actor

            cleanup_coro = cleanup_ray_actor(self._proxy)
            try:
                _run_sync(cleanup_coro)
            except Exception:
                cleanup_coro.close()
                raise

    def poll(self) -> int | None:
        if self._native is not None:
            self.returncode = self._native.poll()
            return self.returncode

        rc = _run_sync(self._proxy.poll())
        self.returncode = rc
        return rc

    def wait(self, timeout: float | None = None) -> int:
        if self._native is not None:
            self.returncode = self._native.wait(timeout=timeout)
            return self.returncode

        rc = _run_sync(self._proxy.wait(timeout))
        self.returncode = rc
        return rc

    def communicate(self, input=None, timeout: float | None = None) -> tuple:
        if self._native is not None:
            stdout, stderr = self._native.communicate(input=input, timeout=timeout)
            self.returncode = self._native.returncode
            return stdout, stderr

        async def _do():
            stdout, stderr = await self._proxy.communicate(input, timeout)
            self.returncode = await self._proxy.returncode()
            return stdout, stderr

        try:
            return _run_sync(_do())
        except PulsingActorError as error:
            _maybe_raise_timeout_expired(error, self._args, timeout)

    def send_signal(self, sig: int) -> None:
        if self._native is not None:
            self._native.send_signal(sig)
            return
        _run_sync(self._proxy.send_signal(sig))

    def terminate(self) -> None:
        if self._native is not None:
            self._native.terminate()
            return
        _run_sync(self._proxy.terminate())

    def kill(self) -> None:
        if self._native is not None:
            self._native.kill()
            return
        _run_sync(self._proxy.kill())


def run(
    args,
    *,
    stdin=None,
    input=None,
    stdout=None,
    stderr=None,
    capture_output: bool = False,
    cwd=None,
    env=None,
    shell: bool = False,
    encoding=None,
    errors=None,
    text: bool = False,
    timeout: float | None = None,
    check: bool = False,
    placement: str | int = "local",
    system=None,
    name: str | None = None,
    resources: dict | None = None,
) -> CompletedProcess:
    """Run a command and return ``subprocess.CompletedProcess``."""
    if capture_output:
        if stdout is not None or stderr is not None:
            raise ValueError("capture_output is mutually exclusive with stdout/stderr")
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE

    if input is not None:
        if stdin is not None:
            raise ValueError("stdin and input are mutually exclusive")
        stdin = subprocess.PIPE

    proc = Popen(
        args,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        shell=shell,
        encoding=encoding,
        errors=errors,
        text=text,
        placement=placement,
        system=system,
        name=name,
        resources=resources,
    )

    try:
        out, err = proc.communicate(input=input, timeout=timeout)
    finally:
        proc.close()

    result = CompletedProcess(
        args=args, returncode=proc.returncode, stdout=out, stderr=err
    )
    if check:
        result.check_returncode()
    return result


def call(
    args, *, timeout=None, placement="local", system=None, resources=None, **kwargs
) -> int:
    return run(
        args,
        timeout=timeout,
        placement=placement,
        system=system,
        resources=resources,
        **kwargs,
    ).returncode


def check_call(
    args, *, timeout=None, placement="local", system=None, resources=None, **kwargs
) -> int:
    return run(
        args,
        timeout=timeout,
        check=True,
        placement=placement,
        system=system,
        resources=resources,
        **kwargs,
    ).returncode


def check_output(
    args,
    *,
    stderr=None,
    timeout=None,
    placement="local",
    system=None,
    resources=None,
    **kwargs,
) -> bytes | str:
    return run(
        args,
        stdout=subprocess.PIPE,
        stderr=stderr,
        timeout=timeout,
        check=True,
        placement=placement,
        system=system,
        resources=resources,
        **kwargs,
    ).stdout
