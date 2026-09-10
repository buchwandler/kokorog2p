"""Run pytest while reporting and limiting process-tree RSS."""

from __future__ import annotations

import argparse
import sys

try:
    from tools.test_resources import run_with_rss_limit
except ModuleNotFoundError:
    from test_resources import run_with_rss_limit


def _max_rss(value: str) -> int | None:
    if value.lower() == "auto":
        return None
    limit = int(value)
    if limit <= 0:
        raise argparse.ArgumentTypeError("max RSS must be greater than zero")
    return limit


def _parse_args(argv: list[str]) -> tuple[int | None, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run pytest while reporting and limiting process-tree RSS."
    )
    parser.add_argument(
        "--max-rss-mb",
        type=_max_rss,
        default=None,
        help="RSS ceiling in MiB, or auto for the conservative default.",
    )
    args, pytest_args = parser.parse_known_args(argv)
    return args.max_rss_mb, pytest_args


def main(argv: list[str] | None = None) -> int:
    """Execute ``python -m pytest`` and return its exit status."""
    max_rss_mb, pytest_args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = run_with_rss_limit(
        [sys.executable, "-m", "pytest", *pytest_args],
        max_rss_mb=max_rss_mb,
    )
    print(f"Peak RSS {result.peak_rss / 2**20:.1f} MiB")
    if result.limit_exceeded:
        print(
            "RSS limit exceeded; pytest stopped safely at the "
            f"{result.limit_mb} MiB ceiling.",
            file=sys.stderr,
        )
    else:
        print(f"RSS limit {result.limit_mb} MiB")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
