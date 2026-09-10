"""Regression tests for process and resource memory lifetime behavior."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools import run_test_suite


def test_pipeline_test_module_does_not_import_spacy() -> None:
    """Collection helpers must not import the heavyweight spaCy package."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import tests.test_pipeline_api; "
                "assert 'spacy' not in sys.modules"
            ),
        ],
        check=False,
        cwd=Path(__file__).parents[1],
    )
    assert result.returncode == 0


def test_english_variants_share_no_lexicon_selection() -> None:
    """Behavioral variants reuse the no-lexicon selection without external data."""
    from kokorog2p import clear_cache, get_g2p

    clear_cache(deep=True)
    curly = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        lexicons=(),
    )
    ascii_quotes = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        lexicons=(),
    )

    assert curly is ascii_quotes
    assert curly.lexicon.lexicons == ()


def test_french_equivalent_aliases_share_factory_identity() -> None:
    """Equivalent French aliases and selections reuse one canonical factory."""
    from kokorog2p import clear_cache, get_g2p

    clear_cache(deep=True)
    first = get_g2p("fr", use_spacy=False, use_espeak_fallback=False, lexicons=())
    second = get_g2p("french", use_spacy=False, use_espeak_fallback=False, lexicons=())

    assert first is second
    assert first.lexicon.lexicons == ()


def test_factory_aliases_and_unknown_options() -> None:
    """Aliases reuse identities and ignored options fail explicitly."""
    from kokorog2p import cache_info, clear_cache, get_g2p

    clear_cache(deep=True)
    canonical = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        lexicons=(),
    )
    alias = get_g2p(
        "english",
        use_spacy=False,
        use_espeak_fallback=False,
        lexicons=(),
    )
    assert canonical is alias
    assert cache_info().policy == "bounded-lru"

    with pytest.raises(TypeError, match="Unsupported get_g2p options"):
        get_g2p("en-us", markdown_syntax="disabled", lexicons=())


def test_deep_clear_releases_resource_caches() -> None:
    """Deep cleanup clears both instance and parsed dictionary caches."""
    from kokorog2p import clear_cache, get_g2p
    from kokorog2p.en.lexicon import lexicon_cache_info as english_cache_info
    from kokorog2p.fr.lexicon import lexicon_cache_info as french_cache_info

    get_g2p("en-us", use_spacy=False, use_espeak_fallback=False, lexicons=())
    get_g2p("fr", use_spacy=False, use_espeak_fallback=False, lexicons=())
    clear_cache(deep=True)

    assert english_cache_info().currsize == 0
    assert french_cache_info().currsize == 0


def test_english_variant_memory_is_not_multiplicative() -> None:
    """Six retained variants should not retain six complete dictionaries."""
    pytest.importorskip("psutil")
    code = """
import gc
import psutil
from kokorog2p import clear_cache, get_g2p

process = psutil.Process()
clear_cache(deep=True)
baseline = process.memory_info().rss
variants = [get_g2p("en-us", use_spacy=False, use_espeak_fallback=False,
                    lexicons=(), phoneme_quotes="curly")]
one = process.memory_info().rss
for quote_style in ("ascii", "none"):
    for strict in (False, True):
        variants.append(get_g2p(
            "en-us", use_spacy=False, use_espeak_fallback=False,
            lexicons=(), phoneme_quotes=quote_style, strict=strict,
        ))
gc.collect()
six = process.memory_info().rss
print(baseline, one, six)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
    )
    baseline, one, six = (int(value) for value in result.stdout.split())
    one_delta = max(one - baseline, 1)
    assert six - baseline <= 2.5 * one_delta


def test_runner_profiles_keep_safe_and_exhaustive_selection(tmp_path: Path) -> None:
    """Core excludes integrations while full keeps marked non-integration modules."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    ordinary = tests_dir / "test_ordinary.py"
    heavy = tests_dir / "test_heavy.py"
    integration = tests_dir / "test_integration.py"
    ordinary.write_text("def test_one(): pass\n", encoding="utf-8")
    heavy.write_text(
        "import pytest\n@pytest.mark.resource_heavy\ndef test_one(): pass\n",
        encoding="utf-8",
    )
    integration.write_text(
        "import pytest\n@pytest.mark.integration\ndef test_one(): pass\n",
        encoding="utf-8",
    )

    files = run_test_suite.discover_test_files(tmp_path)
    assert run_test_suite.select_test_files(files, profile="core") == [heavy, ordinary]
    assert run_test_suite.select_test_files(
        files, profile="full", include_integration=True
    ) == [heavy, integration, ordinary]


def test_canonical_runner_forwards_one_batch_without_parallel_flags(
    monkeypatch, tmp_path: Path
) -> None:
    files = tuple(tmp_path / "tests" / name for name in ("test_a.py", "test_b.py"))
    calls = []
    monkeypatch.setattr(
        run_test_suite,
        "run_with_rss_limit",
        lambda command, **kwargs: (
            calls.append(command) or run_test_suite.RSSRunResult(0, 10, 512)
        ),
    )

    result = run_test_suite.run_test_plan(
        [run_test_suite.TestGroup(files)], [], root=tmp_path, max_rss_mb=512
    )

    assert result.returncode == 0
    assert len(calls) == 1
    assert calls[0][-2:] == ["tests/test_a.py", "tests/test_b.py"]
    assert "-n" not in calls[0]


def test_canonical_runner_aggregates_failures_and_honors_fail_fast(
    monkeypatch, tmp_path: Path
) -> None:
    files = tuple(tmp_path / "tests" / name for name in ("test_a.py", "test_b.py"))
    results = iter(
        [
            run_test_suite.RSSRunResult(5, 10, 512),
            run_test_suite.RSSRunResult(0, 12, 512),
        ]
    )
    monkeypatch.setattr(
        run_test_suite,
        "_run_group",
        lambda *args, **kwargs: next(results),
    )
    groups = [run_test_suite.TestGroup((path,)) for path in files]

    result = run_test_suite.run_test_plan(
        groups, [], root=tmp_path, max_rss_mb=512, fail_fast=True
    )

    assert result.returncode == 5
    assert result.groups_run == 1
    assert result.failures[0].files == ("tests/test_a.py",)
