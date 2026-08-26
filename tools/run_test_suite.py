"""Run the complete pytest suite in isolated, sequential subprocesses."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_PATTERN = "test_*.py"


def discover_test_files(root: Path = ROOT) -> list[Path]:
    """Return all test modules in deterministic order."""
    return sorted((root / "tests").glob(TEST_PATTERN))


def _relative_test_path(test_file: Path, root: Path = ROOT) -> str:
    return test_file.relative_to(root).as_posix()


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Run each tests/test_*.py module in a fresh pytest subprocess."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List discovered test modules without running them.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first test module failure.",
    )
    parser.add_argument(
        "--start-at",
        metavar="PATH",
        help="Start with this test module and continue in sorted order.",
    )
    parser.add_argument(
        "--match",
        metavar="REGEX",
        help=(
            "Run only test modules whose relative paths match this regular expression."
        ),
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Pass one argument to every pytest subprocess. May be repeated.",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional pytest arguments passed to every subprocess.",
    )
    return parser


def select_test_files(
    test_files: list[Path],
    *,
    start_at: str | None = None,
    match: str | None = None,
    root: Path = ROOT,
) -> list[Path]:
    """Apply start and regular-expression filters to discovered modules."""
    selected = test_files
    if start_at is not None:
        normalized_start = Path(start_at).as_posix()
        relative_paths = [_relative_test_path(path, root) for path in selected]
        try:
            selected = selected[relative_paths.index(normalized_start) :]
        except ValueError as exc:
            raise ValueError(f"test module not found: {start_at}") from exc

    if match is not None:
        matcher = re.compile(match)
        selected = [
            path for path in selected if matcher.search(_relative_test_path(path, root))
        ]
    return selected


def run_test_files(
    test_files: list[Path],
    pytest_args: list[str],
    *,
    fail_fast: bool = False,
    root: Path = ROOT,
) -> int:
    """Run selected test modules sequentially and return the first failure code."""
    first_failure = 0
    for test_file in test_files:
        relative_path = _relative_test_path(test_file, root)
        print(f"Running {relative_path}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *pytest_args, relative_path],
            cwd=root,
            check=False,
        )
        if result.returncode != 0:
            if first_failure == 0:
                first_failure = result.returncode
            if fail_fast:
                break
    return first_failure


def main(argv: list[str] | None = None) -> int:
    """Discover and run the selected test modules."""
    parser = build_parser()
    args = parser.parse_args(argv)
    test_files = discover_test_files()

    try:
        selected = select_test_files(
            test_files,
            start_at=args.start_at,
            match=args.match,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.list:
        for test_file in selected:
            print(_relative_test_path(test_file))
        return 0

    if not selected:
        parser.error("no test modules matched the requested selection")

    return run_test_files(
        selected,
        [*args.pytest_arg, *args.pytest_args],
        fail_fast=args.fail_fast,
    )


if __name__ == "__main__":
    raise SystemExit(main())
