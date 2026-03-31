#!/usr/bin/env python3
"""
pulsing.subprocess 示例。

默认不传 ``resources`` 时走原生 ``subprocess``。
只有同时满足下面两个条件时，才会走 Pulsing 后端：

1. 给调用显式传入非空 ``resources``
2. 设置 ``USE_POLSING_SUBPROCESS=1``

    python examples/python/subprocess_example.py
    python examples/python/subprocess_example.py --resources
    USE_POLSING_SUBPROCESS=1 python examples/python/subprocess_example.py --resources
"""

import os
import sys

import pulsing.subprocess as subprocess

PIPE = subprocess.PIPE
USE_RESOURCES = "--resources" in sys.argv
EXTRA = {"resources": {"num_cpus": 2}} if USE_RESOURCES else {}
ENV_ENABLED = os.getenv("USE_POLSING_SUBPROCESS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
USES_PULSING = bool(EXTRA.get("resources")) and ENV_ENABLED


def demo_run_and_check_output():
    print("\n=== run / check_output ===")

    result = subprocess.run(
        ["echo", "hello from run()"],
        capture_output=True,
        text=True,
        check=True,
        **EXTRA,
    )
    print("run()        ->", result.stdout.strip())

    hostname = subprocess.check_output(["hostname"], text=True, **EXTRA)
    print("check_output ->", hostname.strip())


def demo_popen_communicate():
    print("\n=== Popen / communicate ===")

    proc = subprocess.Popen(["cat"], stdin=PIPE, stdout=PIPE, text=True, **EXTRA)
    stdout, _ = proc.communicate(input="pipe test")
    print("cat          ->", stdout.strip())

    proc = subprocess.Popen(
        ["python3", "-c", "print(input().upper())"],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        **EXTRA,
    )
    stdout, stderr = proc.communicate(input="hello world")
    print("stdin/stdout ->", stdout.strip())
    if stderr:
        print("stderr       ->", stderr.strip())

    proc = subprocess.Popen(["ls", "-la"], stdout=PIPE, stderr=PIPE, text=True, **EXTRA)
    stdout, stderr = proc.communicate()
    print("ls -la       ->")
    print(stdout.strip())
    if stderr:
        print("stderr       ->", stderr.strip())


def demo_timeout():
    print("\n=== timeout ===")

    proc = subprocess.Popen(["sleep", "2"], **EXTRA)
    try:
        proc.communicate(timeout=0.2)
    except subprocess.TimeoutExpired:
        print("timeout      -> sleep 触发 TimeoutExpired")
        proc.kill()
        proc.communicate()


def demo_multi_turn_shell():
    print("\n=== multi-turn shell ===")

    proc = subprocess.Popen(
        ["/bin/sh"],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        **EXTRA,
    )

    def run_turn(cmd: str) -> str:
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()
        return proc.stdout.readline().strip()

    print(
        "turn 1       ->",
        run_turn("WORK=/tmp/pulsing_demo_$$ && mkdir -p $WORK && echo $WORK"),
    )
    print(
        "turn 2       ->",
        run_turn("echo 'hello pulsing' > $WORK/greet.txt && cat $WORK/greet.txt"),
    )
    print("turn 3       ->", run_turn("rm -rf $WORK && echo cleaned"))

    proc.stdin.write("exit\n")
    proc.stdin.flush()
    proc.wait(timeout=5)

    stderr = proc.stderr.read()
    if stderr:
        print("stderr       ->", stderr.strip())


def main():
    print("backend      ->", "pulsing" if USES_PULSING else "native")
    demo_run_and_check_output()
    demo_popen_communicate()
    demo_timeout()
    demo_multi_turn_shell()


if __name__ == "__main__":
    main()
