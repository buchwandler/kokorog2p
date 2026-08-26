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


def test_english_variants_share_lexicon_resources() -> None:
    """Behavioral variants must share one mapping per dialect and tier."""
    from kokorog2p import clear_cache, get_g2p

    clear_cache(deep=True)
    curly = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        phoneme_quotes="curly",
    )
    ascii_quotes = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        phoneme_quotes="ascii",
    )

    assert curly is not ascii_quotes
    assert curly.lexicon.golds is ascii_quotes.lexicon.golds
    assert curly.lexicon.silvers is ascii_quotes.lexicon.silvers


def test_french_variants_share_gold_resource() -> None:
    """French configuration variants must reuse the parsed gold mapping."""
    from kokorog2p import clear_cache, get_g2p

    clear_cache(deep=True)
    first = get_g2p("fr", use_spacy=False, use_espeak_fallback=False)
    second = get_g2p(
        "french", use_spacy=False, use_espeak_fallback=False, load_silver=False
    )

    assert first is not second
    assert first.lexicon.golds is second.lexicon.golds


def test_factory_aliases_and_unknown_options() -> None:
    """Aliases reuse identities and ignored options fail explicitly."""
    from kokorog2p import cache_info, clear_cache, get_g2p

    clear_cache(deep=True)
    canonical = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    alias = get_g2p(
        "english",
        use_spacy=False,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    assert canonical is alias
    assert cache_info().policy == "bounded-lru"

    with pytest.raises(TypeError, match="Unsupported get_g2p options"):
        get_g2p("en-us", markdown_syntax="disabled")


def test_deep_clear_releases_resource_caches() -> None:
    """Deep cleanup clears both instance and parsed dictionary caches."""
    from kokorog2p import clear_cache, get_g2p
    from kokorog2p.en.lexicon import lexicon_cache_info as english_cache_info
    from kokorog2p.fr.lexicon import lexicon_cache_info as french_cache_info

    get_g2p("en-us", use_spacy=False, use_espeak_fallback=False)
    get_g2p("fr", use_spacy=False, use_espeak_fallback=False)
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
                    load_silver=False, phoneme_quotes="curly")]
one = process.memory_info().rss
for quote_style in ("ascii", "none"):
    for strict in (False, True):
        variants.append(get_g2p(
            "en-us", use_spacy=False, use_espeak_fallback=False,
            load_silver=False, phoneme_quotes=quote_style, strict=strict,
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


def test_full_suite_discovers_each_test_module_once(tmp_path: Path) -> None:
    """The isolated runner enumerates every test module exactly once."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    for name in ("test_z.py", "test_a.py", "test_a.txt", "helper.py"):
        (tests_dir / name).touch()

    discovered = run_test_suite.discover_test_files(tmp_path)

    assert [path.name for path in discovered] == ["test_a.py", "test_z.py"]


def test_full_suite_runs_modules_sequentially(monkeypatch, tmp_path: Path) -> None:
    """The default runner starts the next module only after the prior exits."""
    test_files = [tmp_path / "tests" / "test_a.py", tmp_path / "tests" / "test_b.py"]
    calls: list[list[str]] = []
    active = 0
    maximum_active = 0

    def fake_run(command: list[str], **kwargs: object) -> object:
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        calls.append(command)
        active -= 1
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(run_test_suite.subprocess, "run", fake_run)

    assert run_test_suite.run_test_files(test_files, ["-q"], root=tmp_path) == 0
    assert maximum_active == 1
    assert [command[-1] for command in calls] == [
        "tests/test_a.py",
        "tests/test_b.py",
    ]
    assert all("-n" not in command for command in calls)
