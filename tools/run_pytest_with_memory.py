"""Run pytest while reporting current and peak RSS for the process tree."""

from __future__ import annotations

import subprocess
import sys
import time

import psutil


def _tree_rss(process: psutil.Process) -> int:
    """Return RSS for a process and all descendants still visible."""
    try:
        processes = [process, *process.children(recursive=True)]
    except psutil.Error:
        return 0

    total = 0
    for child in processes:
        try:
            total += child.memory_info().rss
        except psutil.Error:
            continue
    return total


def main(argv: list[str] | None = None) -> int:
    """Execute ``python -m pytest`` and return its exit status."""
    args = sys.argv[1:] if argv is None else argv
    process = subprocess.Popen([sys.executable, "-m", "pytest", *args])
    child = psutil.Process(process.pid)
    peak = 0

    while process.poll() is None:
        rss = _tree_rss(child)
        peak = max(peak, rss)
        print(
            f"\rRSS {rss / 2**20:8.1f} MiB | peak {peak / 2**20:8.1f} MiB",
            end="",
            flush=True,
        )
        time.sleep(0.25)

    process.wait()
    print(f"\nPeak RSS {peak / 2**20:.1f} MiB")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
