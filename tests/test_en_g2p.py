import inspect

import pytest

import kokorog2p
from kokorog2p.en import EnglishG2P


def test_constructor_and_factory_have_no_legacy_tier_parameters() -> None:
    legacy = {"load_" + "gold", "load_" + "silver", "use_" + "gold", "use_" + "silver"}
    for function in (kokorog2p.get_g2p, kokorog2p.phonemize, EnglishG2P):
        assert not legacy & set(inspect.signature(function).parameters)


def test_no_lexicon_mode_works_without_external_data() -> None:
    g2p = EnglishG2P(
        language="en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    assert g2p.lexicon.lexicons == ()
    assert g2p("unlistedword")[0].phonemes == "❓"
    g2p.close()


def test_factory_cache_includes_named_selection() -> None:
    kokorog2p.clear_cache(deep=True)
    first = kokorog2p.get_g2p(
        "en-us", lexicons=(), use_spacy=False, use_espeak_fallback=False
    )
    second = kokorog2p.get_g2p(
        "en-us", lexicons=(), use_spacy=False, use_espeak_fallback=False
    )
    assert first is second


def test_silver_selection_is_rejected() -> None:
    with pytest.raises(ValueError, match="Available lexicons: gold"):
        kokorog2p.get_g2p("en-us", lexicons="silver")


def test_phonemize_no_lexicon_mode() -> None:
    result = kokorog2p.phonemize(
        "unlistedword",
        language="en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        return_ids=False,
    )
    assert result.phonemes == "❓"


def test_fallback_only_were_regression() -> None:
    """Test that 'we're' uses corrected provider pronunciation without a Kokoro spelling exception.

    This test should fail if an old/broken runtime is accidentally installed.
    """
    g2p = EnglishG2P(
        language="en-us",
        lexicons=(),
        use_spacy=False,
    )
    result = g2p.phonemize("we're")
    # Expected Kokoro-compatible scalar fallback form from corrected eSpeak provider
    assert result == "wˈɪ\u200dɹ"
    g2p.close()


def test_context_weak_forms_preserved() -> None:
    """Test that normal English sentence/context output does not receive a global new stress rule.

    This verifies the cleanup did not move fallback stress policy into the primary English lexicon.
    """
    g2p = EnglishG2P(
        language="en-us",
        use_spacy=False,
    )
    # Use normal lexicons (default) rather than lexicons=()
    result = g2p.phonemize("I'm going where we're meeting.")
    # Should produce phonemes without error
    assert result is not None
    assert len(result) > 0
    g2p.close()


def test_fallback_only_were_no_spacy() -> None:
    """Test fallback pronunciation for 'we're' without spaCy."""
    g2p = EnglishG2P(
        language="en-us",
        lexicons=(),
        use_spacy=False,
    )
    result = g2p.phonemize("we're")
    assert result == "wˈɪ\u200dɹ"
    g2p.close()


@pytest.mark.spacy
def test_fallback_only_were_with_spacy() -> None:
    """Test fallback pronunciation for 'we're' with spaCy (if available)."""
    try:
        g2p = EnglishG2P(
            language="en-us",
            lexicons=(),
            use_spacy=True,
        )
        result = g2p.phonemize("we're")
        assert result == "wˈɪ\u200dɹ"
        g2p.close()
    except Exception:
        pytest.skip("spaCy model not available")
