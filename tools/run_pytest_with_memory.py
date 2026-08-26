"""Run pytest while reporting and optionally limiting tree RSS."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

import psutil

RSS_LIMIT_EXCEEDED = 3


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


def _parse_args(argv: list[str]) -> tuple[int | None, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run pytest while reporting process-tree RSS usage."
    )
    parser.add_argument(
        "--max-rss-mb",
        type=int,
        help="Terminate pytest cleanly when tree RSS exceeds this many MiB.",
    )
    args, pytest_args = parser.parse_known_args(argv)
    if args.max_rss_mb is not None and args.max_rss_mb <= 0:
        parser.error("--max-rss-mb must be greater than zero")
    return args.max_rss_mb, pytest_args


def main(argv: list[str] | None = None) -> int:
    """Execute ``python -m pytest`` and return its exit status."""
    max_rss_mb, pytest_args = _parse_args(sys.argv[1:] if argv is None else argv)
    max_rss = max_rss_mb * 2**20 if max_rss_mb is not None else None
    process = subprocess.Popen([sys.executable, "-m", "pytest", *pytest_args])
    child = psutil.Process(process.pid)
    peak = 0
    limit_exceeded = False

    while process.poll() is None:
        rss = _tree_rss(child)
        peak = max(peak, rss)
        print(
            f"\rRSS {rss / 2**20:8.1f} MiB | peak {peak / 2**20:8.1f} MiB",
            end="",
            flush=True,
        )
        if max_rss is not None and rss > max_rss:
            print(
                f"\nRSS limit exceeded: {rss / 2**20:.1f} MiB "
                f"> {max_rss_mb} MiB; terminating pytest",
                flush=True,
            )
            process.terminate()
            limit_exceeded = True
            break
        time.sleep(0.25)

    if limit_exceeded:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        print(f"Peak RSS {peak / 2**20:.1f} MiB", flush=True)
        return RSS_LIMIT_EXCEEDED

    process.wait()
    print(f"\nPeak RSS {peak / 2**20:.1f} MiB")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
