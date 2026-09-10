"""Shared process and memory controls for resource-bounded test runners."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass

import psutil

RSS_LIMIT_EXCEEDED = 3
AUTO_RSS_MIN_MB = 512
AUTO_RSS_MAX_MB = 3072
AUTO_RSS_FRACTION = 0.20


@dataclass(frozen=True)
class RSSRunResult:
    """Result of a subprocess monitored for tree RSS."""

    returncode: int
    peak_rss: int
    limit_mb: int
    limit_exceeded: bool = False


def tree_rss(process: psutil.Process) -> int:
    """Return RSS for a process and all descendants still visible."""
    try:
        processes = [process, *process.children(recursive=True)]
    except psutil.Error:
        return 0

    total = 0
    for current in processes:
        try:
            total += current.memory_info().rss
        except psutil.Error:
            continue
    return total


def auto_rss_limit() -> int:
    """Return the conservative default RSS ceiling in MiB."""
    physical_mb = psutil.virtual_memory().total // 2**20
    return max(
        AUTO_RSS_MIN_MB,
        min(AUTO_RSS_MAX_MB, int(physical_mb * AUTO_RSS_FRACTION)),
    )


def terminate_process_tree(process: psutil.Process, *, timeout: float = 2.0) -> None:
    """Terminate a process and descendants, then kill survivors."""
    try:
        children = process.children(recursive=True)
    except psutil.Error:
        children = []

    for child in reversed(children):
        try:
            child.terminate()
        except psutil.Error:
            pass
    try:
        process.terminate()
    except psutil.Error:
        pass

    processes = [*children, process]
    _, alive = psutil.wait_procs(processes, timeout=timeout)
    for survivor in alive:
        try:
            survivor.kill()
        except psutil.Error:
            pass
    if alive:
        psutil.wait_procs(alive, timeout=timeout)


def run_with_rss_limit(
    command: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    max_rss_mb: int | None = None,
    poll_interval: float = 0.25,
) -> RSSRunResult:
    """Run one child process while enforcing a tree RSS ceiling."""
    limit_mb = max_rss_mb if max_rss_mb is not None else auto_rss_limit()
    if limit_mb <= 0:
        raise ValueError("max_rss_mb must be greater than zero")

    child = subprocess.Popen(list(command), cwd=cwd, env=env)
    process = psutil.Process(child.pid)
    limit_bytes = limit_mb * 2**20
    peak_rss = 0

    while child.poll() is None:
        rss = tree_rss(process)
        peak_rss = max(peak_rss, rss)
        if rss > limit_bytes:
            terminate_process_tree(process)
            child.wait()
            return RSSRunResult(
                RSS_LIMIT_EXCEEDED,
                peak_rss,
                limit_mb,
                limit_exceeded=True,
            )
        time.sleep(poll_interval)

    child.wait()
    peak_rss = max(peak_rss, tree_rss(process))
    return RSSRunResult(child.returncode, peak_rss, limit_mb)
