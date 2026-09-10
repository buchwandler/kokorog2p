"""Regression tests for process and resource memory lifetime behavior."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


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
