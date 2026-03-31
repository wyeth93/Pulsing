"""Tests for Ray-backed pulsing.subprocess cleanup and auto-init."""

import pytest

ray = pytest.importorskip("ray")

import pulsing as pul
import pulsing.subprocess.popen as popen_module
from pulsing.subprocess import PIPE, Popen, run
from pulsing.subprocess.ray_spawn import cleanup_ray_actor


def _enable_pulsing_backend(monkeypatch, value: str = "1") -> None:
    monkeypatch.setenv("USE_POLSING_SUBPROCESS", value)


@pytest.fixture(autouse=True)
def clear_subprocess_env(monkeypatch):
    monkeypatch.delenv("USE_POLSING_SUBPROCESS", raising=False)


@pytest.fixture(autouse=True)
async def ray_and_subprocess_backend():
    if not ray.is_initialized():
        ray.init(num_cpus=2)
    yield
    popen_module._shutdown_module_runtime()
    if pul.is_initialized():
        await pul.shutdown()
    popen_module._set_pulsing_loop(None)
    ray.shutdown()


def test_non_empty_resources_with_env_disabled_stays_native():
    proc = Popen(
        ["echo", "native"],
        stdout=PIPE,
        resources={"num_cpus": 1},
    )
    stdout, _ = proc.communicate()

    assert stdout.strip() == b"native"
    assert proc._native is not None
    assert proc._proxy is None
    assert not pul.is_initialized()


@pytest.mark.asyncio
async def test_popen_close_cleans_up_ray_actor(monkeypatch):
    _enable_pulsing_backend(monkeypatch)
    proc = Popen(
        ["echo", "hello"],
        stdout=PIPE,
        resources={"num_cpus": 1},
    )
    proc.communicate()
    handle = proc._proxy._ray_node_actor

    assert handle is not None
    assert pul.is_initialized()
    assert str(pul.get_system().addr).startswith("0.0.0.0:")

    proc.close()
    assert proc._proxy._ray_node_actor is None

    with pytest.raises(ray.exceptions.RayActorError):
        ray.get(handle.shutdown.remote())


@pytest.mark.asyncio
async def test_popen_context_manager_cleans_up_ray(monkeypatch):
    _enable_pulsing_backend(monkeypatch)
    with Popen(
        ["echo", "ctx"],
        stdout=PIPE,
        resources={"num_cpus": 1},
    ) as proc:
        proc.communicate()
        handle = proc._proxy._ray_node_actor
        assert handle is not None

    assert proc._proxy._ray_node_actor is None


@pytest.mark.asyncio
async def test_double_close_is_noop(monkeypatch):
    _enable_pulsing_backend(monkeypatch)
    proc = Popen(
        ["echo", "twice"],
        stdout=PIPE,
        resources={"num_cpus": 1},
    )
    proc.communicate()
    proc.close()
    proc.close()


@pytest.mark.asyncio
async def test_cleanup_ray_actor_directly(monkeypatch):
    _enable_pulsing_backend(monkeypatch)
    proc = Popen(
        ["echo", "direct"],
        stdout=PIPE,
        resources={"num_cpus": 1},
    )
    proc.communicate()
    handle = proc._proxy._ray_node_actor

    assert handle is not None

    popen_module._run_sync(cleanup_ray_actor(proc._proxy))
    assert proc._proxy._ray_node_actor is None


@pytest.mark.asyncio
async def test_run_helper_cleans_up_ray(monkeypatch):
    _enable_pulsing_backend(monkeypatch)
    result = run(
        ["echo", "run_cleanup"],
        capture_output=True,
        resources={"num_cpus": 1},
    )

    assert result.returncode == 0
    assert b"run_cleanup" in result.stdout
