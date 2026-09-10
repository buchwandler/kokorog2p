"""Run KokoroG2P tests in deterministic, resource-bounded batches."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from tools.test_resources import (
        RSS_LIMIT_EXCEEDED,
        RSSRunResult,
        run_with_rss_limit,
    )
except ModuleNotFoundError:
    from test_resources import RSS_LIMIT_EXCEEDED, RSSRunResult, run_with_rss_limit

ROOT = Path(__file__).resolve().parents[1]
TEST_PATTERN = "test_*.py"
DEFAULT_BATCH_SIZE = 8
MARKER_NAMES = ("integration", "spacy", "slow", "resource_heavy")


@dataclass(frozen=True)
class TestGroup:
    """A sequential pytest invocation plan item."""

    files: tuple[Path, ...]
    isolated: bool = False

    @property
    def label(self) -> str:
        return ", ".join(path.as_posix() for path in self.files)


@dataclass(frozen=True)
class GroupFailure:
    """A failed test group and its stable exit classification."""

    files: tuple[str, ...]
    returncode: int
    resource_limit: bool = False


@dataclass(frozen=True)
class SuiteResult:
    """Aggregated result for one runner invocation."""

    returncode: int
    failures: tuple[GroupFailure, ...]
    groups_run: int
    peak_rss: int


def discover_test_files(root: Path = ROOT) -> list[Path]:
    """Return all test modules in deterministic order."""
    return sorted((root / "tests").glob(TEST_PATTERN))


def _relative_test_path(test_file: Path, root: Path = ROOT) -> str:
    return test_file.relative_to(root).as_posix()


def _source_markers(test_file: Path) -> frozenset[str]:
    source = test_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test_file))
    marked_nodes = [
        node.decorator_list
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    decorator_text = " ".join(
        ast.unparse(decorator)
        for decorators in marked_nodes
        for decorator in decorators
    )
    module_text = " ".join(
        ast.unparse(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "pytestmark"
            for target in node.targets
        )
    )
    marker_text = f"{decorator_text} {module_text}"
    return frozenset(
        marker
        for marker in MARKER_NAMES
        if re.search(rf"pytest\.mark\.{marker}\b", marker_text)
    )


def select_test_files(
    test_files: list[Path],
    *,
    profile: str = "full",
    start_at: str | None = None,
    match: str | None = None,
    include_integration: bool = False,
    root: Path = ROOT,
) -> list[Path]:
    if profile not in {"core", "full", "release"}:
        raise ValueError(f"unknown profile: {profile}")
    selected = []
    for path in test_files:
        markers = _source_markers(path)
        if not include_integration and "integration" in markers:
            continue
        if profile not in {"core", "full", "release"}:
            raise ValueError(f"unknown profile: {profile}")
        selected.append(path)

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


def build_test_plan(
    test_files: Sequence[Path],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    root: Path = ROOT,
) -> list[TestGroup]:
    """Batch ordinary modules and isolate explicitly marked modules."""
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    groups: list[TestGroup] = []
    ordinary: list[Path] = []
    for path in test_files:
        if _source_markers(path):
            if ordinary:
                groups.extend(
                    TestGroup(tuple(ordinary[index : index + batch_size]))
                    for index in range(0, len(ordinary), batch_size)
                )
                ordinary = []
            groups.append(TestGroup((path,), isolated=True))
        else:
            ordinary.append(path)
    if ordinary:
        groups.extend(
            TestGroup(tuple(ordinary[index : index + batch_size]))
            for index in range(0, len(ordinary), batch_size)
        )
    return groups


def _pytest_command(
    files: Iterable[Path],
    pytest_args: Sequence[str],
    *,
    root: Path,
    coverage: bool,
    junit_path: Path | None,
) -> list[str]:
    relative_files = [_relative_test_path(path, root) for path in files]
    args = list(pytest_args)
    if junit_path is not None:
        args.append(f"--junitxml={junit_path}")
    command = [sys.executable]
    if coverage:
        command.extend(["-m", "coverage", "run", "--parallel-mode", "-m", "pytest"])
    else:
        command.extend(["-m", "pytest"])
    command.extend([*args, *relative_files])
    return command


def _child_environment(*, disable_plugin_autoload: bool) -> dict[str, str]:
    environment = os.environ.copy()
    if disable_plugin_autoload:
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    else:
        environment.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    return environment


def _run_group(
    group: TestGroup,
    pytest_args: Sequence[str],
    *,
    root: Path,
    max_rss_mb: int | None,
    coverage: bool,
    junit_path: Path | None,
    disable_plugin_autoload: bool,
) -> RSSRunResult:
    command = _pytest_command(
        group.files,
        pytest_args,
        root=root,
        coverage=coverage,
        junit_path=junit_path,
    )
    print(f"Running {group.label}", flush=True)
    return run_with_rss_limit(
        command,
        cwd=root,
        env=_child_environment(disable_plugin_autoload=disable_plugin_autoload),
        max_rss_mb=max_rss_mb,
    )


def _execute_group(
    group: TestGroup,
    pytest_args: Sequence[str],
    *,
    root: Path,
    max_rss_mb: int | None,
    coverage: bool,
    junit_dir: Path | None,
    disable_plugin_autoload: bool,
    failures: list[GroupFailure],
    peak_rss: list[int],
) -> None:
    junit_path = None
    if junit_dir is not None:
        junit_dir.mkdir(parents=True, exist_ok=True)
        junit_path = junit_dir / f"batch-{len(failures) + 1:03d}.xml"

    result = _run_group(
        group,
        pytest_args,
        root=root,
        max_rss_mb=max_rss_mb,
        coverage=coverage,
        junit_path=junit_path,
        disable_plugin_autoload=disable_plugin_autoload,
    )
    peak_rss[0] = max(peak_rss[0], result.peak_rss)
    if result.limit_exceeded and len(group.files) > 1:
        midpoint = len(group.files) // 2
        for files in (group.files[:midpoint], group.files[midpoint:]):
            _execute_group(
                TestGroup(files),
                pytest_args,
                root=root,
                max_rss_mb=max_rss_mb,
                coverage=coverage,
                junit_dir=junit_dir,
                disable_plugin_autoload=disable_plugin_autoload,
                failures=failures,
                peak_rss=peak_rss,
            )
        return

    if result.returncode != 0:
        failures.append(
            GroupFailure(
                tuple(_relative_test_path(path, root) for path in group.files),
                result.returncode,
                result.limit_exceeded or result.returncode == RSS_LIMIT_EXCEEDED,
            )
        )


def run_test_plan(
    groups: Sequence[TestGroup],
    pytest_args: Sequence[str],
    *,
    root: Path = ROOT,
    max_rss_mb: int | None = None,
    fail_fast: bool = False,
    coverage: bool = False,
    junit_dir: Path | None = None,
    disable_plugin_autoload: bool = True,
) -> SuiteResult:
    """Execute groups sequentially and aggregate failures."""
    failures: list[GroupFailure] = []
    peak_rss = [0]
    groups_run = 0
    for group in groups:
        groups_run += 1
        before = len(failures)
        _execute_group(
            group,
            pytest_args,
            root=root,
            max_rss_mb=max_rss_mb,
            coverage=coverage,
            junit_dir=junit_dir,
            disable_plugin_autoload=disable_plugin_autoload,
            failures=failures,
            peak_rss=peak_rss,
        )
        if fail_fast and len(failures) > before:
            break

    first_failure = failures[0].returncode if failures else 0
    return SuiteResult(first_failure, tuple(failures), groups_run, peak_rss[0])


def run_test_files(
    test_files: list[Path],
    pytest_args: list[str],
    *,
    fail_fast: bool = False,
    root: Path = ROOT,
) -> int:
    """Compatibility runner for callers that request one file per process."""
    first_failure = 0
    failures: list[tuple[str, int]] = []
    for test_file in test_files:
        relative_path = _relative_test_path(test_file, root)
        print(f"Running {relative_path}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *pytest_args, relative_path],
            cwd=root,
            check=False,
        )
        if result.returncode != 0:
            failures.append((relative_path, result.returncode))
            if first_failure == 0:
                first_failure = result.returncode
            if fail_fast:
                break

    if failures:
        print("\nFailed test modules:", file=sys.stderr, flush=True)
        for relative_path, returncode in failures:
            print(
                f"  - {relative_path} (exit {returncode})",
                file=sys.stderr,
                flush=True,
            )
    return first_failure


def _max_rss(value: str) -> int | None:
    if value.lower() == "auto":
        return None
    limit = int(value)
    if limit <= 0:
        raise argparse.ArgumentTypeError("max RSS must be greater than zero")
    return limit


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Run tests in deterministic, sequential, resource-bounded batches."
    )
    parser.add_argument(
        "--profile", choices=("core", "full", "release"), default="core"
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-rss-mb", type=_max_rss, default=None)
    parser.add_argument(
        "--list-plan",
        "--list",
        action="store_true",
        help="Print the selected execution plan.",
    )
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--start-at", metavar="PATH")
    parser.add_argument("--match", metavar="REGEX")
    parser.add_argument("--include-integration", action="store_true")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--json-report", metavar="PATH")
    parser.add_argument("--junit-dir", type=Path, default=None)
    parser.add_argument("--enable-pytest-plugins", action="store_true")
    parser.add_argument("--pytest-arg", action="append", default=[], metavar="ARG")
    parser.add_argument("pytest_args", nargs="*")
    return parser


def _write_json_report(
    path: str, result: SuiteResult, groups: Sequence[TestGroup]
) -> None:
    payload = {
        "returncode": result.returncode,
        "groups_run": result.groups_run,
        "peak_rss_mb": result.peak_rss / 2**20,
        "groups": [[file.as_posix() for file in group.files] for group in groups],
        "failures": [
            {
                "files": failure.files,
                "returncode": failure.returncode,
                "resource_limit": failure.resource_limit,
            }
            for failure in result.failures
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Discover, plan, and optionally execute the selected test profile."""
    parser = build_parser()
    args, unknown_args = parser.parse_known_args(argv)
    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero")
    if args.max_rss_mb is not None and args.max_rss_mb <= 0:
        parser.error("--max-rss-mb must be greater than zero or auto")

    try:
        selected = select_test_files(
            discover_test_files(),
            profile=args.profile,
            start_at=args.start_at,
            match=args.match,
            include_integration=args.include_integration,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if not selected:
        parser.error("no test modules matched the requested selection")

    groups = build_test_plan(selected, batch_size=args.batch_size)
    if args.list_plan:
        for index, group in enumerate(groups, 1):
            isolation = " isolated" if group.isolated else ""
            print(f"{index:03d}{isolation}: {group.label}")
        return 0

    profile_args = [
        "-o",
        (
            "addopts=-v --tb=short -m 'not integration and not spacy and not slow "
            "and not resource_heavy'"
            if args.profile == "core"
            else "addopts=-v --tb=short"
        ),
    ]
    pytest_args = [
        *profile_args,
        *args.pytest_arg,
        *args.pytest_args,
        *unknown_args,
    ]
    result = run_test_plan(
        groups,
        pytest_args,
        max_rss_mb=args.max_rss_mb,
        fail_fast=args.fail_fast,
        coverage=args.coverage,
        junit_dir=args.junit_dir,
        disable_plugin_autoload=not args.enable_pytest_plugins,
    )
    if args.coverage and result.returncode == 0:
        for command in (
            [sys.executable, "-m", "coverage", "combine"],
            [sys.executable, "-m", "coverage", "xml"],
            [sys.executable, "-m", "coverage", "report"],
        ):
            completed = subprocess.run(command, cwd=ROOT, check=False)
            if completed.returncode != 0:
                return completed.returncode
    if args.json_report:
        _write_json_report(args.json_report, result, groups)
    if result.failures:
        print("\nFailed test groups:", file=sys.stderr, flush=True)
        for failure in result.failures:
            kind = "resource limit" if failure.resource_limit else "test failure"
            print(
                f"  - {', '.join(failure.files)} ({kind}, exit {failure.returncode})",
                file=sys.stderr,
            )
    print(f"Peak RSS {result.peak_rss / 2**20:.1f} MiB", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
