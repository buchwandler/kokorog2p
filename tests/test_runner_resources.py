"""Contracts for the sequential test runners and RSS policy."""

from pathlib import Path

from tools import run_test_suite as suite
from tools import test_resources as resources


def test_test_fixtures_do_not_build_g2lex_assets() -> None:
    conftest = Path("tests/conftest.py").read_text(encoding="utf-8")
    assert "g2lex" not in conftest
    assert "lexphon data" not in conftest


def test_safe_pytest_selection_and_ci_profiles_are_explicit() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert (
        "not integration and not spacy and not slow and not resource_heavy" in pyproject
    )
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "--profile full --batch-size 4 --max-rss-mb auto" in workflow
    assert "--include-integration --batch-size 2 --max-rss-mb auto" in workflow


def test_auto_rss_limit_is_clamped(monkeypatch) -> None:
    monkeypatch.setattr(
        resources.psutil,
        "virtual_memory",
        lambda: type("Memory", (), {"total": 1024 * 2**20})(),
    )
    assert resources.auto_rss_limit() == resources.AUTO_RSS_MIN_MB


def test_build_test_plan_is_deterministic_and_isolates_marked_modules(
    tmp_path, monkeypatch
) -> None:
    ordinary = tmp_path / "test_ordinary.py"
    marked = tmp_path / "test_marked.py"
    ordinary.write_text("def test_one(): pass\n", encoding="utf-8")
    marked.write_text(
        "@pytest.mark.resource_heavy\ndef test_one(): pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        suite,
        "_source_markers",
        lambda path: frozenset({"resource_heavy"}) if path == marked else frozenset(),
    )

    groups = suite.build_test_plan([ordinary, marked, ordinary], batch_size=2)

    assert groups == [
        suite.TestGroup((ordinary,), isolated=False),
        suite.TestGroup((marked,), isolated=True),
        suite.TestGroup((ordinary,), isolated=False),
    ]


def test_resource_limited_batch_is_split_without_parallelism(
    tmp_path, monkeypatch
) -> None:
    files = tuple(tmp_path / f"test_{index}.py" for index in range(4))
    results = iter(
        [
            resources.RSSRunResult(resources.RSS_LIMIT_EXCEEDED, 9, 8, True),
            resources.RSSRunResult(0, 5, 8),
            resources.RSSRunResult(0, 6, 8),
        ]
    )
    calls: list[tuple[Path, ...]] = []

    def fake_run(group, *args, **kwargs):
        calls.append(group.files)
        return next(results)

    monkeypatch.setattr(suite, "_run_group", fake_run)
    result = suite.run_test_plan(
        [suite.TestGroup(files)],
        [],
        root=tmp_path,
        max_rss_mb=8,
    )

    assert result.returncode == 0
    assert result.failures == ()
    assert calls == [files, files[:2], files[2:]]
    assert result.peak_rss == 9
